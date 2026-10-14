"""freeze_check_v2.py 自测套件（隔离根目录，绝不触碰真实基线仓库）。

覆盖五项可回验缺陷：

  T1 干净仓库            -> 基线三项 OK，退出码 3（指纹一致、门槛未就绪）
  T2 工作树脏（未跟踪）  -> "基线工作树干净" FAIL + 逐条列出脏项，退出码 2
  T3 仓库不存在（git 失败）-> 基线项标注 <git 失败>，退出码 5
  T4 脚本自身被改写      -> "核验脚本自身" FAIL，退出码 2
  T5 管道被禁环境中捕获  -> git 输出捕获回退临时文件，仍能拿到真实输出（F-5）

实现说明：本套件自身也**不使用管道**捕获子进程输出（受限沙箱禁止创建管道，
WinError 5），一律写入临时文件后读取。

用法：python selftest_v2.py
"""
import atexit
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

HERE = Path(__file__).resolve().parent
REAL_SCRIPT = HERE / "freeze_check_v2.py"
GIT = r"C:\Program Files\Git\cmd\git.exe"
SANDBOX = HERE / "_selftest-sandbox"
FAKE_ROOT = SANDBOX / "fk"
FAKE_BASE = FAKE_ROOT / "_xexp" / "base"
FAKE_EXPECTED = SANDBOX / "selftest-expected.json"
FAKE_SELECTION = SANDBOX / "selftest-selected.json"

_TMP = []


def _cleanup():
    for p in _TMP:
        try:
            os.unlink(p)
        except OSError:
            pass


atexit.register(_cleanup)


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest().upper()


def run_nopipe(cmd):
    """不依赖管道的子进程执行：输出重定向到临时文件。"""
    fo = tempfile.mkstemp(prefix="selftest-out-", suffix=".txt")
    fe = tempfile.mkstemp(prefix="selftest-err-", suffix=".txt")
    os.close(fo[0])
    os.close(fe[0])
    _TMP.extend([fo[1], fe[1]])
    with open(fo[1], "w", encoding="utf-8") as o, open(fe[1], "w", encoding="utf-8") as e:
        rc = subprocess.run(cmd, stdout=o, stderr=e).returncode
    return (rc,
            Path(fo[1]).read_text(encoding="utf-8", errors="replace"),
            Path(fe[1]).read_text(encoding="utf-8", errors="replace"))


def git(*args, cwd=None):
    cmd = [GIT, *args] if cwd is None else [GIT, "-C", str(cwd), *args]
    rc, out, err = run_nopipe(cmd)
    assert rc == 0, f"git 失败 {args}: {err}"
    return out.strip()


def build_fake_root():
    if SANDBOX.exists():
        shutil.rmtree(SANDBOX, ignore_errors=True)
    FAKE_ROOT.mkdir(parents=True, exist_ok=True)

    files = {
        "_xexp/manifest.json": '{"manifest": "selftest-v1"}',
        "spec.md": "# spec",
        "_xexp/risk-registry/RISK-REGISTRY-v1.json": '{"entries": [], "subject_baseline": {}}',
        "_xexp/risk-registry/verify_registry.py": "# verifier",
        "_xexp/h3-case-protocol/H3-case-registration-protocol-v1.md": "# protocol",
        "_xexp/h3-case-protocol/H3-constraint-authorization-review-v1.json":
            json.dumps({"manual_review_completed": False,
                        "entries": [{"constraint_id": "PI-001", "authorization": "AUTHORIZED"},
                                    {"constraint_id": "CV-001", "authorization": "BLOCKED"}]},
                       ensure_ascii=False),
        "_xexp_dev2/detect_x0.py": "# engine",
    }
    for rel, content in files.items():
        p = FAKE_ROOT / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    FAKE_BASE.mkdir(parents=True, exist_ok=True)
    # 自测使用的脚本副本与授权审查文件副本（脚本从自身目录读 selected-cases.json）
    sandbox_script = SANDBOX / "selftest-freeze_check_v2.py"
    sandbox_script.write_text(REAL_SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
    (SANDBOX / "selected-cases.json").write_text(
        json.dumps({"formal_cases_selected": []}, ensure_ascii=False), encoding="utf-8")
    return sandbox_script


def write_expected(self_sha: str, base_path: str, commit: str, tree: str, reg_sha: str):
    exp = {
        "fingerprints_version": "selftest",
        "bound_freeze_record": {"file": "_xexp/manifest.json",
                                "sha256": sha256(FAKE_ROOT / "_xexp/manifest.json")},
        "self_check": {"path": "selftest-freeze_check_v2.py", "sha256": self_sha},
        "spec": {"v1_2_1_current": {"path": "spec.md", "sha256": sha256(FAKE_ROOT / "spec.md")}},
        "risk_registry": {
            "path": "_xexp/risk-registry/RISK-REGISTRY-v1.json",
            "sha256": reg_sha,
            "verifier": {"path": "_xexp/risk-registry/verify_registry.py",
                         "sha256": sha256(FAKE_ROOT / "_xexp/risk-registry/verify_registry.py")},
        },
        "case_protocol": {
            "path": "_xexp/h3-case-protocol/H3-case-registration-protocol-v1.md",
            "sha256": sha256(FAKE_ROOT / "_xexp/h3-case-protocol/H3-case-registration-protocol-v1.md")},
        "authorization_review": {
            "path": "_xexp/h3-case-protocol/H3-constraint-authorization-review-v1.json",
            "sha256": sha256(FAKE_ROOT / "_xexp/h3-case-protocol/H3-constraint-authorization-review-v1.json")},
        "engine": {"path": "_xexp_dev2/detect_x0.py",
                   "sha256": sha256(FAKE_ROOT / "_xexp_dev2/detect_x0.py")},
        "baseline": {"path": base_path, "commit": commit, "tree": tree,
                     "worktree_must_be_clean": True},
    }
    FAKE_EXPECTED.write_text(json.dumps(exp, ensure_ascii=False, indent=2), encoding="utf-8")
    return exp


def set_registry_baseline(commit: str, tree: str) -> str:
    p = FAKE_ROOT / "_xexp/risk-registry/RISK-REGISTRY-v1.json"
    p.write_text(json.dumps({"entries": [],
                             "subject_baseline": {"commit": commit, "tree": tree}},
                            ensure_ascii=False), encoding="utf-8")
    return sha256(p)


def run_case(name, script_path: Path, expect_rc: int, expect_substrings):
    rc, out, err = run_nopipe([sys.executable, str(script_path),
                               "--expected", str(FAKE_EXPECTED),
                               "--root", str(FAKE_ROOT)])
    text = out + err
    missing = [s for s in expect_substrings if s not in text]
    ok = rc == expect_rc and not missing
    print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    print(f"        退出码 期望 {expect_rc} / 实测 {rc}")
    if missing:
        print(f"        缺失断言: {missing}")
        for ln in text.splitlines():
            if ("FAIL" in ln or "基线" in ln or "自身" in ln or "退出码" in ln
                    or "捕获方式" in ln):
                print(f"           | {ln}")
    return ok


def main() -> int:
    results = []
    sandbox_script = build_fake_root()
    script_sha = sha256(sandbox_script)

    # ---------- T1 干净仓库 ----------
    git("init", "-q", cwd=FAKE_BASE)
    (FAKE_BASE / "a.txt").write_text("hello", encoding="utf-8")
    git("add", "-A", cwd=FAKE_BASE)
    git("-c", "user.email=s@t", "-c", "user.name=s", "commit", "-q", "-m", "init", cwd=FAKE_BASE)
    commit = git("rev-parse", "HEAD", cwd=FAKE_BASE)
    tree = git("rev-parse", "HEAD^{tree}", cwd=FAKE_BASE)
    reg_sha = set_registry_baseline(commit, tree)
    write_expected(script_sha, str(FAKE_BASE), commit, tree, reg_sha)

    results.append(run_case("T1 干净仓库 -> 退出码 3（指纹一致、门槛未就绪）",
                            sandbox_script, 3,
                            ["[OK  ] 基线工作树干净", "[OK  ] 基线 commit", "[OK  ] 基线 tree",
                             "[退出码 3]"]))

    # ---------- T2 工作树脏 ----------
    (FAKE_BASE / "untracked.txt").write_text("dirty", encoding="utf-8")
    results.append(run_case("T2 工作树脏 -> 退出码 2 + 逐条列出脏项",
                            sandbox_script, 2,
                            ["[FAIL] 基线工作树干净", "1 项改动/未跟踪",
                             "=== 基线工作树脏项（逐条列出）===", "untracked.txt",
                             "[退出码 2]"]))
    (FAKE_BASE / "untracked.txt").unlink()

    # ---------- T3 git 失败（仓库不存在） ----------
    exp = json.loads(FAKE_EXPECTED.read_text(encoding="utf-8"))
    exp["baseline"]["path"] = str(SANDBOX / "NO_SUCH_REPO")
    FAKE_EXPECTED.write_text(json.dumps(exp, ensure_ascii=False, indent=2), encoding="utf-8")
    results.append(run_case("T3 仓库不存在 -> 退出码 5 + 基线项标注 <git 失败>",
                            sandbox_script, 5,
                            ["[FAIL] 基线工作树干净", "<git 失败>", "=== git 命令失败",
                             "返回码:", "[退出码 5]"]))
    exp["baseline"]["path"] = str(FAKE_BASE)
    FAKE_EXPECTED.write_text(json.dumps(exp, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---------- T4 脚本自身被改写 ----------
    tampered = SANDBOX / "tampered-freeze_check_v2.py"
    tampered.write_text(sandbox_script.read_text(encoding="utf-8") + "\n# 篡改标记\n",
                        encoding="utf-8")
    results.append(run_case("T4 脚本自身被改写 -> 自身项 FAIL + 退出码 2",
                            tampered, 2,
                            ["[FAIL] 核验脚本自身（freeze_check_v2.py）",
                             "冻结工具已被改写", "[退出码 2]"]))

    # ---------- T5 管道禁用下的捕获回退 ----------
    rc, out, err = run_nopipe([sys.executable, str(sandbox_script),
                               "--expected", str(FAKE_EXPECTED),
                               "--root", str(FAKE_ROOT)])
    mode_ok = ("（git 输出捕获方式：tempfile）" in out) or ("（git 输出捕获方式：pipe）" in out)
    print(f"[{'PASS' if mode_ok else 'FAIL'}] T5 git 输出捕获方式可自证（pipe 或 tempfile 回退）")
    if not mode_ok:
        print(f"        stdout 尾部: {out[-300:]!r}")
    results.append(mode_ok)

    print()
    print(f"自测汇总：{sum(results)}/{len(results)} 通过")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
