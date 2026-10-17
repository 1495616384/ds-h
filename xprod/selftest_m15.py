"""M15 自测：把「流程文档解析复用」的验收点写成可执行断言。

核心思路：**夹具临时自建**——每次测试在临时目录里现造一个最小代码根 + 设计文档 + 流程文档 +
一份分工计划（5 份改动），使本自测**不依赖**任何归档基线副本、不依赖网络；
本文件与 `flow.py` 同样不含冻结链目录名字面量（由 M0 自测第三条校验）。

主夹具（决定各测试的期望值）：
    代码根：src/app/{__init__,api,core,notify,other}.py、docs/{guide,spec}.md
      ——**故意不建** report.py / archive.py，使 FL-002 的两个步骤锚**失联（断链）**，
        从而「复用」这件事在「有断链」的输入上也照样被断言到。
    设计文档：OK-001 @ src/app/api.py、OK-002 @ src/app/core.py、
              OK-003 @ docs/（前缀锚）、OK-004 @ just-a-token（无斜杠 → unanchored）
    流程文档：
      FL-001「下单到发货」：S1@api.py → S2@core.py → S3@notify.py → S4（**无锚**）
      FL-002「日报汇总」：R1@report.py → R2@archive.py（两锚**均断链**）
    各 diff：A 改 api.py、B 改 core.py、C 改 notify.py、D 改 other.py、E 再改一次 core.py

覆盖（对应 `X产品化-M15设计稿-v1.md` §八 的 ①–⑩）：
    ① 等价性（无 diff）：`analyze` 与 `analyze_prepared(prepare(...))` 逐字节一致；
    ② 等价性（有 diff）：四类 diff（命中直接步骤 / 命中失联步骤 / 无命中 / 无 diff）逐字节一致；
    ③ 准备体形状：`prepare` == `analyze` 输出**去掉 `impact` 键**，且键序为四键固定序；
    ④ 复用不变性：同一 `prepared` 连续 5 次（含同一 diff 重复、也含不同 diff）结果各自与单独
       `analyze` 逐字节一致，且 `prepared` 在前后**摘要不变**（证明只读）；
    ⑤ 复用计数（核心证据，库级）：计数探针下 `prepare` ×1 + `analyze_prepared` ×5 → 两计数器 **== 1**；
       **对照** `analyze` ×5 → 两计数器均为 **5**（N→1 的差异真实存在）；
    ⑥ 复用计数（核心证据，端到端）：同一探针下 `conflict.analyze_plan`（5 份改动 + 流程文档）
       → `flow.parse_flow_doc` 计数 **== 1**（M14 逐改动重复解析已消除）；
    ⑦ 结构断言（防复发）：`inspect.getsource(flow.analyze)` **不含** `scan_tree(` 与 `parse_flow_doc(`
       ——证明 `analyze` 只是委托，采集不会在编排层被再写一遍；
    ⑧ 确定性：同输入两次 `to_json` / `render_text` 逐字节一致；
    ⑨ 只读：`prepare` / `analyze_prepared` / `analyze` 前后**夹具目录复合摘要不变**；
    ⑩ CLI 与 M14 回归：`flow` 子命令 stdout 与库输出逐字节一致、无 `\\r\\n`、退出码 0；
       坏流程文档 / 代码根非目录 → 1；参数不足 / `--diff` 缺值 → 2；`selftest_m14` 仍 10/10。

沿用 M0–M14 约定：不用 `subprocess` 管道，改临时文件重定向（本机沙箱禁建管道）。
"""

from __future__ import annotations

import hashlib
import inspect
import json
import tempfile
from pathlib import Path

from . import conflict, drift, flow
from .selftest_kit import PKG_DIR, cli as _cli, run_module as _run_module, dir_digest as _dir_digest, diff_one_file as _diff


_DESIGN = (
    "# 夹具设计文档（M15 自测专用）\n"
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
    "# 流程夹具（M15 自测专用）\n"
    "\n"
    "## FL-001 — 下单到发货\n"
    "\n"
    "- step:\n"
    "  - S1: 校验库存 @ src/app/api.py\n"
    "  - S2: 扣减库存 @ src/app/core.py\n"
    "  - S3: 发货通知 @ src/app/notify.py\n"
    "  - S4: 人工复核\n"
    "- edge:\n"
    "  - S1 -> S2\n"
    "  - S2 -> S3\n"
    "  - S3 -> S4\n"
    "\n"
    "## FL-002 — 日报汇总\n"
    "\n"
    "- step:\n"
    "  - R1: 汇总 @ src/app/report.py\n"
    "  - R2: 归档 @ src/app/archive.py\n"
    "- edge:\n"
    "  - R1 -> R2\n"
)

# id → (变更文件, 该文件新内容)；A–E 与 M14 自测同形（含「E 与 B 改同一文件」）
_CHANGES = (
    ("A", "src/app/api.py", "from app.core import X\nA = 1\n"),
    ("B", "src/app/core.py", "X = 2\n"),
    ("C", "src/app/notify.py", "N = 2\n"),
    ("D", "src/app/other.py", "Z = 4\n"),
    ("E", "src/app/core.py", "X = 3\n"),
)

# 额外造一份「命中失联步骤 R1（report.py）」的 diff，用于 ② 覆盖「断链 + 复用」组合
_DANGLING_DIFF = ("F", "src/app/report.py", "R = 9\n")


def _make_root(td: Path) -> Path:
    """建最小代码根（层层 `__init__.py`，使 M3 影响分析器有依赖图节点可用）。"""
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
    for cid, path, new in (*_CHANGES, _DANGLING_DIFF):
        dp = td / f"{cid}.diff"
        dp.write_text(_diff(path, "old\n", new), encoding="utf-8")
        diffs[cid] = dp
    return root, design, flow_doc, diffs


def _plan_with_all_changes(td: Path, diffs: dict[str, Path]) -> Path:
    """造一份含 A–E 五份改动（id 升序）的分工计划，供 ⑥ 端到端计数用。"""
    changesets = [{"id": cid, "diff": diffs[cid].name} for cid, _, _ in _CHANGES]
    plan = td / "plan.json"
    plan.write_text(
        json.dumps({"plan_id": "M15 夹具", "changesets": changesets}, ensure_ascii=False),
        encoding="utf-8",
    )
    return plan


def _doc_digest(doc: dict) -> str:
    """对内存中的文档取摘要——用本包**规范序列化**（保留键序），故「值」与「键序」一并受保护。

    为什么不用 `json.dumps(..., sort_keys=True)`：`sort_keys` 会把键序抹平，于是「键序被就地改乱」
    这类污染照不出来；而键序在本仓库是**写死口径**（确定性 / 逐字节可比），必须一并纳入只读证据。
    """
    return hashlib.sha256(flow.to_json(doc).encode("utf-8")).hexdigest()


class _Probe:
    """计数探针：临时包装 `flow.parse_flow_doc` 与 `drift.scan_tree`，`try/finally` 还原。

    为什么不用「计时」：耗时受机器抖动影响、不可复现；**计数**才是「N 次变成 1 次」的直接证据。
    """

    def __init__(self) -> None:
        self.calls = {"parse_flow_doc": 0, "scan_tree": 0}

    def __enter__(self) -> "_Probe":
        self._orig_parse = flow.parse_flow_doc
        self._orig_scan = drift.scan_tree

        def wrap_parse(text: str):
            self.calls["parse_flow_doc"] += 1
            return self._orig_parse(text)

        def wrap_scan(root: Path):
            self.calls["scan_tree"] += 1
            return self._orig_scan(root)

        flow.parse_flow_doc = wrap_parse
        drift.scan_tree = wrap_scan
        return self

    def __exit__(self, *exc: object) -> bool:
        flow.parse_flow_doc = self._orig_parse
        drift.scan_tree = self._orig_scan
        return False


def test_equivalence_without_diff() -> None:
    """① 等价性（无 diff）：`analyze` 与「采集 + 构造」两段调用逐字节一致。"""
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, _design, flow_doc, _diffs = _fixture(td)
        legacy = flow.analyze(flow_doc, root)
        split = flow.analyze_prepared(flow.prepare(flow_doc, root))
    assert flow.to_json(legacy) == flow.to_json(split), "无 diff 时两段调用应与 analyze 逐字节一致"
    assert legacy["impact"] is None and split["impact"] is None, "无 diff 时 impact 应为 null"


def test_equivalence_with_diff() -> None:
    """② 等价性（有 diff）：命中直接被改文件 / 命中失联锚 / 无命中三类都逐字节一致。"""
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, _design, flow_doc, diffs = _fixture(td)
        for cid in ("A", "B", "F", "D"):  # A 命中 S1；B 命中 S2；F 命中失联的 R1；D 无命中
            d = diffs[cid]
            legacy = flow.analyze(flow_doc, root, d)
            split = flow.analyze_prepared(flow.prepare(flow_doc, root), d)
            assert flow.to_json(legacy) == flow.to_json(split), f"{cid}：有 diff 时两段调用应逐字节一致"
            for key in ("direct_steps", "affected_steps", "dangling_steps", "verdict"):
                assert legacy["impact"][key] == split["impact"][key], f"{cid}：impact.{key} 应一致"


def test_prepared_shape() -> None:
    """③ 准备体形状：`prepare` == `analyze` 输出去掉 `impact` 键；键序为四键固定序。"""
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, _design, flow_doc, diffs = _fixture(td)
        prepared = flow.prepare(flow_doc, root)
        full = flow.analyze(flow_doc, root, diffs["A"])
        stripped = {k: v for k, v in full.items() if k != "impact"}
    assert list(prepared) == ["flow_count", "step_count", "edge_count", "flows"], f"键序应为四键固定序，实际 {list(prepared)}"
    assert prepared == stripped, "prepare 的值应与 analyze 输出去掉 impact 后完全相同"
    assert list(full) == ["flow_count", "step_count", "edge_count", "flows", "impact"], f"analyze 键序不得变，实际 {list(full)}"


def test_reuse_is_pure() -> None:
    """④ 复用不变性：同一 `prepared` 连续 5 次（含重复 diff）结果各自正确，且自身摘要不变。"""
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, _design, flow_doc, diffs = _fixture(td)
        prepared = flow.prepare(flow_doc, root)
        before = _doc_digest(prepared)
        order = ["A", "B", "A", "F", "D"]  # 含重复同一 diff，证明「复用不串味」
        results = [flow.analyze_prepared(prepared, diffs[cid]) for cid in order]
        after = _doc_digest(prepared)
        assert before == after, "analyze_prepared 不得就地修改传入的 prepared"
        # 断言必须留在临时目录存活期内（目录一回收，`analyze` 会因代码根不存在而抛 FlowError）
        for cid, got in zip(order, results):
            expected = flow.analyze(flow_doc, root, diffs[cid])
            assert flow.to_json(got) == flow.to_json(expected), f"{cid}：复用结果应与单独 analyze 逐字节一致"
        assert flow.to_json(results[0]) == flow.to_json(results[2]), "同一 diff 复用两次应得到同一结果"


def test_reuse_counter_library_level() -> None:
    """⑤ 复用计数（核心证据）：prepare×1 + analyze_prepared×5 → 计数器 == 1；对照 analyze×5 → == 5。"""
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, _design, flow_doc, diffs = _fixture(td)
        order = ["A", "B", "C", "D", "F"]

        with _Probe() as reuse:
            prepared = flow.prepare(flow_doc, root)
            for cid in order:
                flow.analyze_prepared(prepared, diffs[cid])
        assert reuse.calls == {"parse_flow_doc": 1, "scan_tree": 1}, f"复用路径应只采集一次，实际 {reuse.calls}"

        with _Probe() as control:
            for cid in order:
                flow.analyze(flow_doc, root, diffs[cid])
        assert control.calls == {"parse_flow_doc": 5, "scan_tree": 5}, f"对照路径应采集 5 次，实际 {control.calls}"


def test_reuse_counter_end_to_end() -> None:
    """⑥ 复用计数（端到端）：`conflict.analyze_plan`（5 份改动）只解析流程文档 1 次。"""
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design, flow_doc, diffs = _fixture(td)
        plan = _plan_with_all_changes(td, diffs)
        with _Probe() as probe:
            doc = conflict.analyze_plan(plan, root, design, flow_doc)
    assert probe.calls == {"parse_flow_doc": 1, "scan_tree": 1}, f"M14 逐改动重复解析应已消除，实际 {probe.calls}"
    assert [r["id"] for r in doc["flow_of_changesets"]] == ["A", "B", "C", "D", "E"], "流程面应覆盖全部 5 份改动"


def test_analyze_is_thin_delegation() -> None:
    """⑦ 结构断言（防复发）：`analyze` 源码不含 `scan_tree(` / `parse_flow_doc(`——采集不得被再写一遍。"""
    src = inspect.getsource(flow.analyze)
    assert "scan_tree(" not in src, "analyze 不得在编排层重新扫树"
    assert "parse_flow_doc(" not in src, "analyze 不得在编排层重新解析流程文档"
    assert "prepare(" in src and "analyze_prepared(" in src, "analyze 应显式委托给两个唯一实现"


def test_determinism() -> None:
    """⑧ 确定性：同输入两次 `to_json` / `render_text` 逐字节一致。"""
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, _design, flow_doc, diffs = _fixture(td)
        prepared = flow.prepare(flow_doc, root)
        first, second = flow.analyze_prepared(prepared, diffs["A"]), flow.analyze_prepared(prepared, diffs["A"])
        assert flow.to_json(first) == flow.to_json(second), "同输入两次 to_json 应逐字节一致"
        assert flow.render_text(first) == flow.render_text(second), "同输入两次 render_text 应逐字节一致"
        assert flow.render_text(flow.analyze_prepared(prepared)) == flow.render_text(flow.analyze_prepared(prepared))


def test_read_only() -> None:
    """⑨ 只读：`prepare` / `analyze_prepared` / `analyze` 前后夹具目录复合摘要不变。"""
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design, flow_doc, diffs = _fixture(td)
        before = _dir_digest(td)
        prepared = flow.prepare(flow_doc, root)
        flow.analyze_prepared(prepared, diffs["A"])
        flow.analyze_prepared(prepared)
        flow.analyze(flow_doc, root, diffs["F"])
        after = _dir_digest(td)
    assert before == after, "全过程不得写夹具中的任何一个字节"


def test_cli_and_m14_regression() -> None:
    """⑩ CLI 与 M14 回归：stdout 与库输出逐字节一致、无 `\\r\\n`；错误码语义不变；selftest_m14 仍 10/10。"""
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, _design, flow_doc, diffs = _fixture(td)
        expected = flow.to_json(flow.analyze(flow_doc, root, diffs["A"])).encode("utf-8")
        code, out, _err = _cli("flow", str(flow_doc), str(root), "--diff", str(diffs["A"]))
        assert code == 0, f"flow 子命令应退出码 0，实际 {code}"
        assert out == expected, "CLI stdout 应与库输出逐字节一致"
        assert b"\r\n" not in out, "stdout 不得被翻译成 CRLF"

        expected_text = flow.render_text(flow.analyze(flow_doc, root)).encode("utf-8")
        code_t, out_t, _err_t = _cli("flow", str(flow_doc), str(root), "--text")
        assert code_t == 0 and out_t == expected_text, "--text 与无 --diff 组合应与库输出逐字节一致"

        bad = td / "bad-flow.md"
        bad.write_text("这一行根本不像流程文档\n", encoding="utf-8")
        assert _cli("flow", str(bad), str(root))[0] == 1, "坏流程文档应退出码 1"
        assert _cli("flow", str(flow_doc), str(td / "nope"))[0] == 1, "代码根非目录应退出码 1"
        assert _cli("flow", str(flow_doc))[0] == 2, "参数不足应退出码 2"
        assert _cli("flow", str(flow_doc), str(root), "--diff")[0] == 2, "--diff 缺值应退出码 2"

        code_r, out_r, _err_r = _run_module("selftest_m14")
        tail = out_r.decode("utf-8", "replace").strip().splitlines()[-1] if out_r else ""
        assert code_r == 0 and tail == "10/10 passed", f"M14 流程层口径不得受重构影响，实际末行 {tail!r}"


def main() -> int:
    tests = (
        test_equivalence_without_diff,
        test_equivalence_with_diff,
        test_prepared_shape,
        test_reuse_is_pure,
        test_reuse_counter_library_level,
        test_reuse_counter_end_to_end,
        test_analyze_is_thin_delegation,
        test_determinism,
        test_read_only,
        test_cli_and_m14_regression,
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
