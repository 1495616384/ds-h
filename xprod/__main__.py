"""`python -m xprod` 的最小命令行入口。

M0 实现 `--version`；M1 追加 `parse`——把设计文档译为「条目—约束—证据」JSON；
M2 追加 `graph`——从只读代码副本构建模块依赖图，并可下钻单文件符号；
M3 追加 `impact`——给定模拟 diff，输出受影响条目 / 文件清单（`--text` 给人类可读版本）；
M5 追加 `dryrun`——按剧本回放 M4 设计的干跑骨架，输出收敛与否决判定（`--text` 给人类可读版本）；
M6 追加 `guard`——流程护栏：冻结快照「改动前 / 改动后」比对 + 推送三态判定（`--text` 给人类可读版本）；
M7 追加 `conflict`——并发改动冲突检测：给定分工计划（多份并发改动），报出相互冲突的改动对（`--text` 给人类可读版本）；
M8 追加 `drift`——一致性漂移校验：给定代码根与设计文档，逐条证据锚解析活性，报出失联锚与设计盲区（`--text` 给人类可读版本）；
M9 追加 `view`——逻辑控制面可视面：把条目、锚活性、设计盲区与依赖图汇成单个自包含 HTML（写到 stdout）；
M10 追加 `sync`——同步基线比对：把锚活性存成基线，之后比对报出新增失联 / 恢复 / 证据增删 / 盲区变化（`--text` 给人类可读版本）；
M11 扩展 `view`——可选 `--baseline <snap.json>`：给了基线就在可视面追加「同步增量（相对基线）」段，
增量快照经 `sync.snapshot_from_drift` 由**同一次** `drift` 采集构造（不重复采集、不与 `sync` 分叉）。
M12 追加 `flow`——业务流 / 数据流影响图：给定流程文档与代码根，报出步骤锚活性、直接命中与沿下游闭包
扩散的步骤；给了 `--diff` 再算一次流程级影响判定（`--text` 给人类可读版本）。
M13 扩展 `view`——可选 `--flow <flow-doc.md>`（配合可选 `--diff`）：流程影响面与既有段汇成同一张页面。
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
    "       python -m xprod drift <code-root> <design-doc> [--text]\n"
    "       python -m xprod view <code-root> <design-doc> [--baseline <snap.json>] [--flow <flow-doc.md>] [--diff <diff-file>]\n"
    "       python -m xprod sync <code-root> <design-doc> [--save <snap.json>|--compare <snap.json>] [--text]\n"
    "       python -m xprod flow <flow-doc.md> <code-root> [--diff <diff-file>] [--text]"
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
        _write_bytes(parser.to_json(doc))
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
    if args and args[0] == "view":
        from . import drift, flow, graph_builder, impact_analyzer, parser, sync, viewer

        rest = args[1:]
        missing = False

        def take(flag: str) -> str | None:
            """取出 `--flag value` 并从 rest 中删除；不存在返回 None，缺值置 `missing`。"""
            nonlocal rest, missing
            if flag not in rest:
                return None
            i = rest.index(flag)
            if i + 1 >= len(rest):
                missing = True
                return None
            value = rest[i + 1]
            del rest[i : i + 2]
            return value

        baseline_path = take("--baseline")
        flow_path = take("--flow")
        diff_path = take("--diff")
        # `--diff` 依附于 `--flow`：给了 `--diff` 却没给 `--flow` 属用法错误，不静默丢弃
        if len(rest) != 2 or missing or (diff_path is not None and flow_path is None):
            print(USAGE, file=sys.stderr)
            return 2
        try:
            baseline = sync.load_snapshot(baseline_path) if baseline_path is not None else None
            doc = viewer.analyze(rest[0], rest[1], baseline, flow_path, diff_path)
        except (
            drift.DriftError,
            flow.FlowError,
            graph_builder.GraphError,
            impact_analyzer.ImpactError,
            parser.ParseError,
            sync.SyncError,
            OSError,
        ) as exc:
            print(f"view error: {exc}", file=sys.stderr)
            return 1
        _write_bytes(viewer.render_html(doc))
        return 0
    if args and args[0] == "sync":
        from . import drift, parser, sync

        rest = args[1:]
        as_text = "--text" in rest
        if as_text:
            del rest[rest.index("--text")]

        def take(flag: str) -> str | None:
            """取出 `--flag value` 并从 rest 中删除；不存在返回 None，缺值抛 SyncError。"""
            if flag not in rest:
                return None
            i = rest.index(flag)
            if i + 1 >= len(rest):
                raise sync.SyncError(f"{flag} 缺少取值")
            value = rest[i + 1]
            del rest[i : i + 2]
            return value

        try:
            save = take("--save")
            compare = take("--compare")
            if len(rest) != 2 or (save and compare):
                print(USAGE, file=sys.stderr)
                return 2
            current = sync.snapshot(rest[0], rest[1])
            if save:
                sync.save_snapshot(save, current)
            if compare:
                doc = sync.compare_snapshots(sync.load_snapshot(compare), current)
            else:
                doc = current
        except (drift.DriftError, parser.ParseError, sync.SyncError, OSError) as exc:
            print(f"sync error: {exc}", file=sys.stderr)
            return 1
        text = sync.render_text(doc) if as_text else sync.to_json(doc)
        _write_bytes(text)
        return 0
    if args and args[0] == "flow":
        from . import flow, impact_analyzer

        rest = args[1:]
        as_text = "--text" in rest
        if as_text:
            del rest[rest.index("--text")]
        diff_file = None
        if "--diff" in rest:
            i = rest.index("--diff")
            if i + 1 >= len(rest):
                print(USAGE, file=sys.stderr)
                return 2
            diff_file = rest[i + 1]
            del rest[i : i + 2]
        if len(rest) != 2:
            print(USAGE, file=sys.stderr)
            return 2
        try:
            doc = flow.analyze(rest[0], rest[1], diff_file)
        except (flow.FlowError, impact_analyzer.ImpactError, OSError) as exc:
            print(f"flow error: {exc}", file=sys.stderr)
            return 1
        text = flow.render_text(doc) if as_text else flow.to_json(doc)
        _write_bytes(text)
        return 0
    print(USAGE, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
