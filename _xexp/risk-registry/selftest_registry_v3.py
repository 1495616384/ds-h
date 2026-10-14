"""verify_registry v3 与 proc_capture 的自测（隔离根目录，不触碰真实基线）。

  R1 真实登记表（--root 指向真实 G:\\ds-h） -> 应"通过"且绑定一致
  R2 隔离根目录下伪造基线（git 仓库存在但 HEAD 与登记表不符） -> 应报告"绑定不一致"
  R3 隔离根目录下基线路径不存在（git 失败） -> 应报告 git 失败与返回码、结论"未通过"
  R4 proc_capture 自证捕获方式（pipe 或 tempfile 回退）且能真实拿到子进程输出

用法：python selftest_registry_v3.py
"""
import atexit
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent / "tools"
sys.path.insert(0, str(TOOLS))
from proc_capture import force_utf8_stdio, probe_capture_mode, run_captured  # noqa: E402

force_utf8_stdio()

VERIFY = HERE / "verify_registry.py"
GIT = r"C:\Program Files\Git\cmd\git.exe"
SANDBOX = HERE / "_selftest-sandbox-registry"
_TMP = []


def _cleanup():
    for p in _TMP:
        try:
            os.unlink(p)
        except OSError:
            pass


atexit.register(_cleanup)


def run_nopipe(cmd):
    fo = tempfile.mkstemp(prefix="reg-out-", suffix=".txt")
    fe = tempfile.mkstemp(prefix="reg-err-", suffix=".txt")
    os.close(fo[0])
    os.close(fe[0])
    _TMP.extend([fo[1], fe[1]])
    with open(fo[1], "w", encoding="utf-8") as o, open(fe[1], "w", encoding="utf-8") as e:
        rc = subprocess.run(list(cmd), stdout=o, stderr=e).returncode
    return (rc,
            Path(fo[1]).read_text(encoding="utf-8", errors="replace"),
            Path(fe[1]).read_text(encoding="utf-8", errors="replace"))


def git(*args, cwd=None):
    rc, out, err = run_nopipe([GIT, *(("-C", str(cwd)) if cwd else ()), *args])
    assert rc == 0, f"git 失败 {args}: {err}"
    return out.strip()


def case(name, cmd, expect_rc, expect_substrings):
    rc, out, err = run_nopipe(cmd)
    text = out + err
    missing = [s for s in expect_substrings if s not in text]
    ok = rc == expect_rc and not missing
    print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    print(f"        退出码 期望 {expect_rc} / 实测 {rc}")
    if missing:
        print(f"        缺失断言: {missing}")
        for ln in text.splitlines():
            if ("FAIL" in ln or "绑定" in ln or "git" in ln or "总结果" in ln or "捕获方式" in ln):
                print(f"           | {ln}")
    return ok


def main() -> int:
    results = []

    # R1 真实登记表
    results.append(case("R1 真实登记表 -> 通过 + 绑定一致",
                        [sys.executable, str(VERIFY), "--root", r"G:\ds-h"], 0,
                        ["绑定一致 OK", "自动校验总结果: 通过"]))

    # 构造隔离沙箱
    if SANDBOX.exists():
        shutil.rmtree(SANDBOX, ignore_errors=True)
    base = SANDBOX / "_xexp" / "base"
    base.mkdir(parents=True, exist_ok=True)
    git("init", "-q", cwd=base)
    (base / "a.txt").write_text("x", encoding="utf-8")
    git("add", "-A", cwd=base)
    git("-c", "user.email=s@t", "-c", "user.name=s", "commit", "-q", "-m", "init", cwd=base)
    real_reg = json.loads((HERE / "RISK-REGISTRY-v1.json").read_text(encoding="utf-8"))

    # R2 绑定不一致：把登记表的 commit 改成一个不存在于沙箱的值
    fake = json.loads(json.dumps(real_reg, ensure_ascii=False))
    fake["subject_baseline"]["commit"] = "0" * 40
    fake_reg = SANDBOX / "RISK-REGISTRY-v1.json"
    fake_reg.write_text(json.dumps(fake, ensure_ascii=False), encoding="utf-8")
    results.append(case("R2 隔离基线 + 登记表 commit 不符 -> 绑定不一致",
                        [sys.executable, str(VERIFY), "--root", str(SANDBOX),
                         "--registry", str(fake_reg)], 1,
                        ["FAIL 基线绑定不一致", "自动校验总结果: 未通过"]))

    # R3 git 失败：基线目录不存在
    results.append(case("R3 基线路径不存在 -> git 失败被显式报告",
                        [sys.executable, str(VERIFY), "--root", str(SANDBOX / "NO_SUCH_ROOT"),
                         "--registry", str(fake_reg)], 1,
                        ["git 命令失败", "返回码", "<git 失败>"]))

    # R4 捕获方式自证
    mode, rc, out = probe_capture_mode()
    ok = rc == 0 and out == "probe-ok" and mode in ("pipe", "tempfile")
    print(f"[{'PASS' if ok else 'FAIL'}] R4 proc_capture 自证：mode={mode} rc={rc} out={out!r}")
    results.append(ok)

    print()
    print(f"自测汇总：{sum(results)}/{len(results)} 通过")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
