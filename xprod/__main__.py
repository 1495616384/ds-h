"""`python -m xprod` 的最小命令行入口。

M0 实现 `--version`；M1 追加 `parse`——把设计文档译为「条目—约束—证据」JSON；
M2 追加 `graph`——从只读代码副本构建模块依赖图，并可下钻单文件符号；
M3 追加 `impact`——给定模拟 diff，输出受影响条目 / 文件清单（`--text` 给人类可读版本）；
M5 追加 `dryrun`——按剧本回放 M4 设计的干跑骨架，输出收敛与否决判定（`--text` 给人类可读版本）；
M6 追加 `guard`——流程护栏：冻结快照「改动前 / 改动后」比对 + 推送三态判定（`--text` 给人类可读版本）；
M7 追加 `conflict`——并发改动冲突检测：给定分工计划（多份并发改动），报出相互冲突的改动对（`--text` 给人类可读版本）；
M8 追加 `drift`——一致性漂移校验：给定代码根与设计文档，逐条证据锚解析活性，报出失联锚与设计盲区（`--text` 给人类可读版本）。
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
    "       python -m xprod dryrun <scenarios.json> [--text]\n"
    "       python -m xprod guard freeze --checker <freeze-checker.py> [--root <dir>] [--save <snap.json>|--compare <snap.json>] [--text]\n"
    "       python -m xprod guard push [--repo <dir>] [--git <path>] [--remote <name>] [--branch <name>] [--text]\n"
    "       python -m xprod conflict <plan.json> <code-root> <design-doc> [--text]\n"
    "       python -m xprod drift <code-root> <design-doc> [--text]"
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
    if args and args[0] == "guard":
        from . import guard

        rest = args[1:]
        as_text = "--text" in rest
        if as_text:
            del rest[rest.index("--text")]
        if not rest:
            print(USAGE, file=sys.stderr)
            return 2
        mode, rest = rest[0], rest[1:]

        def take(flag: str) -> str | None:
            """取出 `--flag value` 并从 rest 中删除；不存在返回 None，缺值抛 GuardError。"""
            if flag not in rest:
                return None
            i = rest.index(flag)
            if i + 1 >= len(rest):
                raise guard.GuardError(f"{flag} 缺少取值")
            value = rest[i + 1]
            del rest[i : i + 2]
            return value

        try:
            if mode == "freeze":
                checker = take("--checker")
                if checker is None:
                    print(USAGE, file=sys.stderr)
                    return 2
                root = take("--root")
                save = take("--save")
                compare = take("--compare")
                if rest or (save and compare):
                    print(USAGE, file=sys.stderr)
                    return 2
                current = guard.run_freeze_check(checker, root)
                if save:
                    guard.save_snapshot(save, current)
                if compare:
                    doc = guard.compare_snapshots(guard.load_snapshot(compare), current)
                else:
                    doc = current.to_dict()
            elif mode == "push":
                repo = take("--repo") or "."
                git_path = take("--git") or "git"
                remote = take("--remote") or "origin"
                branch = take("--branch") or "master"
                if rest:
                    print(USAGE, file=sys.stderr)
                    return 2
                doc = guard.probe_push_state(repo, remote, branch, git_path)
            else:
                print(USAGE, file=sys.stderr)
                return 2
        except (guard.GuardError, OSError) as exc:
            print(f"guard error: {exc}", file=sys.stderr)
            return 1
        text = guard.render_text(doc) if as_text else guard.to_json(doc)
        _write_bytes(text)
        return 0
    if args and args[0] == "conflict":
        from . import conflict, graph_builder, impact_analyzer, parser

        rest = args[1:]
        as_text = "--text" in rest
        if as_text:
            del rest[rest.index("--text")]
        if len(rest) != 3:
            print(USAGE, file=sys.stderr)
            return 2
        try:
            doc = conflict.analyze_plan(rest[0], rest[1], rest[2])
        except (
            conflict.ConflictError,
            graph_builder.GraphError,
            impact_analyzer.ImpactError,
            parser.ParseError,
            OSError,
        ) as exc:
            print(f"conflict error: {exc}", file=sys.stderr)
            return 1
        text = conflict.render_text(doc) if as_text else conflict.to_json(doc)
        _write_bytes(text)
        return 0
    if args and args[0] == "drift":
        from . import drift, parser

        rest = args[1:]
        as_text = "--text" in rest
        if as_text:
            del rest[rest.index("--text")]
        if len(rest) != 2:
            print(USAGE, file=sys.stderr)
            return 2
        try:
            doc = drift.analyze(rest[0], rest[1])
        except (drift.DriftError, parser.ParseError, OSError) as exc:
            print(f"drift error: {exc}", file=sys.stderr)
            return 1
        text = drift.render_text(doc) if as_text else drift.to_json(doc)
        _write_bytes(text)
        return 0
    print(USAGE, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
