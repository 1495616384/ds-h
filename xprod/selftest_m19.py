"""M19 自测：把「契约常量与生产者产物『同源』的收口（产出不变量）」的验收点写成可执行断言。

核心思路与夹具：**临时自建**最小代码根 + 设计文档 + 流程文档 + 两份改动 diff（与 M18 自测同一套夹具口径），
不依赖归档基线副本 / 网络；本文件与产品模块同样不含冻结链目录名字面量（由 M0 自测第三条校验全部
`xprod/**/*.py`，含本文件）。

覆盖（对应 `X产品化-M19设计稿-v1.md` §八 的 ①–⑧）：
    ① 合法路径逐字节不变：`analyze`（等价旧路径）与 `analyze_prepared(prepare(...))`（拆分路径）对三个
       模块的 `to_json` / `render_text` **逐字节一致**——产出不变量对合法输入恒真，零对外差异；
    ② 常量与实现同源：`list(prepare(...)) == list(PREPARED_REQUIRED_KEYS)` 对**三个**模块成立（沿用 M18 ③）；
    ③ **产出不变量确实生效（核心证据）**：**受控注入 + `try/finally` 还原**——临时把某模块
       `PREPARED_REQUIRED_KEYS` 改成**截断**或**反序**的元组，调该模块 `prepare` → 抛**本模块既有错误类型**，
       消息含**产物实际键序**、**契约键序**、以及「属生产者缺陷 / 非调用方误传」定性；`finally` 还原后合法路径
       恢复键序一致——证「分叉在**定义点**、以**指向生产者**的诊断失败」；
    ④ 交叉投喂诊断**不回归**：三例**真实** `prepare` 产物互投仍抛**不同**的「采集体缺键」诊断，且消息**不含**
       「属生产者缺陷」——证明**生产者缺陷 ≠ 调用方误传**，两类诊断未被混为一谈；
    ⑤ 既有契约回归：`selftest_m15` / `selftest_m16` / `selftest_m17` 各 **10/10** 仍通过（**零修订**）；
       `selftest_m18` 在**定点精化 ⑥ 后**仍 **10/10**；
    ⑥ 结构断言精化（防复发）：`inspect.getsource` 三个 `analyze_prepared` **仍含**输入缺失键校验形态；
       三个 `prepare` 源码**含**常量名（产出不变量）但**不含** `missing = …` 形态的**输入**校验；
    ⑦ 只读 + 确定性：全过程夹具目录复合摘要不变；同输入两次输出逐字节一致；
       `PREPARED_REQUIRED_KEYS` 自身**不被**任何代码路径改写；
    ⑧ CLI 与退出码回归：`flow` / `drift` / `impact` / `conflict` / `view` 正常路径 stdout 与库输出
       **逐字节一致**、退出码 **0**、**无 `\\r\\n`**；坏文档 / 非目录退出码 **1**；用法错误退出码 **2**。

沿用 M0–M18 约定：不用 `subprocess` 管道，改临时文件重定向（本机沙箱禁建管道）。
"""

from __future__ import annotations

import inspect
import json
import re
import tempfile
from pathlib import Path

from . import conflict, drift, flow, impact_analyzer, viewer
from .selftest_kit import cli as _cli, run_module as _run_module, last_line as _last_line, dir_digest as _dir_digest

PKG_DIR = Path(__file__).resolve().parent

_DESIGN = (
    "# 夹具设计文档（M19 自测专用）\n"
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
    "# 流程夹具（M19 自测专用）\n"
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
    """建最小代码根（层层 `__init__.py`，使依赖图有模块名可解析、有节点可用）。"""
    root = td / "root"
    (root / "src" / "app").mkdir(parents=True)
    (root / "docs").mkdir(parents=True)
    (root / "src" / "app" / "__init__.py").write_text("", encoding="utf-8")
    (root / "src" / "app" / "api.py").write_text("from app.core import X\nA = 0\n", encoding="utf-8")
    (root / "src" / "app" / "core.py").write_text("X = 1\n", encoding="utf-8")
    (root / "src" / "app" / "notify.py").write_text("N = 1\n", encoding="utf-8")
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


def _plan(td: Path, cids: tuple[str, ...], diffs: dict[str, Path]) -> Path:
    """造一份分工计划（`diff` 用文件名，相对计划文件所在目录解析）；id 升序以满足 `load_plan` 规范化。"""
    changesets = [{"id": cid, "diff": diffs[cid].name} for cid in sorted(cids)]
    plan = td / "plan.json"
    plan.write_text(
        json.dumps({"plan_id": "M19 夹具", "changesets": changesets}, ensure_ascii=False),
        encoding="utf-8",
    )
    return plan


def _capture(fn, *args: object, **kwargs: object) -> BaseException | None:
    """调用 `fn` 并捕获任何异常，返回异常实例；未抛异常返回 None（供按类型断言用）。"""
    try:
        fn(*args, **kwargs)
    except BaseException as exc:  # 自测要按**类型**断言，故此处广捕
        return exc
    return None


def _all_passed(tail: str) -> bool:
    m = _ALL_PASSED.match(tail)
    return bool(m) and m.group("ok") == m.group("total")


def _prepare_cases(root: Path, design: Path, flow_doc: Path) -> tuple:
    """三个（模块, 既有错误类型, 调用 prepare 的零参 lambda）三元组——三处断言共用同一份口径。"""
    return (
        (flow, flow.FlowError, lambda: flow.prepare(flow_doc, root)),
        (impact_analyzer, impact_analyzer.ImpactError, lambda: impact_analyzer.prepare(root, design)),
        (drift, drift.DriftError, lambda: drift.prepare(root, design)),
    )


def test_legal_path_byte_identical() -> None:
    """① 合法路径逐字节不变：等价旧路径（`analyze`）与新拆分路径（`analyze_prepared(prepare(...))`）一致。"""
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design, flow_doc, diffs = _fixture(td)

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
    """② 常量与实现同源：`prepare` 的键序逐字等于 `PREPARED_REQUIRED_KEYS`。"""
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design, flow_doc, _diffs = _fixture(td)

        for mod, _err, call in _prepare_cases(root, design, flow_doc):
            assert list(call()) == list(mod.PREPARED_REQUIRED_KEYS), \
                f"{mod.__name__} 常量与实现不同源：{list(mod.PREPARED_REQUIRED_KEYS)} vs {list(call())}"


def test_production_invariant_effective() -> None:
    """③ 产出不变量确实生效（**核心证据**）：受控注入 + `try/finally` 还原。

    对每个模块，临时把 `PREPARED_REQUIRED_KEYS` 改成**截断**（少一个键）/ **反序** 的元组，调 `prepare`：
    必须抛**本模块既有错误类型**，且消息含**产物实际键序**、**契约键序**、「属生产者缺陷 / 非调用方误传」定性；
    `finally` 内**必须**还原常量，并断言还原后合法路径键序恢复一致——证明分叉在**定义点**被拦下、诊断**指向生产者**。
    """
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design, flow_doc, _diffs = _fixture(td)

        for mod, err_type, call in _prepare_cases(root, design, flow_doc):
            original = mod.PREPARED_REQUIRED_KEYS
            assert list(call()) == list(original), f"{mod.__name__}：合法路径应满足契约（注入前基线）"
            for injected in (tuple(original[:-1]), tuple(reversed(original))):
                try:
                    mod.PREPARED_REQUIRED_KEYS = injected
                    exc = _capture(call)
                    assert isinstance(exc, err_type), \
                        f"{mod.__name__}.prepare 在常量被注入后应抛 {err_type.__name__}，实际 {type(exc).__name__}"
                    msg = str(exc)
                    assert str(original) in msg, f"消息应含**产物实际键序** {original}：{msg}"
                    assert str(injected) in msg, f"消息应含**契约键序** {injected}：{msg}"
                    assert "属生产者缺陷" in msg, f"消息应含「属生产者缺陷」定性：{msg}"
                    assert "非调用方误传" in msg, f"消息应含「非调用方误传」定性：{msg}"
                finally:
                    mod.PREPARED_REQUIRED_KEYS = original
            # 还原后合法路径恢复逐字节一致（键序 + 取值）
            assert list(call()) == list(original), f"{mod.__name__}：还原后 prepare 键序应恢复"


def test_cross_feed_diagnosis_not_regressed() -> None:
    """④ 交叉投喂诊断**不回归**：三例真实体互投仍抛「采集体缺键」诊断，且**不含**生产者缺陷定性。

    这条证明本项**没有**把两类诊断混为一谈：**调用方误传**（M18 消费端诊断）≠ **生产者缺陷**（M19 产出不变量）。
    """
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design, flow_doc, diffs = _fixture(td)

        flow_prepared = flow.prepare(flow_doc, root)
        impact_prepared = impact_analyzer.prepare(root, design)
        drift_prepared = drift.prepare(root, design)
        diff_text = _diff("src/app/api.py", "old\n", "new\n")

        cases = (
            (drift.analyze_prepared, (flow_prepared,), drift.DriftError, "drift", drift.PREPARED_REQUIRED_KEYS),
            (impact_analyzer.analyze_prepared, (drift_prepared, diff_text), impact_analyzer.ImpactError,
             "impact_analyzer", impact_analyzer.PREPARED_REQUIRED_KEYS),
            (flow.analyze_prepared, (impact_prepared, diffs["A"]), flow.FlowError, "flow", flow.PREPARED_REQUIRED_KEYS),
        )
        for entry, args, err_type, name, keys in cases:
            exc = _capture(entry, *args)
            assert isinstance(exc, err_type), f"{name} 入口应抛 {err_type.__name__}，实际 {type(exc).__name__}"
            msg = str(exc)
            assert "缺少必需键" in msg, f"应报「采集体缺键」诊断：{msg}"
            assert f"应由 {name}.prepare 产出" in msg, f"消息应含期望产出方：{msg}"
            assert "属生产者缺陷" not in msg, f"误传诊断**不得**混入生产者缺陷定性：{msg}"


def test_contract_regression() -> None:
    """⑤ 既有契约回归：M15 / M16 / M17 各 10/10；M18 在定点精化 ⑥ 后仍 10/10。"""
    for mod in ("selftest_m15", "selftest_m16", "selftest_m17", "selftest_m18"):
        rc, out, _err = _run_module(mod)
        tail = _last_line(out)
        assert rc == 0 and tail == "10/10 passed", f"{mod} 应为 10/10 通过，实际 rc={rc} tail={tail!r}"


def test_structural_assertions() -> None:
    """⑥ 结构断言精化（防复发）：`analyze_prepared` **调用**共享输入校验、不内联模板；`prepare` **调用**产出不变量、不调输入校验。

    M20 定点替换（原为匹配文本 `missing = [k for k in PREPARED_REQUIRED_KEYS`）——改为**守结构**（同 M18 ⑥）：
    契约校验已收口为**唯一实现** `contract`，故断言锚在**是否调用共享函数**、模板是否**只存在于** `contract.py`。
    """
    for mod in (flow, impact_analyzer, drift):
        src_ap = inspect.getsource(mod.analyze_prepared)
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


def test_read_only_and_determinism() -> None:
    """⑦ 只读 + 确定性：夹具目录复合摘要不变；同输入两次逐字节一致；常量不被任何路径改写。"""
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design, flow_doc, diffs = _fixture(td)
        before = _dir_digest(td)
        const_before = (
            tuple(flow.PREPARED_REQUIRED_KEYS),
            tuple(impact_analyzer.PREPARED_REQUIRED_KEYS),
            tuple(drift.PREPARED_REQUIRED_KEYS),
        )

        # 正常 + 复用路径跑多遍（含 carried prepared 的 analyze_prepared）
        flow_prepared = flow.prepare(flow_doc, root)
        impact_prepared = impact_analyzer.prepare(root, design)
        drift_prepared = drift.prepare(root, design)
        for _ in range(3):
            flow.analyze_prepared(flow_prepared, diffs["A"])
            impact_analyzer.analyze_prepared(impact_prepared, impact_analyzer.read_diff(diffs["A"]))
            drift.analyze_prepared(drift_prepared)

        assert flow.to_json(flow.analyze(flow_doc, root, diffs["A"])) == \
            flow.to_json(flow.analyze(flow_doc, root, diffs["A"])), "flow：同输入两次应逐字节一致"
        assert drift.to_json(drift.analyze(root, design)) == \
            drift.to_json(drift.analyze(root, design)), "drift：同输入两次应逐字节一致"
        assert impact_analyzer.to_json(impact_analyzer.analyze_files(diffs["A"], root, design)) == \
            impact_analyzer.to_json(impact_analyzer.analyze_files(diffs["A"], root, design)), \
            "impact：同输入两次应逐字节一致"

        const_after = (
            tuple(flow.PREPARED_REQUIRED_KEYS),
            tuple(impact_analyzer.PREPARED_REQUIRED_KEYS),
            tuple(drift.PREPARED_REQUIRED_KEYS),
        )
        assert const_before == const_after, "PREPARED_REQUIRED_KEYS 不得被任何代码路径改写"
        assert _dir_digest(td) == before, "全过程不得写夹具中的任何一个字节"


def test_cli_and_exit_codes() -> None:
    """⑧ CLI 与退出码回归：正常路径逐字节一致、无 CRLF、退出码 0；错误路径仍 1；用法错误仍 2。"""
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design, flow_doc, diffs = _fixture(td)
        plan = _plan(td, ("A", "B"), diffs)

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

        # 错误路径仍是 1
        bad_design = td / "bad-design.md"
        bad_design.write_text("这一行根本不是设计文档\n", encoding="utf-8")
        bad_flow = td / "bad-flow.md"
        bad_flow.write_text("这不是流程文档\n", encoding="utf-8")
        assert _cli("drift", str(root), str(bad_design))[0] == 1, "坏设计文档经 drift 应退出码 1"
        assert _cli("view", str(root), str(bad_design))[0] == 1, "坏设计文档经 view 应退出码 1"
        assert _cli("impact", str(diffs["A"]), str(root), str(bad_design))[0] == 1, "坏设计文档经 impact 应退出码 1"
        assert _cli("flow", str(bad_flow), str(root))[0] == 1, "坏流程文档经 flow 应退出码 1"
        assert _cli("conflict", str(plan), str(root), str(design), "--flow", str(bad_flow))[0] == 1, \
            "坏流程文档经 conflict 应退出码 1"
        assert _cli("drift", str(td / "nope"), str(design))[0] == 1, "代码根非目录应退出码 1"

        # 用法错误仍是 2
        assert _cli("drift", str(root))[0] == 2, "drift 参数不足应退出码 2"
        assert _cli("flow", str(root))[0] == 2, "flow 参数不足应退出码 2"


def main() -> int:
    tests = (
        test_legal_path_byte_identical,
        test_constant_matches_prepare,
        test_production_invariant_effective,
        test_cross_feed_diagnosis_not_regressed,
        test_contract_regression,
        test_structural_assertions,
        test_read_only_and_determinism,
        test_cli_and_exit_codes,
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
