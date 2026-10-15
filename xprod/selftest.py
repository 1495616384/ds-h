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


def main() -> int:
    tests = (test_version_nonempty, test_cli_version, test_isolation_no_freeze_paths)
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
