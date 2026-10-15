"""`python -m xprod` 的最小命令行入口。

M0 实现 `--version`；M1 追加 `parse`——把设计文档译为「条目—约束—证据」JSON。
参数解析仍不用 argparse，保持外部面最小、零依赖。
"""

from __future__ import annotations

import sys

from . import __version__

USAGE = (
    "usage: python -m xprod --version\n"
    "       python -m xprod parse <design-doc.md>"
)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else list(argv)
    if args == ["--version"]:
        print(f"xprod {__version__}")
        return 0
    if len(args) == 2 and args[0] == "parse":
        from . import parser

        try:
            doc = parser.parse_file(args[1])
        except (parser.ParseError, OSError) as exc:
            print(f"parse error: {exc}", file=sys.stderr)
            return 1
        sys.stdout.write(parser.to_json(doc))
        return 0
    print(USAGE, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
