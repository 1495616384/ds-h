"""`python -m xprod` 的最小命令行入口。

M0 实现 `--version`；M1 追加 `parse`——把设计文档译为「条目—约束—证据」JSON；
M2 追加 `graph`——从只读代码副本构建模块依赖图，并可下钻单文件符号；
M3 追加 `impact`——给定模拟 diff，输出受影响条目 / 文件清单（`--text` 给人类可读版本）；
M5 追加 `dryrun`——按剧本回放 M4 设计的干跑骨架，输出收敛与否决判定（`--text` 给人类可读版本）。
参数解析仍不用 argparse，保持外部面最小、零依赖。
"""

from __future__ import annotations

import sys

from . import __version__

USAGE = (
    "usage: python -m xprod --version\n"
    "       python -m xprod parse <design-doc.md>\n"
    "       python -m xprod graph <code-root> [--tree <node-id>]\n"
    "       python -m xprod impact <diff-file> <code-root> <design-doc> [--text]\n"
    "       python -m xprod dryrun <scenarios.json> [--text]"
)


def _write_bytes(text: str) -> None:
    """把输出直接写入字节流。

    Windows 文本模式下 `sys.stdout` 会把 `\\n` 翻译成 `\\r\\n`，使 stdout 与真值
    无法逐字节比对；`graph` 的验收标准（stdout 与真值逐字节一致）要求绕开该翻译。
    """
    sys.stdout.buffer.write(text.encode("utf-8"))


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
    if args and args[0] == "graph":
        from . import graph_builder

        rest = args[1:]
        tree_id = None
        if "--tree" in rest:
            i = rest.index("--tree")
            if i + 1 >= len(rest):
                print(USAGE, file=sys.stderr)
                return 2
            tree_id = rest[i + 1]
            del rest[i : i + 2]
        if len(rest) != 1:
            print(USAGE, file=sys.stderr)
            return 2
        try:
            doc = graph_builder.build_graph(rest[0])
            text = (
                graph_builder.to_json(doc)
                if tree_id is None
                else graph_builder.render_node_tree(doc, tree_id)
            )
        except (graph_builder.GraphError, OSError) as exc:
            print(f"graph error: {exc}", file=sys.stderr)
            return 1
        _write_bytes(text)
        return 0
    if args and args[0] == "impact":
        from . import graph_builder, impact_analyzer, parser

        rest = args[1:]
        as_text = "--text" in rest
        if as_text:
            del rest[rest.index("--text")]
        if len(rest) != 3:
            print(USAGE, file=sys.stderr)
            return 2
        try:
            doc = impact_analyzer.analyze_files(rest[0], rest[1], rest[2])
        except (
            impact_analyzer.ImpactError,
            graph_builder.GraphError,
            parser.ParseError,
            OSError,
        ) as exc:
            print(f"impact error: {exc}", file=sys.stderr)
            return 1
        text = impact_analyzer.render_text(doc) if as_text else impact_analyzer.to_json(doc)
        _write_bytes(text)
        return 0
    if args and args[0] == "dryrun":
        from . import dryrun

        rest = args[1:]
        as_text = "--text" in rest
        if as_text:
            del rest[rest.index("--text")]
        if len(rest) != 1:
            print(USAGE, file=sys.stderr)
            return 2
        try:
            doc = dryrun.run_scenarios(rest[0])
        except (dryrun.DryRunError, OSError) as exc:
            print(f"dryrun error: {exc}", file=sys.stderr)
            return 1
        text = dryrun.render_text(doc) if as_text else dryrun.to_json(doc)
        _write_bytes(text)
        return 0
    print(USAGE, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
