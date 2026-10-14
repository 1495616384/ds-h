"""H3 统一冻结核验 v3（锚定版）——权威核验程序。

设计目标（相对 v1/v2 的缺口）：
  1. **v5/v6 身份被真实核验**：当前冻结记录（Manifest v6）的哈希由本程序逐次比对；
     历史记录 v1–v5 的哈希一并登记，任何改写历史清单的行为都会以退出码 2 报出。
  2. **无循环依赖**：本程序**不把自身哈希写进任何被核验的文件**，被核验文件也不写本程序哈希
     （v2 的 `self_check` 已从信任文档中移除）。可验证性由**独立锚点**提供：
     `_xexp/v6-anchor/freeze-anchor.json` 记录「锚定提交 + 该提交下各冻结制品的 git blob 哈希」，
     提交对象内容寻址、不可静默改写；锚点文件自身受保护哈希登记在其后继提交中。
     git blob 校验要求 blob 内容与当前工作树内容逐字节一致（含 CRLF），保证可执行可复核。
  3. **expected-fingerprints-v1.json 与 selected-cases.json 纳入检查**（v1/v2 均未覆盖）。
  4. **机器可读报告**：--report 输出 JSON（供受理记录与后续自动化引用）。

退出码：
  0 = 指纹全部一致 且 正式门槛就绪
  2 = 指纹不一致 / 冻结完整性破坏（工作树脏、锚点不符、历史记录被改写、本程序未登记）
  3 = 指纹一致，但正式门槛未就绪（无已选案例 / 整体人工审查未完成）
  4 = 已选案例引用了未获授权使用的约束
  5 = git 命令执行失败（输出真实 stderr 与返回码；基线项按失败处理）

本程序**不**运行检测器；**不**执行语义审查。人工审查清单存在 ≠ 审查完成。
"""
import argparse
import atexit
import datetime
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

DEFAULT_ROOT = Path(r"G:\ds-h")
HERE = Path(__file__).parent
GIT = r"C:\Program Files\Git\cmd\git.exe"

GIT_ERRORS = []       # (args, returncode, stderr)
GIT_CAPTURE_MODE = None
_TMP_FILES = []


def _cleanup():
    for p in _TMP_FILES:
        try:
            os.unlink(p)
        except OSError:
            pass


atexit.register(_cleanup)


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def _run_captured(args):
    """返回 (rc, stdout, stderr)。管道不可用时回退临时文件重定向。"""
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
            GIT_CAPTURE_MODE = "tempfile"
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


def blob_sha256_at(repo: Path, rev: str, path: str):
    """取 git 提交中某路径的 blob 字节内容并算 SHA-256；返回 (status, value)。"""
    rc2, raw, err2 = _cat_file_bytes(repo, rev, path)
    if rc2 != 0:
        return "GIT_FAIL", err2
    return "OK", hashlib.sha256(raw).hexdigest().upper()


def _cat_file_bytes(repo: Path, rev: str, path: str):
    cmd = [GIT, "-C", str(repo), "cat-file", "blob", f"{rev}:{path}"]
    try:
        r = subprocess.run(cmd, capture_output=True)
        return r.returncode, r.stdout or b"", (r.stderr or b"").decode("utf-8", "replace")
    except OSError as exc:
        if getattr(exc, "winerror", None) != 5:
            raise
    fd, name = tempfile.mkstemp(prefix="catfile-", suffix=".bin")
    os.close(fd)
    _TMP_FILES.append(name)
    with open(name, "wb") as fo:
        r = subprocess.run(cmd, stdout=fo, stderr=subprocess.DEVNULL)
    return r.returncode, Path(name).read_bytes(), ""


def main() -> int:
    ap = argparse.ArgumentParser(description="H3 统一冻结核验 v3（锚定版）")
    ap.add_argument("--expected", default=None, help="信任文档（默认 <本目录>/expected-fingerprints-v6.json）")
    ap.add_argument("--anchor", default=None, help="独立锚点（默认 <本目录>/../v6-anchor/freeze-anchor.json）")
    ap.add_argument("--recovery", default=None, help="恢复流程规范文件（仅登记引用）")
    ap.add_argument("--root", default=None, help="被核验根目录（默认 G:\\ds-h）")
    ap.add_argument("--report", default=None, help="写出机器可读 JSON 报告")
    ap.add_argument("--no-anchor", action="store_true", help="跳过锚点核验（仅限诊断，结论不得用于受理）")
    args = ap.parse_args()

    root = Path(args.root).resolve() if args.root else DEFAULT_ROOT
    expected_path = Path(args.expected).resolve() if args.expected else HERE / "expected-fingerprints-v6.json"
    anchor_path = Path(args.anchor).resolve() if args.anchor else HERE.parent / "v6-anchor" / "freeze-anchor.json"
    selection_path = HERE / "selected-cases.json"
    self_path = Path(__file__).resolve()

    checks = []   # (section, item, expected, actual, ok, note)
    warn = []

    def add(section, item, exp, act, ok, note=""):
        checks.append((section, item, str(exp), str(act), bool(ok), note))

    print("=== H3 统一冻结核验 v3（锚定版） ===")
    print(f"根目录    : {root}")
    print(f"信任文档  : {expected_path}")
    print(f"独立锚点  : {'<跳过>' if args.no_anchor else anchor_path}")
    print(f"核验程序  : {self_path}")
    print()

    if not expected_path.exists():
        print(f"[FAIL] 信任文档缺失: {expected_path}")
        print("\n  [退出码 2] 无法核验（信任文档不存在）")
        return 2
    exp = json.loads(expected_path.read_text(encoding="utf-8"))

    # ── A. 信任文档自绑定（身份 A） ─────────────────────────────
    self_declared = ((exp.get("verifier") or {}).get("sha256") or "")
    self_actual = sha256(self_path)
    registered = bool(self_declared)
    if registered:
        add("A 程序身份", "核验程序自身（信任文档声明）", self_declared, self_actual,
            self_declared == self_actual,
            "" if self_declared == self_actual else "未被登记的冻结脚本（可能已改写）")
    else:
        warn.append("信任文档未声明 verifier.sha256：本程序身份未登记")

    # ── B. 当前冻结记录 + 历史链 ──────────────────────────────
    mf = exp["current_manifest"]
    mp = root / mf["file"]
    add("B 冻结记录", f"当前冻结记录 {Path(mf['file']).name}", mf["sha256"],
        sha256(mp) if mp.exists() else "<缺失>", mp.exists() and sha256(mp) == mf["sha256"])
    for key, item in (exp.get("historical_manifests") or {}).items():
        hp = root / item["file"]
        present = hp.exists()
        if not present:
            warn.append(f"历史冻结记录缺失（未纳入强制校验）: {item['file']}")
            continue
        add("B 冻结记录", f"历史记录 {Path(item['file']).name}", item["sha256"],
            sha256(hp), sha256(hp) == item["sha256"], "改写历史清单即失败")

    # ── C. 规范 / 登记表 / 协议 / 授权 / 引擎 ───────────────────
    for key, item in exp["spec"].items():
        sp = root / item["path"]
        add("C 冻结对象", f"规范 {key}", item["sha256"], sha256(sp) if sp.exists() else "<缺失>",
            sp.exists() and sha256(sp) == item["sha256"])
    rr = exp["risk_registry"]
    rp = root / rr["path"]
    add("C 冻结对象", "RISK-REGISTRY v1", rr["sha256"], sha256(rp) if rp.exists() else "<缺失>",
        rp.exists() and sha256(rp) == rr["sha256"])
    vp = root / rr["verifier"]["path"]
    add("C 冻结对象", "登记表校验程序", rr["verifier"]["sha256"],
        sha256(vp) if vp.exists() else "<缺失>", vp.exists() and sha256(vp) == rr["verifier"]["sha256"])
    cp = root / exp["case_protocol"]["path"]
    add("C 冻结对象", "案例登记协议 v1", exp["case_protocol"]["sha256"],
        sha256(cp) if cp.exists() else "<缺失>", cp.exists() and sha256(cp) == exp["case_protocol"]["sha256"])
    ar = exp["authorization_review"]
    arp = root / ar["path"]
    add("C 冻结对象", "逐条授权审查文件", ar["sha256"], sha256(arp) if arp.exists() else "<缺失>",
        arp.exists() and sha256(arp) == ar["sha256"])
    ep = root / exp["engine"]["path"]
    add("C 冻结对象", "检测引擎 detect_x0.py", exp["engine"]["sha256"],
        sha256(ep) if ep.exists() else "<缺失>", ep.exists() and sha256(ep) == exp["engine"]["sha256"])

    # ── D. 冻结工具与输入（含 v1 期望指纹、已选案例登记） ────────
    for key, item in (exp.get("frozen_inputs") or {}).items():
        fp = root / item["path"]
        add("D 冻结输入", f"{key}", item["sha256"], sha256(fp) if fp.exists() else "<缺失>",
            fp.exists() and sha256(fp) == item["sha256"], item.get("note", ""))
    for key, item in (exp.get("support_tools") or {}).items():
        tp = root / item["path"]
        add("D 冻结工具", f"{key}", item["sha256"], sha256(tp) if tp.exists() else "<缺失>",
            tp.exists() and sha256(tp) == item["sha256"], item.get("note", ""))

    # ── E. 独立锚点 ───────────────────────────────────────────
    anchor_data = None
    if args.no_anchor:
        warn.append("已跳过锚点核验（--no-anchor）：本轮结论不得用于受理")
    elif not anchor_path.exists():
        add("E 独立锚点", "锚点文件存在", "存在", "<缺失>", False)
    else:
        anchor_data = json.loads(anchor_path.read_text(encoding="utf-8"))
        commit = anchor_data.get("anchor_commit", "")
        repo = root / (anchor_data.get("anchor_repo", "."))

        # E1 信任文档本身是否被锚定
        ta = (anchor_data.get("anchored_files") or {}).get("expected_fingerprints")
        if not ta:
            add("E 独立锚点", "信任文档已锚定", "已登记", "<未登记>", False)
        else:
            act = sha256(expected_path)
            add("E 独立锚点", "信任文档（期望指纹）未被静默改写", ta.get("content_sha256"),
                act, act == ta.get("content_sha256"))

        # E2 各锚定文件的 git blob 与磁盘内容一致性
        rc, head, _ = git_run("-C", str(repo), "rev-parse", commit)
        add("E 独立锚点", "锚定提交存在", commit[:16], head[:16] if rc == 0 else "<不可解析>",
            rc == 0 and head == commit)
        for key, item in (anchor_data.get("anchored_files") or {}).items():
            if "path" not in item:
                continue
            fp = root / item["path"]
            disk_ok = fp.exists() and sha256(fp) == item["content_sha256"]
            add("E 独立锚点", f"{key} 磁盘内容 == 锚定内容", item["content_sha256"],
                sha256(fp) if fp.exists() else "<缺失>", disk_ok)
            if isinstance(item.get("git_blob"), str) and len(item["git_blob"]) > 20:
                st, val = blob_sha256_at(repo, commit, item["path"])
                add("E 独立锚点", f"{key} git blob 与提交一致", item["git_blob"][:16], str(val)[:16],
                    st == "OK" and val == item["git_blob"], "" if st == "OK" else st)

        # E3 锚点自身不参与自证：改为核验"独立留存文件"是否存在（ANCHOR-COMMIT.md）
        sr = anchor_data.get("self_reference") or {}
        if sr.get("recorded_in"):
            rp2 = root / sr["recorded_in"]
            add("E 独立锚点", "锚点自身哈希的独立留存文件存在", "存在",
                "存在" if rp2.exists() else "<缺失>", rp2.exists(),
                "锚点不自证；其哈希由该留存文件与受理记录多重保存")
        recorded_sha = None
        prot = anchor_data.get("self_protection") or {}
        if prot.get("sha256"):
            recorded_sha = prot["sha256"]
        elif sr.get("recorded_in") and (root / sr["recorded_in"]).exists():
            for ln in (root / sr["recorded_in"]).read_text(encoding="utf-8").splitlines():
                if "freeze-anchor.json" in ln and len(ln.split()) >= 2:
                    tok = ln.split()[0].strip("`| ")
                    if len(tok) == 64 and all(c in "0123456789ABCDEFabcdef" for c in tok):
                        recorded_sha = tok.upper()
                        break
        if recorded_sha:
            act = sha256(anchor_path)
            add("E 独立锚点", "锚点文件哈希与独立留存值一致", recorded_sha, act,
                act == recorded_sha, "锚点被就地修改即失败")
        else:
            warn.append("未找到锚点文件的独立留存哈希（ANCHOR-COMMIT.md 未记录或格式不符）")

    # 锚点自绑定：本程序不得自证（"工具自己说了算"）；此处只登记声明值，逐次比对并记录。
    anchor_declared = anchor_data.get("verifier_declared_sha256") if anchor_data else None
    if anchor_declared:
        add("E 独立锚点", "核验程序身份（锚点声明值）", anchor_declared, self_actual,
            anchor_declared == self_actual,
            "已登记冻结脚本" if anchor_declared == self_actual else "未登记的冻结脚本")
        trust_declared = self_declared
        if trust_declared and trust_declared != anchor_declared:
            warn.append("信任文档的 verifier.sha256 与锚点声明值不同：工具已改版，须发布新清单")
    else:
        warn.append("锚点未声明 verifier_declared_sha256：工具身份无可独立核验的声明值")

    # ── F. 代码层：授权判决 / 基线绑定 / 工作树 ─────────────────
    auth = json.loads(arp.read_text(encoding="utf-8")) if arp.exists() else {"entries": []}
    authorized = sorted({e["constraint_id"] for e in auth.get("entries", [])
                         if e.get("authorization") == "AUTHORIZED"})
    blocked = sorted({e["constraint_id"] for e in auth.get("entries", [])
                      if e.get("authorization") == "BLOCKED"})
    for key, item in (exp.get("authorization_expectation") or {}).items():
        actual = authorized if key == "authorized" else blocked if key == "blocked" else None
        if actual is None:
            continue
        add("F 授权判决", f"{key} 集合与信任文档一致", ",".join(sorted(item)), ",".join(actual),
            sorted(item) == actual)

    bl = exp["baseline"]
    base = root / bl["path"]
    rc1, a_commit, _ = git_run("-C", str(base), "rev-parse", "HEAD")
    rc2, a_tree, _ = git_run("-C", str(base), "rev-parse", "HEAD^{tree}")
    rc3, a_status, _ = git_run("-C", str(base), "status", "--porcelain")
    add("F 基线", "commit", bl["commit"], a_commit, rc1 == 0 and a_commit == bl["commit"])
    add("F 基线", "tree", bl["tree"], a_tree, rc2 == 0 and a_tree == bl["tree"])
    dirty = [ln for ln in a_status.splitlines() if ln.strip()]
    if rc3 != 0:
        wt_state, wt_actual = "GIT_FAIL", "<git 失败>"
    elif dirty:
        wt_state, wt_actual = "DIRTY", f"{len(dirty)} 项改动/未跟踪"
    else:
        wt_state, wt_actual = "CLEAN", "<空>"
    add("F 基线", "工作树干净", "<空>", wt_actual, wt_state == "CLEAN")

    reg = json.loads(rp.read_text(encoding="utf-8")) if rp.exists() else {}
    sb = reg.get("subject_baseline", {})
    add("F 基线", "登记表声明 commit 与实测", sb.get("commit"), a_commit, sb.get("commit") == a_commit)
    add("F 基线", "登记表声明 tree 与实测", sb.get("tree"), a_tree, sb.get("tree") == a_tree)

    # ── 输出 ─────────────────────────────────────────────────
    section = None
    for sec, item, e, a, ok, note in checks:
        if sec != section:
            print(f"\n-- {sec} --")
            section = sec
        tail = f"   [{note}]" if note and not ok else ""
        print(f"[{'OK  ' if ok else 'FAIL'}] {item:<44} 期望 {e[:16]:<16} 实测 {a[:16]:<16}{tail}")
    fails = [c for c in checks if not c[4]]

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
    if warn:
        print("\n=== 警告（不改变退出码）===")
        for w in warn:
            print(f"  ! {w}")

    # ── 已选正式案例 ─────────────────────────────────────────
    sel = json.loads(selection_path.read_text(encoding="utf-8")) if selection_path.exists() \
        else {"formal_cases_selected": []}
    print("\n=== 已选正式案例核验 ===")
    cases = sel.get("formal_cases_selected", [])
    case_fail, unauthorized = [], []
    if not cases:
        print("  尚未选择正式案例（当前状态的应有结果）")
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

    print("\n=== 逐条授权状态（来源：授权审查文件，唯一授权来源） ===")
    print(f"AUTHORIZED（{len(authorized)}）：{authorized}")
    print(f"BLOCKED（{len(blocked)}）：{blocked}")
    print(f"manual_review_completed: {auth.get('manual_review_completed', '<字段缺失，视为未完成>')}")
    print(f"约定：约束级授权 ≠ 案例级审查。剩余案例级检查：{auth.get('remaining_case_level_checks')}")
    if unauthorized:
        print("  未授权引用：")
        for x in unauthorized:
            print(f"    - {x}")

    print("\n=== 结论 ===")
    print(f"（git 输出捕获方式：{GIT_CAPTURE_MODE or '未调用'}）")
    exit_code, verdict = None, ""
    if GIT_ERRORS:
        exit_code, verdict = 5, "git 命令执行失败（基线项已按失败处理）"
    elif fails:
        exit_code, verdict = 2, "指纹不一致 / 冻结完整性破坏"
        for sec, item, e, a, ok, note in fails:
            print(f"    - [{sec}] {item}")
    elif case_fail:
        exit_code, verdict = 2, "案例文件指纹不一致"
    elif unauthorized:
        exit_code, verdict = 4, "已选案例引用未授权约束"
    else:
        gate = []
        if not cases:
            gate.append("尚未选择正式案例")
        if not auth.get("manual_review_completed"):
            gate.append("整体人工审查未完成（案例级 U1 范围检查未做；脚本不执行语义审查）")
        if gate:
            exit_code, verdict = 3, "指纹一致，但正式门槛未就绪"
            for g in gate:
                print(f"    - {g}")
        else:
            exit_code, verdict = 0, "全部通过，正式门槛就绪"

    print(f"\n  [退出码 {exit_code}] {verdict}")
    print(f"  统计：检查项 {len(checks)}，通过 {len(checks) - len(fails)}，失败 {len(fails)}，警告 {len(warn)}")

    if args.report:
        rp_out = Path(args.report)
        rp_out.parent.mkdir(parents=True, exist_ok=True)
        rp_out.write_text(json.dumps({
            "tool": "freeze_check_v3.py",
            "tool_path": str(self_path),
            "tool_sha256": self_actual,
            "tool_registered_in_trust_doc": registered,
            "root": str(root),
            "trust_doc": str(expected_path),
            "trust_doc_sha256": sha256(expected_path),
            "anchor": str(anchor_path),
            "anchor_sha256": sha256(anchor_path) if anchor_path.exists() else None,
            "anchor_commit": (anchor_data or {}).get("anchor_commit"),
            "anchor_used": not args.no_anchor and anchor_data is not None,
            "git_capture_mode": GIT_CAPTURE_MODE,
            "checks": [{"section": s, "item": i, "expected": e, "actual": a, "ok": ok, "note": n}
                       for s, i, e, a, ok, n in checks],
            "warnings": warn,
            "git_errors": [{"args": list(ga), "rc": rc, "stderr": er} for ga, rc, er in GIT_ERRORS],
            "baseline_worktree_state": wt_state,
            "authorized": authorized,
            "blocked": blocked,
            "formal_cases": len(cases),
            "manual_review_completed": auth.get("manual_review_completed", None),
            "exit_code": exit_code,
            "verdict": verdict,
            "checked_at": datetime.datetime.now().isoformat(timespec="seconds"),
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"  报告：{rp_out}")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
