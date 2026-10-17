"""M18 自测：把「三套同名 `prepare` 的区分治理（消费端必需键自校验）」的验收点写成可执行断言。

核心思路：**夹具临时自建**——每次测试在临时目录里现造一个最小代码根 + 设计文档 + 流程文档 +
两份改动 diff，使本自测**不依赖**任何归档基线副本、不依赖网络；本文件与产品模块同样不含
冻结链目录名字面量（由 M0 自测第三条校验全部 `xprod/**/*.py`，含本文件）。

主夹具（决定各测试的期望值）：
    代码根：src/app/{__init__,api,core,notify}.py、docs/{guide,spec}.md
      —— `api.py` 里有 `from app.core import X`，故依赖图上有一条 `api.py → core.py` 的边。
    设计文档：OK-001 @ src/app/api.py（精确锚·活性）、OK-002 @ src/app/core.py（精确锚·活性）、
              OK-003 @ docs/（前缀锚·活性，多命中）、OK-004 @ just-a-token（无斜杠 → unanchored）、
              OK-005 @ src/app/gone.py（精确锚·失联）
    流程文档：FL-001「下单到发货」：S1@api.py → S2@core.py → S3@notify.py → S4（无锚），
              三条边串成一条链，使「沿正向下游闭包」真有内容可用。
    改动：A 改 api.py、B 改 core.py（B 用于把 `conflict` 的两改动组合喂出来）。

覆盖（对应 `X产品化-M18设计稿-v1.md` §八 的 ①–⑩）：
    ① 误传被诊断（**核心证据**）：三例**交叉投喂**（flow 体→drift 入口 / drift 体→impact 入口 /
       impact 体→flow 入口）断言**错误类型 + 消息含缺失键名 + 消息含期望产出方**；
       且三例均用**真实** `prepare` 产物（而非手工假字典）——否则不能证明三套真实体确实互不兼容；
    ② 合法路径逐字节不变：`analyze`（等价旧路径）与 `analyze_prepared(prepare(...))`（新拆分路径）
       对三个模块的 `to_json` / `render_text` **逐字节一致**；
    ③ 常量与实现同源：`list(prepare(...)) == list(PREPARED_REQUIRED_KEYS)` 对**三个**模块成立，
       且对三个合法采集体 `missing` 均为空（校验对合法输入恒真）；
    ④ 既有契约回归：`selftest_m15` / `selftest_m16` / `selftest_m17` 各 **10/10** 仍通过
       （三者都含键序断言，证明**零契约修订**下契约未破）；
    ⑤ 输出未变（回归）：`selftest_m7` 口径不受影响；`selftest_m8` **12/12**、
       `selftest_m9` **9/9**、`selftest_m11` **10/10**、`selftest_m13` **10/10** 仍通过
       （`selftest_m2` / `selftest_m3` 需命令行传入代码根，按 M17 §八 先例由里程碑级全域回归覆盖）；
    ⑥ 结构断言（防复发）：`inspect.getsource` 三个 `analyze_prepared` **均含** `PREPARED_REQUIRED_KEYS`；
       三个 `prepare` 源码**均不含**该校验（证明校验没有跑到采集端——职责边界不漂移）；
    ⑦ 三个必需键集合两两不同：固化「自校验之所以可判别的**前提**」，防今后形状趋同后校验静默失效；
    ⑧ 只读 + 确定性：校验通过后同一 `prepared` 连续复用其复合摘要不变；同输入两次输出逐字节一致；
       全过程夹具目录复合摘要不变；
    ⑨ CLI 与退出码回归：`flow` / `drift` / `impact` / `conflict` / `view` 正常路径 stdout 与库输出
       **逐字节一致**、退出码 **0**、**无 `\\r\\n`**；错误路径（坏设计文档 / 坏流程文档 / 代码根非目录）
       仍为 **1**；参数不足 / 缺值仍为 **2**——新增校验**不改变**退出码语义；
    ⑩ 编号无关性 + 全域回归：本项**只**改「误传时的错误消息」与「新增一个只读常量」，由 ②/④/⑤ 强制；
       逐模块跑**无需命令行参数**的 M0–M17 全域自测，断言全绿（M4 无自测；M18 即本模块，由本文件
       一次运行验收；`selftest_m2` / `selftest_m3` 需命令行传入代码根，由里程碑级全域回归覆盖）。

沿用 M0–M17 约定：不用 `subprocess` 管道，改临时文件重定向（本机沙箱禁建管道）。
"""

from __future__ import annotations

import hashlib
import inspect
import json
import re
import tempfile
from pathlib import Path

from . import conflict, drift, flow, impact_analyzer, parser, selftest_kit, viewer
from .selftest_kit import PKG_DIR, cli as _cli, run_module as _run_module, last_line as _last_line, dir_digest as _dir_digest, diff_one_file as _diff, capture_raises as _capture, make_min_root as _make_root, make_fixture as _fixture


_DESIGN = (
    "# 夹具设计文档（M18 自测专用）\n"
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

_FLOW = (
    "# 流程夹具（M18 自测专用）\n"
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
)

# id → (变更文件, 该文件新内容)；A 命中直接步骤 S1、B 命中 S2，足以把 `conflict` 的两改动组合喂出来
_CHANGES = (
    ("A", "src/app/api.py", "from app.core import X\nA = 1\n"),
    ("B", "src/app/core.py", "X = 2\n"),
)

_ALL_PASSED = re.compile(r"^(?P<ok>\d+)/(?P<total>\d+) passed$")


def _plan(td: Path, cids: tuple[str, ...], diffs: dict[str, Path]) -> Path:
    """造一份分工计划（`diff` 用文件名，相对计划文件所在目录解析）；id 升序以满足 `load_plan` 规范化。"""
    changesets = [{"id": cid, "diff": diffs[cid].name} for cid in sorted(cids)]
    plan = td / "plan.json"
    plan.write_text(
        json.dumps({"plan_id": "M18 夹具", "changesets": changesets}, ensure_ascii=False),
        encoding="utf-8",
    )
    return plan


def _canon(obj: object) -> object:
    """把含集合的采集体规范化为可 JSON 序列化的等价物（集合先排序，字典保持键序）。"""
    if isinstance(obj, set):
        return sorted(obj)
    if isinstance(obj, dict):
        return {k: _canon(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_canon(v) for v in obj]
    return obj


def _prepared_digest(prepared: dict) -> str:
    """采集体复合摘要。

    为什么不能直接 `json.dumps(prepared)`：`drift` 的 `dirs` / `file_set` 是**集合**（非 JSON 可
    序列化），且切字典要保留**键序**（键序在本仓库是写死口径）。故经 `_canon` 规范后再序列化。
    """
    return hashlib.sha256(
        json.dumps(_canon(prepared), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _all_passed(tail: str) -> bool:
    m = _ALL_PASSED.match(tail)
    return bool(m) and m.group("ok") == m.group("total")


def test_cross_feed_diagnosis() -> None:
    """① 误传被诊断（核心证据）：三例交叉投喂，断言错误类型 + 缺失键名 + 期望产出方。

    三例都用**真实** `prepare` 产物——只有真实体才能证明「三套同名采集体确实互不兼容」。
    """
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design, flow_doc, diffs = _fixture(td, design_text=_DESIGN, flow_text=_FLOW, changes=_CHANGES)

        flow_prepared = flow.prepare(flow_doc, root)
        impact_prepared = impact_analyzer.prepare(root, design)
        drift_prepared = drift.prepare(root, design)

        # 真实体确实互不兼容（键集合两两不同）——这是「自校验能判别」的前提
        assert len({tuple(flow_prepared), tuple(impact_prepared), tuple(drift_prepared)}) == 3, \
            "三套真实采集体必须两两不同，否则误传无从判别"

        diff_text = _diff("src/app/api.py", "old\n", "new\n")

        # 例1：flow 体 → drift 入口
        miss1 = [k for k in drift.PREPARED_REQUIRED_KEYS if k not in flow_prepared]
        exc1 = _capture(drift.analyze_prepared, flow_prepared)
        assert isinstance(exc1, drift.DriftError), f"应抛 DriftError，实际 {type(exc1).__name__}"
        msg1 = str(exc1)
        assert msg1 == f"analyze_prepared 收到非 drift 采集体：缺少必需键 {miss1}；应由 drift.prepare 产出", msg1
        for key in ("files", "dirs", "file_set", "design"):
            assert key in msg1, f"消息应含缺失键名 {key!r}：{msg1}"
        assert "drift.prepare" in msg1, f"消息应含期望产出方：{msg1}"

        # 例2：drift 体 → impact 入口
        miss2 = [k for k in impact_analyzer.PREPARED_REQUIRED_KEYS if k not in drift_prepared]
        exc2 = _capture(impact_analyzer.analyze_prepared, drift_prepared, diff_text)
        assert isinstance(exc2, impact_analyzer.ImpactError), f"应抛 ImpactError，实际 {type(exc2).__name__}"
        msg2 = str(exc2)
        assert msg2 == (
            f"analyze_prepared 收到非 impact_analyzer 采集体：缺少必需键 {miss2}；"
            f"应由 impact_analyzer.prepare 产出"
        ), msg2
        assert "graph" in msg2, f"消息应含缺失键名 'graph'：{msg2}"
        assert "impact_analyzer.prepare" in msg2, f"消息应含期望产出方：{msg2}"

        # 例3：impact 体 → flow 入口
        miss3 = [k for k in flow.PREPARED_REQUIRED_KEYS if k not in impact_prepared]
        exc3 = _capture(flow.analyze_prepared, impact_prepared, diffs["A"])
        assert isinstance(exc3, flow.FlowError), f"应抛 FlowError，实际 {type(exc3).__name__}"
        msg3 = str(exc3)
        assert msg3 == f"analyze_prepared 收到非 flow 采集体：缺少必需键 {miss3}；应由 flow.prepare 产出", msg3
        for key in ("flow_count", "step_count", "edge_count", "flows"):
            assert key in msg3, f"消息应含缺失键名 {key!r}：{msg3}"
        assert "flow.prepare" in msg3, f"消息应含期望产出方：{msg3}"


def test_legal_path_byte_identical() -> None:
    """② 合法路径逐字节不变：等价旧路径（`analyze`）与新拆分路径（`analyze_prepared(prepare(...))`）一致。"""
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design, flow_doc, diffs = _fixture(td, design_text=_DESIGN, flow_text=_FLOW, changes=_CHANGES)

        legacy_f = flow.analyze(flow_doc, root, diffs["A"])
        split_f = flow.analyze_prepared(flow.prepare(flow_doc, root), diffs["A"])
        assert flow.to_json(legacy_f) == flow.to_json(split_f), "flow：两路径 to_json 应逐字节一致"
        assert flow.render_text(legacy_f) == flow.render_text(split_f), "flow：两路径 render_text 应逐字节一致"

        legacy_d = drift.analyze(root, design)
        split_d = drift.analyze_prepared(drift.prepare(root, design))
        assert drift.to_json(legacy_d) == drift.to_json(split_d), "drift：两路径 to_json 应逐字节一致"
        assert drift.render_text(legacy_d) == drift.render_text(split_d), "drift：两路径 render_text 应逐字节一致"

        legacy_i = impact_analyzer.analyze_files(diffs["A"], root, design)
        split_i = impact_analyzer.analyze_prepared(
            impact_analyzer.prepare(root, design), impact_analyzer.read_diff(diffs["A"])
        )
        assert impact_analyzer.to_json(legacy_i) == impact_analyzer.to_json(split_i), "impact：两路径 to_json 应逐字节一致"
        assert impact_analyzer.render_text(legacy_i) == impact_analyzer.render_text(split_i), "impact：两路径 render_text 应逐字节一致"


def test_constant_matches_prepare() -> None:
    """③ 常量与实现同源：`prepare` 的键序逐字等于 `PREPARED_REQUIRED_KEYS`；合法体 missing 为空。"""
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design, flow_doc, _diffs = _fixture(td, design_text=_DESIGN, flow_text=_FLOW, changes=_CHANGES)

        flow_prepared = flow.prepare(flow_doc, root)
        impact_prepared = impact_analyzer.prepare(root, design)
        drift_prepared = drift.prepare(root, design)

        assert list(flow_prepared) == list(flow.PREPARED_REQUIRED_KEYS), \
            f"flow 常量与实现不同源：{list(flow.PREPARED_REQUIRED_KEYS)} vs {list(flow_prepared)}"
        assert list(impact_prepared) == list(impact_analyzer.PREPARED_REQUIRED_KEYS), \
            f"impact 常量与实现不同源：{list(impact_analyzer.PREPARED_REQUIRED_KEYS)} vs {list(impact_prepared)}"
        assert list(drift_prepared) == list(drift.PREPARED_REQUIRED_KEYS), \
            f"drift 常量与实现不同源：{list(drift.PREPARED_REQUIRED_KEYS)} vs {list(drift_prepared)}"

        # 校验对合法输入恒真：三个真实体的 missing 均为空
        assert [k for k in flow.PREPARED_REQUIRED_KEYS if k not in flow_prepared] == []
        assert [k for k in impact_analyzer.PREPARED_REQUIRED_KEYS if k not in impact_prepared] == []
        assert [k for k in drift.PREPARED_REQUIRED_KEYS if k not in drift_prepared] == []


def test_contract_regression() -> None:
    """④ 既有契约回归：M15 / M16 / M17 自测各 10/10（三者都含键序断言，证明零契约修订）。"""
    if selftest_kit.in_regression():
        return
    for mod in ("selftest_m15", "selftest_m16", "selftest_m17"):
        rc, out, _err = _run_module(mod)
        tail = _last_line(out)
        assert rc == 0 and tail == "10/10 passed", f"{mod} 应为 10/10 通过，实际 rc={rc} tail={tail!r}"


def test_output_regression() -> None:
    """⑤ 输出未变（回归）：M7 口径不受影响；M8 / M9 / M11 / M13 各自计数仍满。

    **不内嵌 `selftest_m2` / `selftest_m3`**：它们需在命令行传入代码根（其根即归档基线副本，
    与 `samples/expected-graph.json` 固定真值配套），而 M0 自测第三条**禁止产品源码出现冻结链
    目录名**——故按 M17 设计稿 §八 的同一条先例，改由里程碑级**全域回归**在自测外覆盖
    （`selftest_m3` 归 M3 口径，与本项无关；M18 只保证不经它改变其任何合法输入产物）。
    """
    if selftest_kit.in_regression():
        return
    for mod, expect in (
        ("selftest_m7", None),
        ("selftest_m8", "12/12 passed"),
        ("selftest_m9", "9/9 passed"),
        ("selftest_m11", "10/10 passed"),
        ("selftest_m13", "10/10 passed"),
    ):
        rc, out, _err = _run_module(mod)
        tail = _last_line(out)
        assert rc == 0, f"{mod} 应退出码 0，实际 {rc}；末行 {tail!r}"
        if expect is None:
            assert _all_passed(tail), f"{mod} 末行应为 'N/N passed'，实际 {tail!r}"
        else:
            assert tail == expect, f"{mod} 末行应为 {expect!r}，实际 {tail!r}"


def test_structural_assertions() -> None:
    """⑥ 结构断言（防复发）：**输入**校验只在消费端入口、且经**唯一实现**；采集端含**产出**不变量、不含输入校验。

    M20 定点替换（原为匹配文本 `missing = [k for k in PREPARED_REQUIRED_KEYS`）——改为**守结构**：
    三个 `analyze_prepared` 必须**调用**共享实现 `contract.require_prepared_keys`，且**不得内联**消息模板；
    三个 `prepare` 必须**调用** `contract.assert_produced_keys`，且**不得调用** `require_prepared_keys`
    （输入校验属消费端职责）。理由：模板已收口为**全仓唯一**（只在 `contract.py`），
    仍按源码文本匹配会随实现改写即失真（M19 已因此不得不精化一次）。
    """
    for mod in (flow, impact_analyzer, drift):
        src_ap = inspect.getsource(mod.analyze_prepared)
        assert "PREPARED_REQUIRED_KEYS" in src_ap, f"{mod.__name__}.analyze_prepared 应含入口必需键校验"
        assert "require_prepared_keys" in src_ap, \
            f"{mod.__name__}.analyze_prepared 应调用共享实现 contract.require_prepared_keys"
        assert "收到非" not in src_ap and "属生产者缺陷" not in src_ap, \
            f"{mod.__name__}.analyze_prepared 不得内联消息模板（模板全仓唯一，只在 contract.py）"
        src_prep = inspect.getsource(mod.prepare)
        assert "PREPARED_REQUIRED_KEYS" in src_prep, \
            f"{mod.__name__}.prepare 应含产出不变量（返回前引用常量名自证产物键序）"
        assert "assert_produced_keys" in src_prep, \
            f"{mod.__name__}.prepare 应调用共享实现 contract.assert_produced_keys"
        assert "require_prepared_keys" not in src_prep, \
            f"{mod.__name__}.prepare 不得调用**输入**校验（输入校验属消费端职责）"


def test_key_sets_pairwise_distinct() -> None:
    """⑦ 三个必需键集合两两不同：固化「自校验之所以可判别」的前提，防形状趋同后静默失效。"""
    f = tuple(flow.PREPARED_REQUIRED_KEYS)
    i = tuple(impact_analyzer.PREPARED_REQUIRED_KEYS)
    d = tuple(drift.PREPARED_REQUIRED_KEYS)
    assert len({f, i, d}) == 3, f"三个必需键清单必须两两不同，实际 {f} / {i} / {d}"
    assert set(f) & set(d) == set(), "flow 与 drift 的键集合应为空交集"
    assert set(f) & set(i) == set(), "flow 与 impact 的键集合应为空交集"
    assert set(i) & set(d) == {"design"}, f"impact 与 drift 应只共享 design，实际 {set(i) & set(d)}"


def test_read_only_and_determinism() -> None:
    """⑧ 只读 + 确定性：校验通过后复用其复合摘要不变；同输入两次逐字节一致；夹具目录摘要不变。"""
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design, flow_doc, diffs = _fixture(td, design_text=_DESIGN, flow_text=_FLOW, changes=_CHANGES)
        before = _dir_digest(td)

        flow_prepared = flow.prepare(flow_doc, root)
        fd0 = _prepared_digest(flow_prepared)
        for _ in range(3):
            flow.analyze_prepared(flow_prepared, diffs["A"])
        assert _prepared_digest(flow_prepared) == fd0, "flow.analyze_prepared 不得就地修改 prepared"

        impact_prepared = impact_analyzer.prepare(root, design)
        id0 = _prepared_digest(impact_prepared)
        for _ in range(3):
            impact_analyzer.analyze_prepared(impact_prepared, impact_analyzer.read_diff(diffs["A"]))
        assert _prepared_digest(impact_prepared) == id0, "impact.analyze_prepared 不得就地修改 prepared"

        drift_prepared = drift.prepare(root, design)
        dd0 = _prepared_digest(drift_prepared)
        for _ in range(3):
            drift.analyze_prepared(drift_prepared)
        assert _prepared_digest(drift_prepared) == dd0, "drift.analyze_prepared 不得就地修改 prepared"

        # 确定性：同输入两次逐字节一致
        assert flow.to_json(flow.analyze(flow_doc, root, diffs["A"])) == flow.to_json(flow.analyze(flow_doc, root, diffs["A"]))
        assert drift.to_json(drift.analyze(root, design)) == drift.to_json(drift.analyze(root, design))
        assert impact_analyzer.to_json(impact_analyzer.analyze_files(diffs["A"], root, design)) == \
            impact_analyzer.to_json(impact_analyzer.analyze_files(diffs["A"], root, design))

        after = _dir_digest(td)
        assert before == after, "全过程不得写夹具中的任何一个字节"


def test_cli_and_exit_codes() -> None:
    """⑨ CLI 与退出码回归：正常路径逐字节一致、无 CRLF、退出码 0；错误路径仍 1；用法错误仍 2。"""
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design, flow_doc, diffs = _fixture(td, design_text=_DESIGN, flow_text=_FLOW, changes=_CHANGES)
        plan = _plan(td, ("A", "B"), diffs)

        # 正常路径：stdout 与库输出逐字节一致、退出码 0、无 \r\n
        lib_f = flow.analyze(flow_doc, root, diffs["A"])
        code, out, _err = _cli("flow", str(flow_doc), str(root), "--diff", str(diffs["A"]))
        assert code == 0, f"flow 正常路径应退出码 0，实际 {code}"
        assert out == flow.to_json(lib_f).encode("utf-8"), "flow stdout 应与库输出逐字节一致"
        assert b"\r\n" not in out, "stdout 不得被翻译成 CRLF"

        lib_d = drift.analyze(root, design)
        code, out, _err = _cli("drift", str(root), str(design))
        assert code == 0 and out == drift.to_json(lib_d).encode("utf-8"), "drift stdout 应与库输出逐字节一致"
        assert b"\r\n" not in out

        lib_i = impact_analyzer.analyze_files(diffs["A"], root, design)
        code, out, _err = _cli("impact", str(diffs["A"]), str(root), str(design))
        assert code == 0 and out == impact_analyzer.to_json(lib_i).encode("utf-8"), "impact stdout 应与库输出逐字节一致"
        assert b"\r\n" not in out

        lib_c = conflict.analyze_plan(plan, root, design, flow_doc)
        code, out, _err = _cli("conflict", str(plan), str(root), str(design), "--flow", str(flow_doc))
        assert code == 0 and out == conflict.to_json(lib_c).encode("utf-8"), "conflict stdout 应与库输出逐字节一致"
        assert b"\r\n" not in out

        lib_v = viewer.analyze(root, design)
        code, out, _err = _cli("view", str(root), str(design))
        assert code == 0 and out == viewer.render_html(lib_v).encode("utf-8"), "view stdout 应与库输出逐字节一致"
        assert b"\r\n" not in out

        # 错误路径仍是 1（含三套模块既有错误类型经 CLI 的映射）
        bad_design = td / "bad-design.md"
        bad_design.write_text("这一行根本不是设计文档\n", encoding="utf-8")
        bad_flow = td / "bad-flow.md"
        bad_flow.write_text("这不是流程文档\n", encoding="utf-8")
        assert _cli("drift", str(root), str(bad_design))[0] == 1, "坏设计文档经 drift 应退出码 1"
        assert _cli("view", str(root), str(bad_design))[0] == 1, "坏设计文档经 view 应退出码 1"
        assert _cli("impact", str(diffs["A"]), str(root), str(bad_design))[0] == 1, "坏设计文档经 impact 应退出码 1"
        assert _cli("flow", str(bad_flow), str(root))[0] == 1, "坏流程文档经 flow 应退出码 1"
        assert _cli("conflict", str(plan), str(root), str(design), "--flow", str(bad_flow))[0] == 1, \
            "坏流程文档经 conflict 应退出码 1（新增校验不得把退出码改成 2 或 0）"
        assert _cli("drift", str(td / "nope"), str(design))[0] == 1, "代码根非目录应退出码 1"

        # 用法错误仍是 2
        assert _cli("drift", str(root))[0] == 2, "drift 参数不足应退出码 2"
        assert _cli("flow", str(root))[0] == 2, "flow 参数不足应退出码 2"


def test_numbering_independence_and_full_regression() -> None:
    """⑩ 编号无关性 + 全域回归：本项只改错误消息与新增只读常量；全域自测全绿。

    M4 无自测；M18 即本模块，由本文件自身一次运行验收。此处逐模块跑**无需命令行参数**的
    M0–M17（`selftest_m2` / `selftest_m3` 需在命令行传入代码根，且其根即归档基线副本——
    按 M17 设计稿 §八 同一条先例，由里程碑级全域回归在自测外覆盖，本处不内嵌）。
    断言退出码 0 且末行为 `N/N passed`——即「合法输入对外产物未变」的全域证据。
    """
    if selftest_kit.in_regression():
        return
    mods = (
        "selftest",
        "selftest_m1",
        "selftest_m5",
        "selftest_m6",
        "selftest_m7",
        "selftest_m8",
        "selftest_m9",
        "selftest_m10",
        "selftest_m11",
        "selftest_m12",
        "selftest_m13",
        "selftest_m14",
        "selftest_m15",
        "selftest_m16",
        "selftest_m17",
    )
    for mod in mods:
        rc, out, err = _run_module(mod)
        tail = _last_line(out)
        assert rc == 0, f"{mod} 应退出码 0，实际 {rc}；stderr={err.strip()!r}"
        assert _all_passed(tail), f"{mod} 末行应为 'N/N passed'，实际 {tail!r}"


def main() -> int:
    tests = (
        test_cross_feed_diagnosis,
        test_legal_path_byte_identical,
        test_constant_matches_prepare,
        test_contract_regression,
        test_output_regression,
        test_structural_assertions,
        test_key_sets_pairwise_distinct,
        test_read_only_and_determinism,
        test_cli_and_exit_codes,
        test_numbering_independence_and_full_regression,
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
