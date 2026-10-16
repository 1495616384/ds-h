"""M0 自测：把 M0 的三条验收点写成可执行断言。

覆盖：① 版本字段非空；② `python -m xprod --version` 退出码 0 且输出含版本号；
③ 隔离性——包内产品源码不出现冻结链目录名。

刻意不用 `subprocess(capture_output=True)`：本机沙箱禁止创建管道
（见 `_xexp/X项目-阶段二进展与工作交接-v2.md` §六 G-1），改用临时文件重定向。
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from . import __version__

PKG_DIR = Path(__file__).resolve().parent
SELF = Path(__file__).resolve()

# 冻结链目录名特征：拼接构造，避免本文件自身被第 ③ 条检查误伤
_FREEZE_MARKER = "_" + "xexp"


def test_version_nonempty() -> None:
    assert __version__ and __version__.strip(), "版本字段不得为空"


def test_cli_version() -> None:
    with tempfile.TemporaryDirectory() as td:
        out_p = Path(td) / "out.txt"
        err_p = Path(td) / "err.txt"
        with open(out_p, "w", encoding="utf-8") as fo, open(err_p, "w", encoding="utf-8") as fe:
            proc = subprocess.run(
                [sys.executable, "-m", "xprod", "--version"],
                cwd=str(PKG_DIR.parent),
                stdout=fo,
                stderr=fe,
            )
        out = out_p.read_text(encoding="utf-8")
        err = err_p.read_text(encoding="utf-8")
    assert proc.returncode == 0, f"退出码应为 0，实际 {proc.returncode}；stderr={err!r}"
    assert __version__ in out, f"stdout 应含版本 {__version__!r}；实际 stdout={out!r}"


def test_isolation_no_freeze_paths() -> None:
    offenders = []
    for py in PKG_DIR.rglob("*.py"):
        if py.resolve() == SELF:
            continue  # 本文件是检查器，不是产品代码
        if _FREEZE_MARKER in py.read_text(encoding="utf-8"):
            offenders.append(py.relative_to(PKG_DIR).as_posix())
    assert not offenders, f"隔离性被破坏，以下产品文件引用了冻结链目录名：{offenders}"


def test_no_direct_write_text_in_product() -> None:
    """字节稳定写盘口径（静态强制）：产品模块不得直接用 `write_text`。

    Windows 文本模式会把换行符翻译成回车加换行，破坏「产物逐字节可复现」。
    确定性文本产物一律经 `textio.save_text`；自测文件用 write_text 造夹具，属正当用法。
    """
    offenders = []
    for py in PKG_DIR.rglob("*.py"):
        if py.name.startswith("selftest"):
            continue  # 自测文件是夹具构造，不在产品代码口径内
        if ".write_text(" in py.read_text(encoding="utf-8"):
            offenders.append(py.relative_to(PKG_DIR).as_posix())
    assert not offenders, f"以下产品模块绕过了 textio 直接用 write_text：{offenders}"


def main() -> int:
    tests = (
        test_version_nonempty,
        test_cli_version,
        test_isolation_no_freeze_paths,
        test_no_direct_write_text_in_product,
    )
    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as exc:
            failed += 1
            print(f"FAIL {t.__name__}: {exc}")
        else:
            print(f"PASS {t.__name__}")
    print(f"{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
