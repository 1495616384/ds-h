"""M17 自测：把「viewer 设计文档双解析收口」的验收点写成可执行断言。

核心思路：**夹具临时自建**——每次测试在临时目录里现造一个最小代码根 + 设计文档，
使本自测**不依赖**任何归档基线副本、不依赖网络；本文件与 `drift.py` / `viewer.py` 同样
不含冻结链目录名字面量（由 M0 自测第三条校验）。

主夹具（决定各测试的期望值）：
    代码根：src/app/{__init__,api,core,notify}.py、docs/{guide,spec}.md
      —— `api.py` 里有 `from app.core import X`，故图上有一条 `api.py → core.py` 的边，
        使 `viewer.analyze` 的依赖图段真有内容可渲染。
    设计文档：OK-001 @ src/app/api.py（精确锚·活性）、OK-002 @ src/app/core.py（精确锚·活性）、
              OK-003 @ docs/（前缀锚·活性，命中 docs/guide.md 与 docs/spec.md）、
              OK-004 @ just-a-token（无斜杠 → unanchored）、OK-005 @ src/app/gone.py（精确锚·失联）
      —— 同时含活性 / 失联 / 无锚三态，条目区与锚活性区都非空，
        从而「两个区是否同源」这件事才真的可被断言。

覆盖（对应 `X产品化-M17设计稿-v1.md` §八 的 ①–⑩）：
    ① 等价性（drift 层）：`analyze` 与 `analyze_prepared(prepare(...))` 逐字节一致；
    ② 准备体形状：`prepare` 的前三项逐项等于 `scan_tree` 的返回、`design` 等于 `parse_file` 的返回；
       键序为 `["files", "dirs", "file_set", "design"]`；`dirs` / `file_set` **保持集合类型**；
       且**不含**任何派生键（采集体只放原始事实）；
    ③ 复用不变性 + 只读：同一 `prepared` 连续 3 次，每次结果与单独 `analyze` **逐字节一致**，
       且 `prepared` 在全部调用**前后**复合摘要不变（证明只读）；
    ④ 复用计数（库级）：计数探针下 `prepare` ×1 + `analyze_prepared` ×3 → 两计数器 **== 1**；
       **对照** `analyze` ×3 → 两计数器均为 **3**（N→1 的差异真实存在，而非「看起来更快」）；
    ⑤ 复用计数（**核心证据**，端到端）：同一探针下 `viewer.analyze` → `parser.parse_file` **== 1**；
       **对照**旧路径 `drift.analyze(...)` + `parser.parse_file(...)` → **== 2**（N→1 的差异真实存在）；
    ⑥ 输出未变（drift 层）：`selftest_m8` 仍 **12/12**；
    ⑦ 结构断言（防复发）：`inspect.getsource(drift.analyze)` **不含** `scan_tree(` 与 `parse_file(`；
       `inspect.getsource(viewer.analyze)` **不含** `parse_file(`——编排 / 汇合层只是一层委托；
    ⑧ 确定性 + 只读：同输入两次 `drift` 的 `to_json` / `render_text`、两次 `viewer.analyze`
       均逐字节一致；`prepare` / `analyze_prepared` / `analyze` / `viewer.analyze` 前后夹具目录
       复合摘要不变；
    ⑨ CLI 与输出回归：`view` 子命令 stdout 与 `viewer.render_html(viewer.analyze(...))` 逐字节一致、
       无 `\\r\\n`、退出码 0；`drift` 子命令 stdout 与库输出逐字节一致、退出码 0；
       坏设计文档 / 代码根非目录 → **1**；参数不足 → **2**；`selftest_m9` 9/9、`selftest_m11` 10/10、
       `selftest_m13` 10/10 仍通过（可视面产物逐字节稳定）；
    ⑩ 编号无关性（对外产物逐字节相同）：把 M17 **之前**的汇合方式（`drift.analyze` 一次 +
       自己再解析设计文档一次）在测试里作为**对照路径**复现，断言它与新汇合结果的**文档与 HTML
       逐字节相同**——即本项只改变「同一事实被采集**几次**」，不改变任何对外产物。

沿用 M0–M16 约定：不用 `subprocess` 管道，改临时文件重定向（本机沙箱禁建管道）。
"""

from __future__ import annotations

import hashlib
import inspect
import json
import tempfile
from pathlib import Path

from . import drift, graph_builder, parser, selftest_kit, viewer
from .selftest_kit import PKG_DIR, cli as _cli, run_module as _run_module, dir_digest as _dir_digest, make_min_root as _make_root


_DESIGN = (
    "# 夹具设计文档（M17 自测专用）\n"
    "\n"
    "### OK-001 — 精确锚 api.py（活性）\n"
    "- type: 公共接口\n"
    "- invariant: 示例不变量\n"
    "- change_control: free\n"
    "- severity: normal\n"
    "- evidence:\n"
    "  - src/app/api.py\n"
    "- action_policy: 警告\n"
    "\n"
    "### OK-002 — 精确锚 core.py（活性）\n"
    "- type: 数据完整性\n"
    "- invariant: 示例不变量\n"
    "- change_control: free\n"
    "- severity: normal\n"
    "- evidence:\n"
    "  - src/app/core.py\n"
    "- action_policy: 警告\n"
    "\n"
    "### OK-003 — 前缀锚 docs/（活性，多命中）\n"
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
    "\n"
    "### OK-005 — 精确锚 gone.py（失联）\n"
    "- type: 数据完整性\n"
    "- invariant: 示例不变量\n"
    "- change_control: free\n"
    "- severity: high\n"
    "- evidence:\n"
    "  - src/app/gone.py\n"
    "- action_policy: 阻断\n"
)


def _fixture(td: Path) -> tuple[Path, Path]:
    """建全套夹具，返回（代码根, 设计文档路径）。"""
    root = _make_root(td)
    design = td / "design.md"
    design.write_text(_DESIGN, encoding="utf-8")
    return root, design


def _prepared_digest(prepared: dict) -> str:
    """采集中间体的复合摘要。

    为什么不能直接 `json.dumps(prepared)`：`dirs` / `file_set` 是**集合**（非 JSON 可序列化），
    且切字典要保留**键序**（键序在本仓库是写死口径）。故按固定顺序逐项规范化：
    `keys` 原样拼接（护键序）、`files` 原样（已排序）、集合先 `sorted` 再序列化（护集合语义）。
    """
    rows = [
        "keys=" + "|".join(prepared),
        "files=" + json.dumps(prepared["files"], ensure_ascii=False),
        "dirs=" + json.dumps(sorted(prepared["dirs"]), ensure_ascii=False),
        "file_set=" + json.dumps(sorted(prepared["file_set"]), ensure_ascii=False),
        "design=" + parser.to_json(prepared["design"]),
    ]
    return hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest()


def _legacy_viewer_doc(root: Path, design_path: Path) -> dict:
    """M17 **之前**的汇合方式（对照路径）：`drift.analyze` 一次 + 自己再解析设计文档一次。

    刻意在测试里保留这条旧路径：它是对外产物「是否逐字节不变」的**对照基线**。
    若将来有人把「两次解析」改回来，本对照仍会通过，但 ⑤ 的计数断言会立刻失败——
    这正是「用计数而不是用感觉」的用意。
    """
    drift_doc = drift.analyze(root, design_path)
    design = parser.parse_file(design_path)
    graph = graph_builder.build_graph(root)

    doc = {
        "verdict": drift_doc["verdict"],
        "entry_count": drift_doc["entry_count"],
        "active_count": drift_doc["active_count"],
        "dangling_count": drift_doc["dangling_count"],
        "unanchored_count": len(drift_doc["unanchored_evidence"]),
        "uncovered_file_count": drift_doc["uncovered_file_count"],
        "node_count": graph["node_count"],
        "edge_count": graph["edge_count"],
        "cycle_count": len(graph["cycles"]),
        "entries": design["entries"],
        "active_anchors": drift_doc["active_anchors"],
        "dangling_anchors": drift_doc["dangling_anchors"],
        "unanchored_evidence": drift_doc["unanchored_evidence"],
        "uncovered_files": drift_doc["uncovered_files"],
        "nodes": graph["nodes"],
        "edges": graph["edges"],
        "cycles": graph["cycles"],
    }
    doc["sync"] = None
    doc["flow"] = None
    return doc


class _Probe:
    """计数探针：临时包装 `drift.scan_tree` 与 `parser.parse_file`，`try/finally` 还原。

    为什么不用「计时」：耗时受机器抖动影响、不可复现；**计数**才是「N 次变成 1 次」的直接证据。
    为什么只包这两个：它们正是 `drift.prepare` 里**与调用方无关**的两件事——枚举文件、解析设计文档；
    `analyze_prepared` 一个都不调，故计数即等价于「采集发生了几次」。
    """

    def __init__(self) -> None:
        self.calls = {"scan_tree": 0, "parse_file": 0}

    def __enter__(self) -> "_Probe":
        self._orig_scan = drift.scan_tree
        self._orig_parse = parser.parse_file

        def wrap_scan(root: str | Path):
            self.calls["scan_tree"] += 1
            return self._orig_scan(root)

        def wrap_parse(path: str | Path):
            self.calls["parse_file"] += 1
            return self._orig_parse(path)

        drift.scan_tree = wrap_scan
        parser.parse_file = wrap_parse
        return self

    def __exit__(self, *exc: object) -> bool:
        drift.scan_tree = self._orig_scan
        parser.parse_file = self._orig_parse
        return False


def test_equivalence_drift() -> None:
    """① 等价性（drift 层）：analyze 与「采集 + 构造」两段调用逐字节一致。"""
    with tempfile.TemporaryDirectory() as td_s:
        root, design = _fixture(Path(td_s))
        legacy = drift.analyze(root, design)
        split = drift.analyze_prepared(drift.prepare(root, design))
        assert drift.to_json(legacy) == drift.to_json(split), "两段调用应与 analyze 逐字节一致"
        assert drift.render_text(legacy) == drift.render_text(split), "文本口径同样不得有差异"


def test_prepared_shape() -> None:
    """② 准备体形状：三项取证原样、键序固定、集合不转列表、不含任何派生键。"""
    with tempfile.TemporaryDirectory() as td_s:
        root, design = _fixture(Path(td_s))
        prepared = drift.prepare(root, design)
        files, dirs, file_set = drift.scan_tree(root)
        assert list(prepared) == ["files", "dirs", "file_set", "design"], f"键序应为固定四项，实际 {list(prepared)}"
        assert prepared["files"] == files, "files 应为 scan_tree 返回的文件有序列表原样"
        assert prepared["dirs"] == dirs, "dirs 应为 scan_tree 返回的目录集合原样"
        assert prepared["file_set"] == file_set, "file_set 应为 scan_tree 返回的文件集合原样"
        assert prepared["design"] == parser.parse_file(design), "design 应为 parse_file 返回原样"
        # 集合类型必须保留：下游 `file_set - covered` 是集合差、`anchor_state` 按集合判成员
        assert isinstance(prepared["dirs"], set), "dirs 必须保持集合类型（不得 JSON 化为列表）"
        assert isinstance(prepared["file_set"], set), "file_set 必须保持集合类型（不得 JSON 化为列表）"
        # 采集体只放原始事实：派生结果（三态清单 / 证据索引 / 覆盖集）不得塞进来
        for forbidden in (
            "active_anchors",
            "dangling_anchors",
            "unanchored_evidence",
            "uncovered_files",
            "status_index",
            "covered",
            "entries",
        ):
            assert forbidden not in prepared, f"采集体不得含派生键 {forbidden!r}"


def test_reuse_is_pure() -> None:
    """③ 复用不变性 + 只读：同一 prepared 连续 3 次结果各自正确，且自身摘要不变。"""
    with tempfile.TemporaryDirectory() as td_s:
        root, design = _fixture(Path(td_s))
        prepared = drift.prepare(root, design)
        before = _prepared_digest(prepared)
        for i in range(3):
            got = drift.analyze_prepared(prepared)
            expected = drift.analyze(root, design)
            assert drift.to_json(got) == drift.to_json(expected), f"第 {i + 1} 次复用结果应与单独 analyze 逐字节一致"
        after = _prepared_digest(prepared)
        assert before == after, "analyze_prepared 不得就地修改传入的 prepared"


def test_reuse_counter_library_level() -> None:
    """④ 复用计数（库级）：prepare×1 + analyze_prepared×3 → 计数器 == 1；对照 analyze×3 → == 3。"""
    with tempfile.TemporaryDirectory() as td_s:
        root, design = _fixture(Path(td_s))

        with _Probe() as reuse:
            prepared = drift.prepare(root, design)
            for _ in range(3):
                drift.analyze_prepared(prepared)
        assert reuse.calls == {"scan_tree": 1, "parse_file": 1}, f"复用路径应只采集一次，实际 {reuse.calls}"

        with _Probe() as control:
            for _ in range(3):
                drift.analyze(root, design)
        assert control.calls == {"scan_tree": 3, "parse_file": 3}, f"对照路径应采集 3 次，实际 {control.calls}"


def test_reuse_counter_end_to_end() -> None:
    """⑤ 复用计数（核心证据，端到端）：viewer.analyze 只解析设计文档 1 次；旧路径为 2 次。"""
    with tempfile.TemporaryDirectory() as td_s:
        root, design = _fixture(Path(td_s))

        with _Probe() as probe:
            doc = viewer.analyze(root, design)
        assert probe.calls == {"scan_tree": 1, "parse_file": 1}, f"可视面应只采集一次，实际 {probe.calls}"
        assert doc["dangling_count"] == 1 and doc["unanchored_count"] == 1, "夹具三态应齐备（1 失联 + 1 无锚）"

        # 对照：M17 之前的调用序列（drift.analyze 内部解析一次 + 自己再解析一次）
        with _Probe() as legacy:
            drift.analyze(root, design)
            parser.parse_file(design)
        assert legacy.calls["parse_file"] == 2, f"旧路径应解析两次设计文档，实际 {legacy.calls}"
        assert legacy.calls["scan_tree"] == 1, f"旧路径的树枚举仍只有一次，实际 {legacy.calls}"


def test_selftest_m8_regression() -> None:
    """⑥ 输出未变（drift 层）：M8 自测仍全绿（其断言覆盖 M8 的输出口径）。"""
    if selftest_kit.in_regression():
        return
    rc, out, err = _run_module("selftest_m8")
    tail = out.decode("utf-8", "replace").strip().splitlines()[-1] if out else ""
    assert rc == 0 and tail == "12/12 passed", f"selftest_m8 末行应为 '12/12 passed'，实际 rc={rc} tail={tail!r}"


def test_structural_assertions() -> None:
    """⑦ 结构断言（防复发）：编排 / 汇合层只是一层委托，采集不得被再写一遍。"""
    src_drift = inspect.getsource(drift.analyze)
    assert "scan_tree(" not in src_drift, "drift.analyze 不得在编排层重新枚举文件"
    assert "parse_file(" not in src_drift, "drift.analyze 不得在编排层重新解析设计文档"
    assert "prepare(" in src_drift and "analyze_prepared(" in src_drift, "drift.analyze 应显式委托给两个唯一实现"

    src_viewer = inspect.getsource(viewer.analyze)
    assert "parse_file(" not in src_viewer, "viewer.analyze 不得自带第二份设计文档解析"
    assert "drift.prepare(" in src_viewer, "viewer.analyze 的采集应唯一收口在 drift.prepare"
    assert "drift.analyze_prepared(" in src_viewer, "viewer.analyze 的判定应唯一收口在 drift.analyze_prepared"


def test_determinism_and_read_only() -> None:
    """⑧ 确定性 + 只读：同输入两次逐字节一致；各入口前后夹具目录复合摘要不变。"""
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design = _fixture(td)
        before = _dir_digest(td)

        first = drift.analyze(root, design)
        second = drift.analyze(root, design)
        assert drift.to_json(first) == drift.to_json(second), "同输入两次 to_json 应逐字节一致"
        assert drift.render_text(first) == drift.render_text(second), "同输入两次 render_text 应逐字节一致"

        v1 = viewer.analyze(root, design)
        v2 = viewer.analyze(root, design)
        assert viewer.render_html(v1) == viewer.render_html(v2), "同输入两次可视面 HTML 应逐字节一致"

        drift.analyze_prepared(drift.prepare(root, design))
        after = _dir_digest(td)
        assert before == after, "全过程不得写夹具中的任何一个字节"


def test_numbering_independence() -> None:
    """⑩ 编号无关性：对外产物与「采集几次」无关——新旧汇合路径的文档与 HTML 逐字节相同。"""
    with tempfile.TemporaryDirectory() as td_s:
        root, design = _fixture(Path(td_s))
        new = viewer.analyze(root, design)
        legacy = _legacy_viewer_doc(root, design)
        # 逐键同序同值：`json.dumps` 保留插入顺序，故键序一并受检
        assert json.dumps(new, ensure_ascii=False) == json.dumps(legacy, ensure_ascii=False), "汇合文档应逐字段（含键序）相同"
        assert new["entries"] == legacy["entries"], "条目区应同源同值"
        assert viewer.render_html(new) == viewer.render_html(legacy), "可视面 HTML 应逐字节相同"


def test_cli_and_regression() -> None:
    """⑨ CLI 与输出回归：stdout 与库输出逐字节一致、无 `\\r\\n`；错误码语义不变；m9 / m11 / m13 仍通过。"""
    if selftest_kit.in_regression():
        return
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design = _fixture(td)

        lib = viewer.analyze(root, design)
        code, out, _err = _cli("view", str(root), str(design))
        assert code == 0, f"view 子命令应退出码 0，实际 {code}"
        assert out == viewer.render_html(lib).encode("utf-8"), "CLI stdout 应与库输出逐字节一致"
        assert b"\r\n" not in out, "stdout 不得被翻译成 CRLF"

        drift_lib = drift.analyze(root, design)
        code_d, out_d, _err_d = _cli("drift", str(root), str(design))
        assert code_d == 0, f"drift 子命令应退出码 0，实际 {code_d}"
        assert out_d == drift.to_json(drift_lib).encode("utf-8"), "drift stdout 应与库输出逐字节一致"
        code_dt, out_dt, _err_dt = _cli("drift", str(root), str(design), "--text")
        assert code_dt == 0 and out_dt == drift.render_text(drift_lib).encode("utf-8"), "--text 应与库输出逐字节一致"

        bad_design = td / "bad-design.md"
        bad_design.write_text("这一行根本不是设计文档\n", encoding="utf-8")
        assert _cli("view", str(root), str(bad_design))[0] == 1, "坏设计文档应退出码 1"
        assert _cli("drift", str(root), str(bad_design))[0] == 1, "坏设计文档应退出码 1"
        assert _cli("view", str(td / "nope"), str(design))[0] == 1, "代码根非目录应退出码 1"
        assert _cli("drift", str(td / "nope"), str(design))[0] == 1, "代码根非目录应退出码 1"
        assert _cli("view", str(root))[0] == 2, "view 参数不足应退出码 2"
        assert _cli("drift", str(root))[0] == 2, "drift 参数不足应退出码 2"

        for mod, expect in (
            ("selftest_m9", "9/9 passed"),
            ("selftest_m11", "10/10 passed"),
            ("selftest_m13", "10/10 passed"),
        ):
            rc, out_r, _err_r = _run_module(mod)
            tail = out_r.decode("utf-8", "replace").strip().splitlines()[-1] if out_r else ""
            assert rc == 0 and tail == expect, f"{mod} 末行应为 {expect!r}，实际 {tail!r}"


def main() -> int:
    tests = (
        test_equivalence_drift,
        test_prepared_shape,
        test_reuse_is_pure,
        test_reuse_counter_library_level,
        test_reuse_counter_end_to_end,
        test_selftest_m8_regression,
        test_structural_assertions,
        test_determinism_and_read_only,
        test_numbering_independence,
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
