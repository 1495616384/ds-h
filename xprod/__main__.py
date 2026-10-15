"""`python -m xprod` 的最小命令行入口（M0）。

M0 只要求验证「包能被 `-m` 方式启动」这一条验收点，故仅实现 `--version`；
参数解析刻意不用 argparse，以缩小 M0 阶段的外部面（后续里程碑再引入）。
"""

from __future__ import annotations

import sys

from . import __version__

USAGE = "usage: python -m xprod --version"


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else list(argv)
    if args == ["--version"]:
        print(f"xprod {__version__}")
        return 0
    print(USAGE, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
