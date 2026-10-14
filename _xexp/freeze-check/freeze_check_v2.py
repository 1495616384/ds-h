"""H3 统一冻结核验 v2（不依赖检测器输出、不依赖控制台代码页、不依赖管道能力）。

v1 -> v2 修正（v1 保留不改写，作为历史记录）：

  F-1 **控制台编码崩溃**：v1 在 GBK 代码页下 print('↔') 抛 UnicodeEncodeError，
      脚本以退出码 1 崩溃、**丢失全部核验结论**（本轮实测复现）。
      v2 启动即把 stdout/stderr 显式 reconfigure(encoding='utf-8', errors='replace')，
      并把全部前缀符号替换为 ASCII，保证任何代码页下都能完整输出。
  F-2 **基线检查假阴性**：v1 中"基线工作树干净"的 ok = (rc3 == 0 and not dirty)，
      且 dirty 为空时显示"实测 0 项改动/未跟踪"。当 git 命令**本身失败**（rc!=0，
      输出为空）时，逐项打印看起来像"干净"。
      v2 把 git 返回码纳入每一项的 ok 条件，并区分"干净 / 脏 / git 失败"三态。
  F-3 **脚本自身未纳入核验**：v1 不核验 freeze_check 自身的 SHA-256。
      v2 引入 self_check（自绑定哈希）。
  F-4 **冻结记录版本可变**：v1 在期望指纹内硬绑定 Manifest v4。
      v2 支持 --manifest vN 选择冻结记录，默认 v5；绑定对象在期望文件中声明。
  F-5 **依赖管道能力**：受限环境下（沙箱禁止创建管道）subprocess 的
      capture_output=True 直接抛 PermissionError(WinError 5)，v1 会以退出码 1 崩溃。
      v2 的 git_run 在管道不可用时**自动回退到临时文件重定向**，仍能拿到真实
      stdout/stderr 与返回码。

退出码：
  0 = 指纹全部一致 且 正式门槛就绪
  2 = 指纹不一致 / 冻结完整性破坏（含基线工作树不干净、脚本自身指纹不符），逐项指出
  3 = 指纹一致，但正式门槛未就绪（无已选案例 / 整体人工审查未完成）
  4 = 已选案例引用了未获授权使用的约束
  5 = git 命令执行失败（输出真实 stderr 与返回码）

注意：本脚本**不**运行检测器；**不**执行语义审查。
脚本中人工审查清单的存在 **不代表** 人工审查已完成。
"""
import argparse
import atexit
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# F-1：先固定输出编码，再打印任何内容
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):  # 非文本流或旧解释器
        pass

ROOT = Path(r"G:\ds-h")          # 可被 --root 覆盖（自测用隔离根目录）
HERE = Path(__file__).parent
GIT = r"C:\Program Files\Git\cmd\git.exe"

GIT_ERRORS = []                  # (args, returncode, stderr)
GIT_CAPTURE_MODE = None          # "pipe" | "tempfile"
_TMP_FILES = []


def _cleanup_tmp():
    for p in _TMP_FILES:
        try:
            os.unlink(p)
        except OSError:
            pass


atexit.register(_cleanup_tmp)


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def _run_captured(args):
    """返回 (rc, stdout, stderr)。优先管道；管道不可用则回退临时文件重定向（F-5）。"""
    global GIT_CAPTURE_MODE
    if GIT_CAPTURE_MODE in (None, "pipe"):
        try:
            r = subprocess.run([GIT, *args], capture_output=True,
                               encoding="utf-8", errors="replace")
            GIT_CAPTURE_MODE = "pipe"
            return r.returncode, r.stdout or "", r.stderr or ""
        except OSError as exc:
            if getattr(exc, "winerror", None) != 5:
                raise
            GIT_CAPTURE_MODE = "tempfile"  # 管道被拒 -> 本进程后续一律走临时文件
    outs = []
    for tag in ("out", "err"):
        fd, name = tempfile.mkstemp(prefix=f"freezecheck-{tag}-", suffix=".txt")
        os.close(fd)
        _TMP_FILES.append(name)
        outs.append(name)
    with open(outs[0], "w", encoding="utf-8") as fo, open(outs[1], "w", encoding="utf-8") as fe:
        r = subprocess.run([GIT, *args], stdout=fo, stderr=fe)
    return (r.returncode,
            Path(outs[0]).read_text(encoding="utf-8", errors="replace"),
            Path(outs[1]).read_text(encoding="utf-8", errors="replace"))


def git_run(*args):
    """执行 git，返回 (rc, stdout, stderr)；失败时记录真实 stderr 与返回码。"""
    try:
        rc, out, err = _run_captured(list(args))
    except OSError as exc:
        GIT_ERRORS.append((args, -1, f"无法执行 git: {exc}"))
        return -1, "", str(exc)
    if rc != 0:
        GIT_ERRORS.append((args, rc, err.strip()))
    return rc, out.strip(), err.strip()


def main() -> int:
    ap = argparse.ArgumentParser(description="H3 统一冻结核验 v2")
    ap.add_argument("--expected", default=None, help="期望指纹文件（默认按 --manifest 推导）")
    ap.add_argument("--manifest", default="v6", help="冻结记录版本，如 v6（当前有效）/ v5（历史）")
    ap.add_argument("--root", default=None, help="被核验根目录（默认 G:\\ds-h；自测用隔离根）")
    args = ap.parse_args()

    root = Path(args.root).resolve() if args.root else ROOT
    expected_path = Path(args.expected).resolve() if args.expected else HERE / f"expected-fingerprints-{args.manifest}.json"
    selection_path = HERE / "selected-cases.json"
    self_path = Path(__file__).resolve()

    print("=== H3 统一冻结核验 v2 ===")
    print(f"根目录  : {root}")
    print(f"期望指纹: {expected_path}")
    print()

    if not expected_path.exists():
        print(f"[FAIL] 期望指纹文件缺失: {expected_path}")
        print("\n  [退出码 2] 无法核验（期望指纹文件不存在）")
        return 2

    exp = json.loads(expected_path.read_text(encoding="utf-8"))
    sel = json.loads(selection_path.read_text(encoding="utf-8")) if selection_path.exists() \
        else {"formal_cases_selected": []}
    checks = []  # (item, expected, actual, ok)

    # 0. 脚本自身指纹（F-3）
    self_exp = (exp.get("self_check") or {}).get("sha256")
    self_act = sha256(self_path)
    if self_exp is None:
        print("[WARN] 期望指纹文件未声明 self_check.sha256；跳过脚本自身核验")
    else:
        checks.append(("核验脚本自身（freeze_check_v2.py）", self_exp, self_act, self_act == self_exp))

    # 1. 冻结记录绑定
    mf = exp["bound_freeze_record"]
    mp = root / mf["file"]
    checks.append((f"冻结记录 {mf['file'].split('/')[-1]}", mf["sha256"],
                   sha256(mp) if mp.exists() else "<缺失>",
                   mp.exists() and sha256(mp) == mf["sha256"]))

    # 2. 规范哈希
    for key, item in exp["spec"].items():
        sp = root / item["path"]
        checks.append((f"规范 {key}", item["sha256"],
                       sha256(sp) if sp.exists() else "<缺失>",
                       sp.exists() and sha256(sp) == item["sha256"]))

    # 3. 登记表 + 校验脚本
    rr = exp["risk_registry"]
    rp = root / rr["path"]
    checks.append(("RISK-REGISTRY v1", rr["sha256"],
                   sha256(rp) if rp.exists() else "<缺失>",
                   rp.exists() and sha256(rp) == rr["sha256"]))
    vp = root / rr["verifier"]["path"]
    checks.append(("登记表校验脚本", rr["verifier"]["sha256"],
                   sha256(vp) if vp.exists() else "<缺失>",
                   vp.exists() and sha256(vp) == rr["verifier"]["sha256"]))

    # 4. 协议 + 逐条授权审查
    cp = root / exp["case_protocol"]["path"]
    checks.append(("案例登记协议 v1", exp["case_protocol"]["sha256"],
                   sha256(cp) if cp.exists() else "<缺失>",
                   cp.exists() and sha256(cp) == exp["case_protocol"]["sha256"]))
    ar = exp["authorization_review"]
    arp = root / ar["path"]
    checks.append(("逐条授权审查文件", ar["sha256"],
                   sha256(arp) if arp.exists() else "<缺失>",
                   arp.exists() and sha256(arp) == ar["sha256"]))

    # 5. 引擎
    ep = root / exp["engine"]["path"]
    checks.append(("引擎 detect_x0.py", exp["engine"]["sha256"],
                   sha256(ep) if ep.exists() else "<缺失>",
                   ep.exists() and sha256(ep) == exp["engine"]["sha256"]))

    # 5b. 支撑工具（受限环境子进程捕获 helper 等；可选段）
    for key, item in (exp.get("tools") or {}).items():
        tp = root / item["path"]
        checks.append((f"支撑工具 {key}", item["sha256"],
                       sha256(tp) if tp.exists() else "<缺失>",
                       tp.exists() and sha256(tp) == item["sha256"]))

    # 6. 基线 commit / tree / 工作树（F-2：三态，返回码纳入 ok）
    bl = exp["baseline"]
    base = root / bl["path"]
    rc1, a_commit, _ = git_run("-C", str(base), "rev-parse", "HEAD")
    rc2, a_tree, _ = git_run("-C", str(base), "rev-parse", "HEAD^{tree}")
    rc3, a_status, _ = git_run("-C", str(base), "status", "--porcelain")
    checks.append(("基线 commit", bl["commit"], a_commit,
                   rc1 == 0 and a_commit == bl["commit"]))
    checks.append(("基线 tree", bl["tree"], a_tree,
                   rc2 == 0 and a_tree == bl["tree"]))
    dirty = [ln for ln in a_status.splitlines() if ln.strip()]
    if rc3 != 0:
        wt_state, wt_actual = "GIT_FAIL", "<git 失败>"
    elif dirty:
        wt_state, wt_actual = "DIRTY", f"{len(dirty)} 项改动/未跟踪"
    else:
        wt_state, wt_actual = "CLEAN", "<空>"
    checks.append(("基线工作树干净", "<空>", wt_actual, wt_state == "CLEAN"))

    # 7. 登记表声明 与 实测
    reg = json.loads(rp.read_text(encoding="utf-8")) if rp.exists() else {}
    sb = reg.get("subject_baseline", {})
    checks.append(("登记表声明 commit 与 实测", sb.get("commit"), a_commit,
                   sb.get("commit") == a_commit))
    checks.append(("登记表声明 tree 与 实测", sb.get("tree"), a_tree,
                   sb.get("tree") == a_tree))

    # 输出
    width = max(len(c[0]) for c in checks)
    for item, e, a, ok in checks:
        print(f"[{'OK  ' if ok else 'FAIL'}] {item.ljust(width)}  期望 {str(e)[:16]}  实测 {str(a)[:16]}")
    fp_fail = [c[0] for c in checks if not c[3]]

    if wt_state == "DIRTY":
        print("\n=== 基线工作树脏项（逐条列出）===")
        for ln in dirty:
            print(f"  {ln}")

    if GIT_ERRORS:
        print("\n=== git 命令失败（真实 stderr 与返回码）===")
        for gargs, rc, err in GIT_ERRORS:
            print(f"  git {' '.join(gargs)}")
            print(f"    返回码: {rc}")
            print(f"    stderr : {err}")

    # 8. 已选正式案例
    print("\n=== 已选正式案例核验 ===")
    cases = sel.get("formal_cases_selected", [])
    case_fail, unauthorized = [], []
    auth = json.loads(arp.read_text(encoding="utf-8")) if arp.exists() else {"entries": []}
    authorized = {e["constraint_id"] for e in auth.get("entries", [])
                  if e.get("authorization") == "AUTHORIZED"}
    blocked = {e["constraint_id"] for e in auth.get("entries", [])
               if e.get("authorization") == "BLOCKED"}
    if not cases:
        print("  尚未选择正式案例（预期状态：本轮不设计案例）")
    else:
        for c in cases:
            cid = c.get("case_id", "?")
            for fkey in ("case_json", "diff_patch", "standard_answer"):
                f = c.get(fkey)
                if not f:
                    case_fail.append(f"{cid}: 缺少 {fkey}")
                    print(f"  FAIL {cid}: 未登记 {fkey}")
                    continue
                fp = root / f["path"]
                ok = fp.exists() and sha256(fp) == f["sha256"].upper()
                print(f"  [{'OK  ' if ok else 'FAIL'}] {cid} {fkey}  {f['sha256'][:16]}")
                if not ok:
                    case_fail.append(f"{cid}: {fkey} 哈希不符")
            for ref in c.get("constraint_ids", []):
                if ref in blocked:
                    unauthorized.append(f"{cid} -> {ref}（BLOCKED）")
                elif ref not in authorized:
                    unauthorized.append(f"{cid} -> {ref}（未列入授权清单）")

    # 9. 逐条授权状态（读自授权审查文件）
    print("\n=== 逐条授权状态（来源：授权审查文件 v1） ===")
    print(f"AUTHORIZED（{len(authorized)}）：{sorted(authorized)}")
    print(f"BLOCKED（{len(blocked)}）：{sorted(blocked)}")
    print(f"manual_review_completed: {auth.get('manual_review_completed')}  <- 未完成前正式案例不得启动")
    if unauthorized:
        print("  未授权引用：")
        for x in unauthorized:
            print(f"    - {x}")

    # 结论与退出码
    print("\n=== 结论 ===")
    print(f"（git 输出捕获方式：{GIT_CAPTURE_MODE or '未调用'}）")
    if GIT_ERRORS:
        print("  [退出码 5] git 命令执行失败（见上；注意：基线检查项已按失败处理）")
        return 5
    if fp_fail:
        print("  指纹核验：未通过")
        for x in fp_fail:
            print(f"    - 不一致项：{x}")
        if "基线工作树干净" in fp_fail:
            print("    （基线含未提交修改或未跟踪文件 -> 冻结完整性破坏）")
        if any("自身" in x for x in fp_fail):
            print("    （核验脚本自身指纹与期望不符 -> 冻结工具已被改写，须发布新清单）")
        print("\n  [退出码 2] 指纹不一致 / 冻结完整性破坏")
        return 2
    print("  指纹核验：全部一致（脚本自身 / 冻结记录 / 规范 / 登记表 / 协议 / 授权审查 / 引擎 / 基线 / 工作树 / 绑定）")

    if case_fail:
        print("  案例核验：未通过")
        print("\n  [退出码 2] 案例文件指纹不一致")
        return 2
    if unauthorized:
        print("  授权核验：未通过（引用了禁止或未登记约束）")
        print("\n  [退出码 4] 已选案例引用未授权约束")
        return 4

    gate_reason = []
    if not cases:
        gate_reason.append("尚未选择正式案例")
    if not auth.get("manual_review_completed"):
        gate_reason.append("整体人工审查未完成（逐条基线侧审查已记录，但案例级 U1 范围检查未做；"
                           "脚本不执行语义审查——清单存在≠审查完成）")
    if gate_reason:
        print("  正式门槛：**未就绪**")
        for r in gate_reason:
            print(f"    - {r}")
        print("\n  [退出码 3] 指纹一致，但正式 H3 尚不可启动")
        return 3
    print("  正式门槛：就绪")
    print("\n  [退出码 0] 全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
