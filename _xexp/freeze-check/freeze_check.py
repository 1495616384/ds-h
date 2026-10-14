"""H3 统一冻结核验（不依赖检测器输出）。

核验对象：
  1. 规范 v1.2.1（现行）SHA-256
  2. RISK-REGISTRY v1 与登记表校验脚本 SHA-256
  3. 案例登记协议 v1 与逐条授权审查文件 SHA-256
  4. 引擎 detect_x0.py SHA-256
  5. 基线 commit / tree / **工作树是否干净（git status --porcelain 为空）**
  6. 登记表内部声明的目标基线 与 实测基线 是否一致
  7. 已选正式案例的 case.json / diff.patch / 标准答案 哈希
  8. 已选案例所引约束是否被**逐条授权**（读取授权审查文件，非硬编码）
  9. Manifest v4（冻结记录）自身哈希（绑定防改写）

退出码：
  0 = 指纹全部一致 且 正式门槛就绪
  2 = 指纹不一致或冻结完整性破坏（硬失败，逐项指出；含基线工作树不干净）
  3 = 指纹一致，但正式门槛未就绪（无已选案例 / 整体人工审查未完成）
  4 = 已选案例引用了未获授权使用的约束
  5 = git 命令执行失败（输出真实 stderr 与返回码）

注意：本脚本**不**运行检测器；**不**执行语义审查。
脚本中人工审查清单的存在 **不代表** 人工审查已完成。
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"G:\ds-h")
HERE = Path(__file__).parent
GIT = r"C:\Program Files\Git\cmd\git.exe"

EXPECTED = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "expected-fingerprints-v1.json"
SELECTION = HERE / "selected-cases.json"

GIT_ERRORS = []  # (args, returncode, stderr)


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def git_run(*args):
    """执行 git，返回 (rc, stdout, stderr)；失败时记录真实 stderr 与返回码。"""
    try:
        r = subprocess.run([GIT, *args], capture_output=True,
                           encoding="utf-8", errors="replace")
    except OSError as exc:
        GIT_ERRORS.append((args, -1, f"无法执行 git: {exc}"))
        return -1, "", str(exc)
    if r.returncode != 0:
        GIT_ERRORS.append((args, r.returncode, (r.stderr or "").strip()))
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


def main() -> int:
    exp = json.loads(EXPECTED.read_text(encoding="utf-8"))
    sel = json.loads(SELECTION.read_text(encoding="utf-8"))
    checks = []  # (item, expected, actual, ok)

    # 9. 冻结记录绑定
    mf = exp["bound_freeze_record"]
    p = ROOT / mf["file"]
    checks.append(("Manifest v4（冻结记录）", mf["sha256"],
                   sha256(p) if p.exists() else "<缺失>",
                   p.exists() and sha256(p) == mf["sha256"]))

    # 1. 规范哈希
    for key, item in exp["spec"].items():
        sp = ROOT / item["path"]
        checks.append((f"规范 {key}", item["sha256"],
                       sha256(sp) if sp.exists() else "<缺失>",
                       sp.exists() and sha256(sp) == item["sha256"]))

    # 2. 登记表 + 校验脚本
    rr = exp["risk_registry"]
    rp = ROOT / rr["path"]
    checks.append(("RISK-REGISTRY v1", rr["sha256"],
                   sha256(rp) if rp.exists() else "<缺失>",
                   rp.exists() and sha256(rp) == rr["sha256"]))
    vp = ROOT / rr["verifier"]["path"]
    checks.append(("登记表校验脚本", rr["verifier"]["sha256"],
                   sha256(vp) if vp.exists() else "<缺失>",
                   vp.exists() and sha256(vp) == rr["verifier"]["sha256"]))

    # 3. 协议 + 逐条授权审查
    cp = ROOT / exp["case_protocol"]["path"]
    checks.append(("案例登记协议 v1", exp["case_protocol"]["sha256"],
                   sha256(cp) if cp.exists() else "<缺失>",
                   cp.exists() and sha256(cp) == exp["case_protocol"]["sha256"]))
    ar = exp["authorization_review"]
    arp = ROOT / ar["path"]
    checks.append(("逐条授权审查文件", ar["sha256"],
                   sha256(arp) if arp.exists() else "<缺失>",
                   arp.exists() and sha256(arp) == ar["sha256"]))

    # 4. 引擎
    ep = ROOT / exp["engine"]["path"]
    checks.append(("引擎 detect_x0.py", exp["engine"]["sha256"],
                   sha256(ep) if ep.exists() else "<缺失>",
                   ep.exists() and sha256(ep) == exp["engine"]["sha256"]))

    # 5. 基线 commit / tree / 工作树
    bl = exp["baseline"]
    base = ROOT / bl["path"]
    rc1, a_commit, _ = git_run("-C", str(base), "rev-parse", "HEAD")
    rc2, a_tree, _ = git_run("-C", str(base), "rev-parse", "HEAD^{tree}")
    rc3, a_status, _ = git_run("-C", str(base), "status", "--porcelain")
    checks.append(("基线 commit", bl["commit"], a_commit, rc1 == 0 and a_commit == bl["commit"]))
    checks.append(("基线 tree", bl["tree"], a_tree, rc2 == 0 and a_tree == bl["tree"]))
    dirty = [ln for ln in a_status.splitlines() if ln.strip()]
    checks.append(("基线工作树干净", "<空>",
                   "<空>" if (rc3 == 0 and not dirty) else f"{len(dirty)} 项改动/未跟踪",
                   rc3 == 0 and not dirty))

    # 6. 登记表声明 ↔ 实测
    reg = json.loads(rp.read_text(encoding="utf-8"))
    sb = reg["subject_baseline"]
    checks.append(("登记表声明 commit ↔ 实测", sb["commit"], a_commit, sb["commit"] == a_commit))
    checks.append(("登记表声明 tree ↔ 实测", sb["tree"], a_tree, sb["tree"] == a_tree))

    # 输出
    print("=== H3 统一冻结核验 ===")
    print(f"根目录: {ROOT}")
    print()
    width = max(len(c[0]) for c in checks)
    for item, e, a, ok in checks:
        print(f"[{'OK  ' if ok else 'FAIL'}] {item.ljust(width)}  期望 {str(e)[:16]}…  实测 {str(a)[:16]}…")
    fp_fail = [c[0] for c in checks if not c[3]]

    if dirty:
        print("\n=== 基线工作树脏项（逐条列出）===")
        for ln in dirty:
            print(f"  {ln}")

    if GIT_ERRORS:
        print("\n=== git 命令失败（真实 stderr 与返回码）===")
        for args, rc, err in GIT_ERRORS:
            print(f"  git {' '.join(args)}")
            print(f"    返回码: {rc}")
            print(f"    stderr : {err}")

    # 7. 已选正式案例
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
                fp = ROOT / f["path"]
                ok = fp.exists() and sha256(fp) == f["sha256"].upper()
                print(f"  [{'OK  ' if ok else 'FAIL'}] {cid} {fkey}  {f['sha256'][:16]}…")
                if not ok:
                    case_fail.append(f"{cid}: {fkey} 哈希不符")
            for ref in c.get("constraint_ids", []):
                if ref in blocked:
                    unauthorized.append(f"{cid} → {ref}（BLOCKED）")
                elif ref not in authorized:
                    unauthorized.append(f"{cid} → {ref}（未列入授权清单）")

    # 8. 逐条授权状态（读自授权审查文件）
    print("\n=== 逐条授权状态（来源：授权审查文件 v1） ===")
    print(f"AUTHORIZED（{len(authorized)}）：{sorted(authorized)}")
    print(f"BLOCKED（{len(blocked)}）：{sorted(blocked)}")
    print(f"manual_review_completed: {ar.get('manual_review_completed')}  ← 未完成前正式案例不得启动")
    if unauthorized:
        print("  未授权引用：")
        for x in unauthorized:
            print(f"    - {x}")

    # 结论与退出码
    print("\n=== 结论 ===")
    if GIT_ERRORS:
        print("  [退出码 5] git 命令执行失败（见上）")
        return 5
    if fp_fail:
        print("  指纹核验：未通过")
        for x in fp_fail:
            print(f"    - 不一致项：{x}")
        if "基线工作树干净" in fp_fail:
            print("    （基线含未提交修改或未跟踪文件 → 冻结完整性破坏）")
        print("\n  [退出码 2] 指纹不一致 / 冻结完整性破坏")
        return 2
    print("  指纹核验：全部一致（规范 / 登记表 / 协议 / 授权审查 / 引擎 / 基线 / 工作树 / 绑定 / 冻结记录）")

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
    if not ar.get("manual_review_completed"):
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
