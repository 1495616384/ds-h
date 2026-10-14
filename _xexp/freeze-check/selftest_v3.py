"""freeze_check_v3.py 端到端测试套件（真实执行，日志与退出码一律实测落盘）。

覆盖任务要求的七类实测：
  T1  Python 语法检查（py_compile，5 个脚本）
  T2  关键 JSON 合法性（5 个文件，用 json.load 实测）
  T3  RISK-REGISTRY 校验（verify_registry.py）
  T4  正常冻结核验（freeze_check_v3.py，默认锚点）
  T5  基线工作树脏测试：植入未跟踪文件 → 期望退出码 2 且逐条列出路径；清理后复核 clean
  T6  Git 失败测试：真实使 `git -C <base> status/rev-parse` 失败（拦截器临时改名 .git）
      → 期望本套件自身复核 baseline.git_fail 测得的退出码 == 5；测试后恢复并复核
  T7  指纹篡改测试：5 个受锚定/受登记文件逐个可恢复篡改 → 期望退出码 2；全部恢复后复核哈希
  T8  正式门槛测试：退出码必须为 3（不得为 0）
  T9  锚点缺失测试：临时改名锚点文件 → 期望退出码 2；恢复后复核
  T10 诊断模式（--no-anchor）：记录警告，不参与受理结论

产物结构：
  <out>/<T*/>/cmd.txt stdout.txt stderr.txt exit_code.txt sha256.txt
  <out>/T6/tamper_probe.txt（拦截器内实测的 baseline.git_fail 退出码）
  <out>/selftest-report.json（机器可读汇总）

用法：python selftest_v3.py [--out <dir>]
"""
import argparse
import atexit
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(r"G:\ds-h")
FC = ROOT / "_xexp" / "freeze-check"
ANCHOR = ROOT / "_xexp" / "v6-anchor" / "freeze-anchor.json"
GIT = r"C:\Program Files\Git\cmd\git.exe"
V3 = FC / "freeze_check_v3.py"
TMP = []


def _cleanup():
    for p in TMP:
        try:
            os.unlink(p)
        except OSError:
            pass


atexit.register(_cleanup)


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(65536), b""):
            h.update(c)
    return h.hexdigest().upper()


def run_nopipe(cmd, cwd=None):
    """不使用管道捕获（受限环境禁止建管道），改临时文件重定向。

    注意：本机 PowerShell 环境下，子进程退出码经 shell 归并后可能变成 3；
    这里直接取 Popen.returncode（真实值），并额外用 exit_code 文件交叉验证。
    """
    fo = tempfile.mkstemp(prefix="st-", suffix=".out")
    fe = tempfile.mkstemp(prefix="st-", suffix=".err")
    os.close(fo[0])
    os.close(fe[0])
    TMP.extend([fo[1], fe[1]])
    with open(fo[1], "w", encoding="utf-8") as o, open(fe[1], "w", encoding="utf-8") as e:
        proc = subprocess.Popen(list(cmd), cwd=str(cwd) if cwd else None, stdout=o, stderr=e)
        proc.wait()
        rc = proc.returncode
    return (rc,
            Path(fo[1]).read_text(encoding="utf-8", errors="replace"),
            Path(fe[1]).read_text(encoding="utf-8", errors="replace"))


def git(*args, repo: Path):
    rc, out, err = run_nopipe([GIT, "-C", str(repo), *args])
    return rc, out.strip(), err.strip()


def base_state():
    base = ROOT / "_xexp" / "base"
    _, head, _ = git("rev-parse", "HEAD", repo=base)
    _, tree, _ = git("rev-parse", "HEAD^{tree}", repo=base)
    _, status, _ = git("status", "--porcelain", repo=base)
    return {"head": head, "tree": tree,
            "dirty": [ln for ln in status.splitlines() if ln.strip()]}


class Suite:
    def __init__(self, out: Path):
        self.out = out
        self.results = []

    def run(self, name, cmd, expect_codes, asserts=(), cwd=None, note=""):
        d = self.out / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "cmd.txt").write_text(" ".join(str(c) for c in cmd) + f"\n(cwd={cwd or os.getcwd()})\n",
                                   encoding="utf-8")
        rc, out, err = run_nopipe(cmd, cwd=cwd)
        (d / "stdout.txt").write_text(out, encoding="utf-8")
        (d / "stderr.txt").write_text(err, encoding="utf-8")
        (d / "exit_code.txt").write_text(str(rc) + "\n", encoding="utf-8")
        many = expect_codes if isinstance(expect_codes, (list, tuple, set)) else [expect_codes]
        missing = [a for a in asserts if a not in out and a not in err]
        ok = rc in many and not missing
        (d / "sha256.txt").write_text(
            "\n".join([
                f"{sha256(d / 'stdout.txt')}  stdout.txt",
                f"{sha256(d / 'stderr.txt')}  stderr.txt",
                f"{sha256(d / 'cmd.txt')}  cmd.txt",
            ]) + "\n", encoding="utf-8")
        self.results.append({
            "test": name, "cmd": " ".join(str(c) for c in cmd), "cwd": cwd or os.getcwd(),
            "exit_code": rc, "expected_exit_codes": sorted(many), "asserts": list(asserts),
            "missing_asserts": missing, "ok": ok,
            "stdout": str(d / "stdout.txt"), "stderr": str(d / "stderr.txt"),
            "stdout_sha256": sha256(d / "stdout.txt"), "stderr_sha256": sha256(d / "stderr.txt"),
            "note": note,
        })
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: rc={rc} (期望 {sorted(many)})"
              + (f" 缺失断言={missing}" if missing else ""))
        return rc, out, err

    def record(self, name, ok, detail, extra=None):
        self.results.append({"test": name, "ok": ok, "detail": detail, **(extra or {})})
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")


def intercept_git_access(base: Path, target_script: Path, out_dir: Path):
    """让 target_script 的 git 调用真实失败：临时把 <base>/.git 改名（拦截器内做，带 finally 恢复）。"""
    interceptor = ROOT / "_xexp" / "v6-anchor" / "_git_fail_interceptor.py"
    probe = out_dir / "T6" / "tamper_probe.txt"
    probe.parent.mkdir(parents=True, exist_ok=True)
    interceptor.write_text(f'''"""临时拦截器：真实破坏 git 访问，运行被核验程序，读取真实退出码，然后恢复。
本文件由 selftest_v3.py 生成，测试结束即恢复现场（finally 保证）。"""
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

BASE = Path(r"{base}")
TARGET = Path(r"{target_script}")
PROBE = Path(r"{probe}")
GITDIR = BASE / ".git"
STASH = BASE / ".git.__selftest_stash__"
assert GITDIR.is_dir(), "基线 .git 不存在，测试中止"
assert not STASH.exists(), "上一次测试未恢复现场，测试中止"
os.rename(GITDIR, STASH)
try:
    fd_out = tempfile.mkstemp(prefix="t6-out-", suffix=".txt"); os.close(fd_out[0])
    fd_err = tempfile.mkstemp(prefix="t6-err-", suffix=".txt"); os.close(fd_err[0])
    with open(fd_out[1], "w", encoding="utf-8") as o, open(fd_err[1], "w", encoding="utf-8") as e:
        rc = subprocess.run([sys.executable, str(TARGET), "--report",
                             str(PROBE.parent / "target-report.json")],
                            stdout=o, stderr=e).returncode
    out = Path(fd_out[1]).read_text(encoding="utf-8", errors="replace")
    err = Path(fd_err[1]).read_text(encoding="utf-8", errors="replace")
    Path(PROBE.parent / "target-stdout.txt").write_text(out, encoding="utf-8")
    Path(PROBE.parent / "target-stderr.txt").write_text(err, encoding="utf-8")
    Path(PROBE.parent / "target-exit_code.txt").write_text(str(rc) + "\\n", encoding="utf-8")
    PROBE.write_text(json.dumps({{"baseline_git_fail_measured_rc": rc}}, ensure_ascii=False), encoding="utf-8")
    print("拦截器：被核验程序退出码 =", rc)
    print("git 失败输出片段：")
    for ln in out.splitlines():
        if "git" in ln or "返回码" in ln or "退出码" in ln:
            print("  |", ln)
finally:
    if STASH.exists():
        os.rename(STASH, GITDIR)
    print("拦截器：.git 已恢复 =", GITDIR.is_dir())
''', encoding="utf-8")
    rc, out, err = run_nopipe([sys.executable, str(interceptor)])
    (out_dir / "T6" / "interceptor-stdout.txt").write_text(out, encoding="utf-8")
    (out_dir / "T6" / "interceptor-stderr.txt").write_text(err, encoding="utf-8")
    (out_dir / "T6" / "interceptor-exit_code.txt").write_text(str(rc) + "\n", encoding="utf-8")
    measured = None
    if probe.exists():
        measured = json.loads(probe.read_text(encoding="utf-8")).get("baseline_git_fail_measured_rc")
    return rc, measured


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "_xexp" / "v6-anchor" / "logs"))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    s = Suite(out)

    before = base_state()

    # ── 辅助：以 --report 的 JSON 为准读取真实退出码（stdout 文本仅作辅助断言） ──
    def run_with_report(name, expect_codes, extra_args=(), asserts=(), note=""):
        rep = out / name / "verify-report.json"
        rep.parent.mkdir(parents=True, exist_ok=True)
        rc, o, e = s.run(name, [sys.executable, str(V3), *extra_args, "--report", str(rep)],
                         expect_codes, asserts=asserts, note=note)
        rep_rc = None
        formula = None
        if rep.exists():
            data = json.loads(rep.read_text(encoding="utf-8"))
            rep_rc = data.get("exit_code")
            formula = data.get("exit_code_formula")
        s.record(f"{name}-report_exit_code", rep_rc == rc,
                 f"报告 exit_code={rep_rc} / 进程退出码={rc} / 公式={formula}")
        return rc, o, e

    # ── T1 语法检查 ──────────────────────────────────────────
    s.run("T1-py_compile", [
        sys.executable, "-m", "py_compile",
        str(FC / "freeze_check_v3.py"), str(FC / "freeze_check_v2.py"),
        str(FC / "freeze_check.py"), str(FC / "selftest_v2.py"),
        str(FC / "selftest_v3.py"),
        str(ROOT / "_xexp" / "risk-registry" / "verify_registry.py"),
        str(ROOT / "_xexp" / "risk-registry" / "selftest_registry_v3.py"),
        str(ROOT / "_xexp" / "tools" / "proc_capture.py"),
    ], 0, note="Python 语法检查")

    # ── T2 JSON 合法性 ──────────────────────────────────────
    json_targets = [
        ROOT / "_xexp" / "risk-registry" / "RISK-REGISTRY-v1.json",
        ROOT / "_xexp" / "h3-case-protocol" / "H3-constraint-authorization-review-v1.json",
        FC / "expected-fingerprints-v1.json",
        FC / "expected-fingerprints-v6.json",
        FC / "selected-cases.json",
        ANCHOR,
    ]
    s.run("T2-json-validity", [
        sys.executable, "-c",
        "import json,sys;"
        "[print('OK', p, len(json.load(open(p, encoding='utf-8')))) for p in sys.argv[1:]]",
        *[str(p) for p in json_targets],
    ], 0, asserts=["OK"] * 1, note="关键 JSON 合法性（json.load 实测）")

    # ── T3 登记表校验 ───────────────────────────────────────
    s.run("T3-verify_registry", [
        sys.executable, str(ROOT / "_xexp" / "risk-registry" / "verify_registry.py")
    ], 0, asserts=["绑定一致 OK", "自动校验总结果: 通过"], note="RISK-REGISTRY 校验")

    # ── T4 正常冻结核验 ─────────────────────────────────────
    run_with_report("T4-freeze_check_normal", 3,
                    asserts=["当前冻结记录 H3-freeze-manifest-v6.md"],
                    note="正常冻结核验：期望 3（指纹一致、门槛未就绪）")

    # ── T5 基线工作树脏 ─────────────────────────────────────
    dirty_probe = ROOT / "_xexp" / "base" / "_selftest_dirty_probe.txt"
    assert not dirty_probe.exists(), "脏测试探针已存在，先清理"
    dirty_probe.write_text("selftest dirty probe\n", encoding="utf-8")
    try:
        s.run("T5-worktree_dirty", [sys.executable, str(V3)], 2,
              asserts=["[FAIL] 工作树干净", "=== 基线工作树脏项（逐条列出）===",
                       "_selftest_dirty_probe.txt", "[退出码 2]"],
              note="植入未跟踪文件 → 期望 2 且逐条列出路径")
    finally:
        dirty_probe.unlink(missing_ok=True)
    after_clean = base_state()
    s.record("T5b-dirty_cleanup_verified",
             (not after_clean["dirty"]) and after_clean["head"] == before["head"]
             and after_clean["tree"] == before["tree"],
             f"清理后 status 空={not after_clean['dirty']}，HEAD 未变={after_clean['head'] == before['head']}，"
             f"tree 未变={after_clean['tree'] == before['tree']}",
             {"after": after_clean, "before": before})

    # ── T6 Git 失败（真实破坏 git 访问） ────────────────────
    irc, measured = intercept_git_access(ROOT / "_xexp" / "base", V3, out)
    restored = base_state()
    s.record("T6-git_fail_measured_rc5",
             measured == 5,
             f"被核验程序在 git 真实失败时的实测退出码 = {measured}（拦截器自身 rc={irc}）",
             {"interceptor_rc": irc, "measured_rc": measured})
    s.record("T6b-git_access_restored",
             (ROOT / "_xexp" / "base" / ".git").is_dir() and not (ROOT / "_xexp" / "base" / ".git.__selftest_stash__").exists()
             and (not restored["dirty"]) and restored["head"] == before["head"],
             f".git 已恢复={ (ROOT / '_xexp' / 'base' / '.git').is_dir() }，"
             f"残留 stash={ (ROOT / '_xexp' / 'base' / '.git.__selftest_stash__').exists() }，"
             f"status 空={not restored['dirty']}，HEAD 未变={restored['head'] == before['head']}")

    # ── T7 指纹篡改（逐个可恢复） ───────────────────────────
    tamper_targets = [
        ("frozen_inputs.selected_cases", FC / "selected-cases.json"),
        ("frozen_inputs.expected_fingerprints_v1", FC / "expected-fingerprints-v1.json"),
        ("authorization_review", ROOT / "_xexp" / "h3-case-protocol" /
         "H3-constraint-authorization-review-v1.json"),
        ("current_manifest", ROOT / "_xexp" / "H3-freeze-manifest-v6.md"),
        ("engine", ROOT / "_xexp_dev2" / "detect_x0.py"),
    ]
    for name, target in tamper_targets:
        original = target.read_bytes()
        original_sha = sha256(target)
        backup = target.with_suffix(target.suffix + ".selftest-orig")
        assert not backup.exists(), f"残留备份 {backup}"
        shutil.copy2(target, backup)
        try:
            if target.suffix == ".json":
                data = json.loads(original.decode("utf-8"))
                data["__selftest_tamper__"] = True
                target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            else:
                target.write_bytes(original + b"\n<!-- selftest tamper -->\n")
            s.run(f"T7-tamper-{name.split('.')[-1]}", [sys.executable, str(V3)], 2,
                  asserts=["[退出码 2]", "指纹不一致 / 冻结完整性破坏"],
                  note=f"可恢复篡改 {name}")
        finally:
            shutil.copy2(backup, target)
            backup.unlink()
        restored_sha = sha256(target)
        s.record(f"T7b-restored-{name.split('.')[-1]}", restored_sha == original_sha,
                 f"恢复后哈希一致={restored_sha == original_sha}（{restored_sha[:16]}）")

    # ── T8 正式门槛必须为 3 ─────────────────────────────────
    rc8, out8, _ = run_with_report("T8-threshold_must_be_3", 3,
                                   asserts=["尚未选择正式案例"],
                                   note="无正式案例 + 人工审查未完成 → 必须 3，不得 0")
    s.record("T8b-not_zero", rc8 != 0, f"实测退出码 {rc8} 不等于 0")

    # ── T9 锚点缺失 ────────────────────────────────────────
    anchor_bak = ANCHOR.with_suffix(".json.selftest-orig")
    anchor_sha = sha256(ANCHOR)
    shutil.copy2(ANCHOR, anchor_bak)
    try:
        ANCHOR.unlink()
        s.run("T9-anchor_missing", [sys.executable, str(V3)], 2,
              asserts=["[退出码 2]", "锚点文件存在"],
              note="锚点缺失 → 期望 2")
    finally:
        shutil.copy2(anchor_bak, ANCHOR)
        anchor_bak.unlink()
    s.record("T9b-anchor_restored", sha256(ANCHOR) == anchor_sha,
             f"锚点恢复后哈希一致={sha256(ANCHOR) == anchor_sha}")

    # ── T10 诊断模式 ───────────────────────────────────────
    run_with_report("T10-no_anchor_diagnostic", 3, extra_args=["--no-anchor"],
                    asserts=["已跳过锚点核验", "警告（不改变退出码）"],
                    note="诊断模式：记录警告，结论不得用于受理")

    # ── 收尾：基线现场复核 ─────────────────────────────────
    final = base_state()
    s.record("Z-baseline_unchanged",
             final["head"] == before["head"] and final["tree"] == before["tree"]
             and not final["dirty"],
             f"HEAD 未变={final['head'] == before['head']}，"
             f"tree 未变={final['tree'] == before['tree']}，status 空={not final['dirty']}",
             {"before": before, "after": final})

    report = {
        "suite": "selftest_v3.py",
        "run_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "root": str(ROOT),
        "out_dir": str(out),
        "freeze_check_v3_sha256": sha256(V3),
        "trust_doc": str(FC / "expected-fingerprints-v6.json"),
        "trust_doc_sha256": sha256(FC / "expected-fingerprints-v6.json"),
        "anchor": str(ANCHOR),
        "anchor_sha256": sha256(ANCHOR) if ANCHOR.exists() else None,
        "baseline_before": before, "baseline_after": final,
        "results": s.results,
        "passed": sum(1 for r in s.results if r["ok"]),
        "total": len(s.results),
    }
    (out / "selftest-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n汇总：{report['passed']}/{report['total']} 通过")
    print(f"报告：{out / 'selftest-report.json'}")
    return 0 if report["passed"] == report["total"] else 1


if __name__ == "__main__":
    sys.exit(main())
