"""M16 自测：把「影响分析器采集 / 构造分离」的验收点写成可执行断言。

核心思路：**夹具临时自建**——每次测试在临时目录里现造一个最小代码根 + 设计文档 + 流程文档 +
五份改动 diff，使本自测**不依赖**任何归档基线副本、不依赖网络；本文件与 `impact_analyzer.py`
同样不含冻结链目录名字面量（由 M0 自测第三条校验）。

主夹具（决定各测试的期望值）：
    代码根：src/app/{__init__,api,core,notify,other}.py、docs/{guide,spec}.md
      —— `api.py` 里有 `from app.core import X`，故图上有一条 `api.py → core.py` 的边，
        改 core.py 时反向闭包会把 api.py 拉进受影响集合（让「构造」这一步真有活干）。
    设计文档：OK-001 @ src/app/api.py、OK-002 @ src/app/core.py、
              OK-003 @ docs/（前缀锚）、OK-004 @ just-a-token（无斜杠 → unanchored）
    流程文档：FL-001「下单到发货」：S1@api.py → S2@core.py（供 ⑥ 端到端计数的流程层用）
    各 diff：A 改 api.py、B 改 core.py、C 改 notify.py、D 改 other.py、E 再改一次 core.py

覆盖（对应 `X产品化-M16设计稿-v1.md` §八 的 ①–⑩）：
    ① 等价性（文本口径）：`analyze` 与 `analyze_prepared(prepare(...))` 逐字节一致（含有 diff / 空 diff）；
    ② 等价性（文件口径）：`analyze_files` 与 `analyze(read_diff(...))` 逐字节一致；
    ③ 准备体形状：`prepare` == `{"graph": build_graph(root), "design": parse_file(design)}`，
       键序为 `["graph", "design"]`，且**不含**任何派生键（采集体只放原始事实）；
    ④ 复用不变性：同一 `prepared` 连续 5 次（含同一 diff 重复、也含不同 diff）结果各自与单独
       `analyze` 逐字节一致，且 `prepared` 在前后**复合摘要不变**（证明只读）；
    ⑤ 复用计数（核心证据，库级）：计数探针下 `prepare` ×1 + `analyze_prepared` ×5 → 两计数器 **== 1**；
       **对照** `analyze` ×5 → 两计数器均为 **5**（N→1 的差异真实存在，而非「看起来更快」）；
    ⑥ 复用计数（核心证据，端到端）：同一探针下 `conflict.analyze_plan`（5 份改动 + 流程文档）
       → `graph_builder.build_graph` 与 `parser.parse_file` 计数**各 == 1**；
    ⑦ 结构断言（防复发）：`inspect.getsource(analyze)` **不含** `build_graph(` 与 `parse_file(`；
       `inspect.getsource(analyze_files)` **不含** `read_text(`——编排层只是一层委托；
    ⑧ 读口径不变：带 BOM 的 diff 经 `read_diff` 与无 BOM 文本一致，且 `analyze_files` 结果与
       `analyze(read_diff(...))` 结果逐字节一致（证明收口没偷偷换编码）；
    ⑨ 确定性 + 只读：同输入两次 `to_json` / `render_text` 逐字节一致；四种入口前后夹具目录摘要不变；
    ⑩ CLI 与 M3 / M7 / M14 / M15 回归：`impact` 子命令 stdout 与库输出逐字节一致、无 `\\r\\n`、
       退出码 0；坏 diff / 坏设计文档 / 代码根非目录 → 1；参数不足 → 2；
       `selftest_m7` 仍 12/12、`selftest_m14` / `selftest_m15` 仍 10/10。

关于 ⑩ 第 4 条（预算内定点调整）：设计稿原写「`selftest_m3` 仍 10/10」，但 `selftest_m3` 需在命令行
传入**代码根**参数（其根即归档基线副本），而 M0 自测第三条**禁止产品源码出现冻结链目录名**——
把该路径硬写进本文件会当场破坏隔离性。故本条改为在自测内回归 `selftest_m7` / `selftest_m14` /
`selftest_m15`（三者均自建夹具、无需参数）；`selftest_m3` 的 10/10 由里程碑级**全域回归**在自测外覆盖。

沿用 M0–M15 约定：不用 `subprocess` 管道，改临时文件重定向（本机沙箱禁建管道）。
"""

from __future__ import annotations

import hashlib
import inspect
import json
import tempfile
from pathlib import Path

from . import conflict, graph_builder, impact_analyzer, parser, selftest_kit
from .selftest_kit import PKG_DIR, cli as _cli, run_module as _run_module, dir_digest as _dir_digest


_DESIGN = (
    "# 夹具设计文档（M16 自测专用）\n"
    "\n"
    "### OK-001 — 精确锚 api.py\n"
    "- type: 公共接口\n"
    "- invariant: 示例不变量\n"
    "- change_control: free\n"
    "- severity: normal\n"
    "- evidence:\n"
    "  - src/app/api.py\n"
    "- action_policy: 警告\n"
    "\n"
    "### OK-002 — 精确锚 core.py\n"
    "- type: 数据完整性\n"
    "- invariant: 示例不变量\n"
    "- change_control: free\n"
    "- severity: normal\n"
    "- evidence:\n"
    "  - src/app/core.py\n"
    "- action_policy: 警告\n"
    "\n"
    "### OK-003 — 前缀锚 docs/\n"
    "- type: 公共接口\n"
    "- invariant: 示例不变量\n"
    "- change_control: free\n"
    "- severity: normal\n"
    "- evidence:\n"
    "  - docs/\n"
    "- action_policy: 警告\n"
    "\n"
    "### OK-004 — 无斜杠锚（unanchored）\n"
    "- type: 公共接口\n"
    "- invariant: 示例不变量\n"
    "- change_control: free\n"
    "- severity: normal\n"
    "- evidence:\n"
    "  - just-a-token\n"
    "- action_policy: 警告\n"
)

_FLOW = (
    "# 流程夹具（M16 自测专用）\n"
    "\n"
    "## FL-001 — 下单到发货\n"
    "\n"
    "- step:\n"
    "  - S1: 校验库存 @ src/app/api.py\n"
    "  - S2: 扣减库存 @ src/app/core.py\n"
    "- edge:\n"
    "  - S1 -> S2\n"
)

# id → (变更文件, 该文件新内容)；A–E 与 M15 / M14 自测同形（含「E 与 B 改同一文件」）
_CHANGES = (
    ("A", "src/app/api.py", "from app.core import X\nA = 1\n"),
    ("B", "src/app/core.py", "X = 2\n"),
    ("C", "src/app/notify.py", "N = 2\n"),
    ("D", "src/app/other.py", "Z = 4\n"),
    ("E", "src/app/core.py", "X = 3\n"),
)


def _diff(path: str, old: str, new: str) -> str:
    """造一份只改一个文件的统一 diff（与 M3 解析口径一致）。"""
    return (
        f"diff --git a/{path} b/{path}\n"
        f"--- a/{path}\n"
        f"+++ b/{path}\n"
        "@@ -1 +1 @@\n"
        f"-{old}\n"
        f"+{new}\n"
    )


def _make_root(td: Path) -> Path:
    """建最小代码根（层层 `__init__.py`，使 M2 依赖图有模块名可解析、M3 有节点可用）。"""
    root = td / "root"
    (root / "src" / "app").mkdir(parents=True)
    (root / "docs").mkdir(parents=True)
    (root / "src" / "app" / "__init__.py").write_text("", encoding="utf-8")
    (root / "src" / "app" / "api.py").write_text("from app.core import X\nA = 0\n", encoding="utf-8")
    (root / "src" / "app" / "core.py").write_text("X = 1\n", encoding="utf-8")
    (root / "src" / "app" / "notify.py").write_text("N = 1\n", encoding="utf-8")
    (root / "src" / "app" / "other.py").write_text("Z = 3\n", encoding="utf-8")
    (root / "docs" / "guide.md").write_text("# 指南\n", encoding="utf-8")
    (root / "docs" / "spec.md").write_text("# 规格\n", encoding="utf-8")
    return root


def _fixture(td: Path) -> tuple[Path, Path, Path, dict[str, Path]]:
    """建全套夹具，返回（代码根, 设计文档, 流程文档, id→diff 路径）。"""
    root = _make_root(td)
    design = td / "design.md"
    design.write_text(_DESIGN, encoding="utf-8")
    flow_doc = td / "flow.md"
    flow_doc.write_text(_FLOW, encoding="utf-8")

    diffs: dict[str, Path] = {}
    for cid, path, new in _CHANGES:
        dp = td / f"{cid}.diff"
        dp.write_text(_diff(path, "old\n", new), encoding="utf-8")
        diffs[cid] = dp
    return root, design, flow_doc, diffs


def _plan_with_all_changes(td: Path, diffs: dict[str, Path]) -> Path:
    """造一份含 A–E 五份改动（id 升序）的分工计划，供 ⑥ 端到端计数用。

    `diff` 写成**相对名**，由 `conflict.load_plan` 相对计划文件所在目录解析（M7 路径规则）。
    """
    changesets = [{"id": cid, "diff": diffs[cid].name} for cid, _, _ in _CHANGES]
    plan = td / "plan.json"
    plan.write_text(
        json.dumps({"plan_id": "M16 夹具", "changesets": changesets}, ensure_ascii=False),
        encoding="utf-8",
    )
    return plan


def _doc_digest(doc: dict) -> str:
    """对内存中的文档取摘要——用本包**规范序列化**（保留键序），故「值」与「键序」一并受保护。

    为什么不用 `json.dumps(..., sort_keys=True)`：`sort_keys` 会把键序抹平，于是「键序被就地改乱」
    这类污染照不出来；而键序在本仓库是**写死口径**（确定性 / 逐字节可比），必须一并纳入只读证据。
    """
    return hashlib.sha256(impact_analyzer.to_json(doc).encode("utf-8")).hexdigest()


class _Probe:
    """计数探针：临时包装 `graph_builder.build_graph` 与 `parser.parse_file`，`try/finally` 还原。

    为什么不用「计时」：耗时受机器抖动影响、不可复现；**计数**才是「N 次变成 1 次」的直接证据。
    为什么只包这两个：它们正是「与 diff 无关」的两件事——建图、解析设计文档；`prepare` 只调它们，
    `analyze_prepared` 一个都不调，故计数即等价于「采集发生了几次」。
    """

    def __init__(self) -> None:
        self.calls = {"build_graph": 0, "parse_file": 0}

    def __enter__(self) -> "_Probe":
        self._orig_build = graph_builder.build_graph
        self._orig_parse = parser.parse_file

        def wrap_build(root: str | Path):
            self.calls["build_graph"] += 1
            return self._orig_build(root)

        def wrap_parse(path: str | Path):
            self.calls["parse_file"] += 1
            return self._orig_parse(path)

        graph_builder.build_graph = wrap_build
        parser.parse_file = wrap_parse
        return self

    def __exit__(self, *exc: object) -> bool:
        graph_builder.build_graph = self._orig_build
        parser.parse_file = self._orig_parse
        return False


def test_equivalence_text() -> None:
    """① 等价性（文本口径）：analyze 与「采集 + 构造」两段调用逐字节一致（含有 diff / 空 diff）。"""
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design, _flow_doc, diffs = _fixture(td)
        text = impact_analyzer.read_diff(diffs["A"])
        legacy = impact_analyzer.analyze(text, root, design)
        split = impact_analyzer.analyze_prepared(impact_analyzer.prepare(root, design), text)
        assert impact_analyzer.to_json(legacy) == impact_analyzer.to_json(split), "有 diff 时两段调用应逐字节一致"
        # 空 diff 文本：同一份 construct 行为也要覆盖（不能只在非空 diff 上成立）
        empty_legacy = impact_analyzer.analyze("", root, design)
        empty_split = impact_analyzer.analyze_prepared(impact_analyzer.prepare(root, design), "")
        assert impact_analyzer.to_json(empty_legacy) == impact_analyzer.to_json(empty_split), "空 diff 时两段调用应逐字节一致"


def test_equivalence_files() -> None:
    """② 等价性（文件口径）：analyze_files 与 analyze(read_diff(...)) 逐字节一致。"""
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design, _flow_doc, diffs = _fixture(td)
        for cid in ("A", "B", "C", "D"):
            files_doc = impact_analyzer.analyze_files(diffs[cid], root, design)
            text_doc = impact_analyzer.analyze(impact_analyzer.read_diff(diffs[cid]), root, design)
            assert impact_analyzer.to_json(files_doc) == impact_analyzer.to_json(text_doc), f"{cid}：读文件与读文本两条入口应同源"


def test_prepared_shape() -> None:
    """③ 准备体形状：prepare == {graph: build_graph, design: parse_file}；键序固定；不含派生键。"""
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design, _flow_doc, _diffs = _fixture(td)
        prepared = impact_analyzer.prepare(root, design)
        expected = {"graph": graph_builder.build_graph(root), "design": parser.parse_file(design)}
        assert list(prepared) == ["graph", "design"], f"键序应为 ['graph', 'design']，实际 {list(prepared)}"
        assert prepared == expected, "prepare 的值应与 build_graph / parse_file 的返回完全相同"
        # 采集体只放原始事实：派生结果（节点 id 集合 / 反向邻接 / 证据索引）不得塞进来
        for forbidden in ("nodes", "edges", "reverse", "by_entry", "tags", "index"):
            assert forbidden not in prepared, f"采集体不得含派生键 {forbidden!r}"


def test_reuse_is_pure() -> None:
    """④ 复用不变性：同一 prepared 连续 5 次（含重复 diff）结果各自正确，且自身摘要不变。"""
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design, _flow_doc, diffs = _fixture(td)
        prepared = impact_analyzer.prepare(root, design)
        before = _doc_digest(prepared)
        order = ["A", "B", "A", "C", "D"]  # 含重复同一 diff，证明「复用不串味」
        results = [
            impact_analyzer.analyze_prepared(prepared, impact_analyzer.read_diff(diffs[cid]))
            for cid in order
        ]
        after = _doc_digest(prepared)
        assert before == after, "analyze_prepared 不得就地修改传入的 prepared"
        # 断言必须留在临时目录存活期内（目录一回收，`analyze` 会因代码根不存在而抛 GraphError）
        for cid, got in zip(order, results):
            expected = impact_analyzer.analyze(impact_analyzer.read_diff(diffs[cid]), root, design)
            assert impact_analyzer.to_json(got) == impact_analyzer.to_json(expected), f"{cid}：复用结果应与单独 analyze 逐字节一致"
        assert impact_analyzer.to_json(results[0]) == impact_analyzer.to_json(results[2]), "同一 diff 复用两次应得到同一结果"


def test_reuse_counter_library_level() -> None:
    """⑤ 复用计数（核心证据）：prepare×1 + analyze_prepared×5 → 计数器 == 1；对照 analyze×5 → == 5。"""
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design, _flow_doc, diffs = _fixture(td)
        order = ["A", "B", "C", "D", "E"]

        with _Probe() as reuse:
            prepared = impact_analyzer.prepare(root, design)
            for cid in order:
                impact_analyzer.analyze_prepared(prepared, impact_analyzer.read_diff(diffs[cid]))
        assert reuse.calls == {"build_graph": 1, "parse_file": 1}, f"复用路径应只采集一次，实际 {reuse.calls}"

        with _Probe() as control:
            for cid in order:
                impact_analyzer.analyze(impact_analyzer.read_diff(diffs[cid]), root, design)
        assert control.calls == {"build_graph": 5, "parse_file": 5}, f"对照路径应采集 5 次，实际 {control.calls}"


def test_reuse_counter_end_to_end() -> None:
    """⑥ 复用计数（端到端）：conflict.analyze_plan（5 份改动 + 流程文档）只建图 / 解析各 1 次。"""
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design, flow_doc, diffs = _fixture(td)
        plan = _plan_with_all_changes(td, diffs)
        with _Probe() as probe:
            doc = conflict.analyze_plan(plan, root, design, flow_doc)
    assert probe.calls == {"build_graph": 1, "parse_file": 1}, f"M7 逐改动重复建图 / 重复解析应已消除，实际 {probe.calls}"
    assert [c["id"] for c in doc["changesets"]] == ["A", "B", "C", "D", "E"], "条目层应覆盖全部 5 份改动"
    assert [r["id"] for r in doc["flow_of_changesets"]] == ["A", "B", "C", "D", "E"], "流程层应覆盖全部 5 份改动"


def test_analyze_is_thin_delegation() -> None:
    """⑦ 结构断言（防复发）：编排层只是一层委托，采集 / 读取不得被再写一遍。"""
    src_analyze = inspect.getsource(impact_analyzer.analyze)
    assert "build_graph(" not in src_analyze, "analyze 不得在编排层重新建图"
    assert "parse_file(" not in src_analyze, "analyze 不得在编排层重新解析设计文档"
    assert "prepare(" in src_analyze and "analyze_prepared(" in src_analyze, "analyze 应显式委托给两个唯一实现"
    src_files = inspect.getsource(impact_analyzer.analyze_files)
    assert "read_text(" not in src_files, "analyze_files 不得自带第二份读口径"
    assert "read_diff(" in src_files, "analyze_files 的读口径应唯一收口在 read_diff"


def test_read_bom_encoding() -> None:
    """⑧ 读口径不变：带 BOM 的 diff 经 read_diff 与无 BOM 文本一致；文件口径与文本口径同源。"""
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design, _flow_doc, diffs = _fixture(td)
        plain = impact_analyzer.read_diff(diffs["A"])
        bom_diff = td / "bom.diff"
        bom_diff.write_bytes(b"\xef\xbb\xbf" + plain.encode("utf-8"))  # UTF-8 BOM 前缀
        got = impact_analyzer.read_diff(bom_diff)
        assert got == plain, "utf-8-sig 应剥离 BOM，与无 BOM 同文本一致"
        files_doc = impact_analyzer.analyze_files(bom_diff, root, design)
        text_doc = impact_analyzer.analyze(got, root, design)
        assert impact_analyzer.to_json(files_doc) == impact_analyzer.to_json(text_doc), "收口不得偷偷换编码"


def test_determinism_and_read_only() -> None:
    """⑨ 确定性 + 只读：同输入两次逐字节一致；四种入口前后夹具目录摘要不变。"""
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design, _flow_doc, diffs = _fixture(td)
        before = _dir_digest(td)
        prepared = impact_analyzer.prepare(root, design)
        first = impact_analyzer.analyze_prepared(prepared, impact_analyzer.read_diff(diffs["A"]))
        second = impact_analyzer.analyze_prepared(prepared, impact_analyzer.read_diff(diffs["A"]))
        assert impact_analyzer.to_json(first) == impact_analyzer.to_json(second), "同输入两次 to_json 应逐字节一致"
        assert impact_analyzer.render_text(first) == impact_analyzer.render_text(second), "同输入两次 render_text 应逐字节一致"
        impact_analyzer.analyze(impact_analyzer.read_diff(diffs["B"]), root, design)
        impact_analyzer.analyze_files(diffs["C"], root, design)
        after = _dir_digest(td)
        assert before == after, "全过程不得写夹具中的任何一个字节"


def test_cli_and_regression() -> None:
    """⑩ CLI 与回归：stdout 与库输出逐字节一致、无 `\\r\\n`；错误码语义不变；m7 / m14 / m15 仍通过。"""
    if selftest_kit.in_regression():
        return
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design, _flow_doc, diffs = _fixture(td)

        lib = impact_analyzer.analyze_files(diffs["A"], root, design)
        code, out, _err = _cli("impact", str(diffs["A"]), str(root), str(design))
        assert code == 0, f"impact 子命令应退出码 0，实际 {code}"
        assert out == impact_analyzer.to_json(lib).encode("utf-8"), "CLI stdout 应与库输出逐字节一致"
        assert b"\r\n" not in out, "stdout 不得被翻译成 CRLF"

        expected_text = impact_analyzer.render_text(lib).encode("utf-8")
        code_t, out_t, _err_t = _cli("impact", str(diffs["A"]), str(root), str(design), "--text")
        assert code_t == 0 and out_t == expected_text, "--text 应与库输出逐字节一致"

        bad_design = td / "bad-design.md"
        bad_design.write_text("这一行根本不是设计文档\n", encoding="utf-8")
        assert _cli("impact", str(diffs["A"]), str(root), str(bad_design))[0] == 1, "坏设计文档应退出码 1"
        bad_diff = td / "bad.diff"
        bad_diff.write_text("这不是统一 diff\n", encoding="utf-8")
        assert _cli("impact", str(bad_diff), str(root), str(design))[0] == 1, "坏 diff 应退出码 1"
        assert _cli("impact", str(diffs["A"]), str(td / "nope"), str(design))[0] == 1, "代码根非目录应退出码 1"
        assert _cli("impact", str(diffs["A"]), str(root))[0] == 2, "参数不足应退出码 2"

        for mod, expect in (
            ("selftest_m7", "12/12 passed"),
            ("selftest_m14", "10/10 passed"),
            ("selftest_m15", "10/10 passed"),
        ):
            rc, out_r, _err_r = _run_module(mod)
            tail = out_r.decode("utf-8", "replace").strip().splitlines()[-1] if out_r else ""
            assert rc == 0 and tail == expect, f"{mod} 末行应为 {expect!r}，实际 {tail!r}"


def main() -> int:
    tests = (
        test_equivalence_text,
        test_equivalence_files,
        test_prepared_shape,
        test_reuse_is_pure,
        test_reuse_counter_library_level,
        test_reuse_counter_end_to_end,
        test_analyze_is_thin_delegation,
        test_read_bom_encoding,
        test_determinism_and_read_only,
        test_cli_and_regression,
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
