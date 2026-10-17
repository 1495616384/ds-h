"""M20 自测：把「入口必需键校验 + 产出不变量『唯一实现』收口」的验收点写成可执行断言。

核心思路与夹具：**临时自建**最小代码根 + 设计文档 + 流程文档 + 两份改动 diff（与 M18 / M19 同一套夹具口径），
不依赖归档基线副本 / 网络；本文件与产品模块同样不含冻结链目录名字面量（由 M0 自测第三条校验全部
`xprod/**/*.py`，含本文件）。

覆盖（对应 `X产品化-M20设计稿-v1.md` §八 的 ①–⑧）：
    ① 合法路径逐字节不变：`analyze`（等价旧路径）与 `analyze_prepared(prepare(...))`（拆分路径）对三个
       模块的 `to_json` / `render_text` **逐字节一致**——共享实现只搬位置、不改行为，零对外差异；
    ② 两类消息**逐字**不变：三例交叉投喂的「采集体缺键」消息**逐字**等于收口前的措辞；
       产出不变量消息**逐字**含两组键序 + 「属生产者缺陷 / 非调用方误传」定性；
    ③ **唯一实现确实成立（核心证据）**：扫源码——带 `{producer}` 占位的**两条参数化模板片段**
       **全仓各只出现 1 处**（只在 `contract.py`）；**实现模块**（非 `selftest_*`）中消费端 / 生产端
       两条消息串只存在于 `contract.py`；
       三个 `analyze_prepared` 源码**含** `require_prepared_keys` 调用、三个 `prepare` 源码**含**
       `assert_produced_keys` 调用；
    ④ **产出不变量仍生效**：受控注入 + `try/finally` 还原（沿用 M19 ③）：三模块 `prepare` 在常量被注入后
       抛**本模块既有错误类型**、消息**逐字**等于生产端模板；还原后合法路径恢复键序一致；
    ⑤ 既有契约回归：`selftest_m15` / `m16` / `m17` 各 **10/10**（**零修订**）；`selftest_m18` / `m19`
       在**定点替换 ⑥ 后**各仍 **10/10**；
    ⑥ 结构断言稳定化（防复发）：三个 `analyze_prepared` 源码**不含**消息模板；三个 `prepare` 源码**不含**
       `require_prepared_keys`；`contract.py` **含**两份参数化模板各 1 处；
    ⑦ 只读 + 确定性：全过程夹具目录复合摘要不变；同输入两次输出逐字节一致；
       `PREPARED_REQUIRED_KEYS` 不被任何代码路径改写；
    ⑧ CLI 与退出码回归：`flow` / `drift` / `impact` / `conflict` / `view` 正常路径 stdout 与库输出
       **逐字节一致**、退出码 **0**、**无 `\\r\\n`**；坏文档 / 非目录退出码 **1**；用法错误退出码 **2**。

**③ 的扫描范围与设计稿的一处已知偏差（诚实标注）**：设计稿 §八 ③ 原写「扫 `xprod/**/*.py`（含自测脚本），
两串各只在 `contract.py` 出现 1 处」。但 `selftest_m18` ① / `selftest_m19` ④ 的**逐字消息断言**必须内嵌
消息文本作为**期望值**（且被 §七.3 明令不得修订），故**裸串**在自测脚本中出现是**断言输入**、非第二份实现。
本自测据此把「唯一」拆成两条**可判定**证据：**(a)** 参数化模板片段（带 `{producer}`）**全仓**唯一；
**(b)** **实现模块**（排除 `selftest_*.py`）中两串只存在于 `contract.py`。二者共同证明「第二份实现」不存在。

沿用 M0–M19 约定：不用 `subprocess` 管道，改临时文件重定向（本机沙箱禁建管道）。
"""

from __future__ import annotations

import inspect
import json
import re
import tempfile
from pathlib import Path

from . import conflict, contract, drift, flow, impact_analyzer, scanscope, selftest_kit, viewer
from .selftest_kit import cli as _cli, run_module as _run_module, last_line as _last_line, dir_digest as _dir_digest

PKG_DIR = Path(__file__).resolve().parent

# 唯一实现模板的**参数化片段**（以拼接构造，避免本文件源码自身被 ③(a) 计入命中）。
# 这两串是「实现」的最小可判据：`contract.py` 里的模板带 `{producer}` 占位，而自测脚本内嵌的是**具体**产出方。
_TMPL_FEED = "收到非 {" + "producer} 采集体"
_TMPL_PROD = "属生产者缺陷（{" + "producer}.prepare"

_DESIGN = (
    "# 夹具设计文档（M20 自测专用）\n"
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
    "# 流程夹具（M20 自测专用）\n"
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
        json.dumps({"plan_id": "M20 夹具", "changesets": changesets}, ensure_ascii=False),
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


def _feed_msg(who: str, missing: list) -> str:
    """消费端「采集体缺键」消息的**逐字**期望值（收口前三个模块的措辞）。

    形参名用 `who` 而非 `producer`：③(a) 会扫全仓源码找带 `{producer}` 占位的**参数化片段**，
    本函数若以 `producer` 为名，其源码本身就会命中该片段、破坏「唯一在 contract.py」的判据。
    """
    return f"analyze_prepared 收到非 {who} 采集体：缺少必需键 {missing}；应由 {who}.prepare 产出"


def _prod_msg(who: str, body_keys: tuple, req_keys: tuple) -> str:
    """生产端「产物键序分叉」消息的**逐字**期望值（收口前三模块的措辞）；形参命名理由同 `_feed_msg`。"""
    return (
        f"prepare 产物键序与 PREPARED_REQUIRED_KEYS 分叉：{body_keys} != {req_keys}；"
        f"属生产者缺陷（{who}.prepare 与契约常量不一致），非调用方误传"
    )


def _prepare_cases(root: Path, design: Path, flow_doc: Path) -> tuple:
    """三个（模块, 产出方名, 既有错误类型, 调 prepare 的零参 lambda）——注入 / 同源 / 消息断言共用同一口径。"""
    return (
        (flow, "flow", flow.FlowError, lambda: flow.prepare(flow_doc, root)),
        (impact_analyzer, "impact_analyzer", impact_analyzer.ImpactError,
         lambda: impact_analyzer.prepare(root, design)),
        (drift, "drift", drift.DriftError, lambda: drift.prepare(root, design)),
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
        assert impact_analyzer.to_json(legacy_i) == impact_analyzer.to_json(split_i), \
            "impact：两路径 to_json 应逐字节一致"
        assert impact_analyzer.render_text(legacy_i) == impact_analyzer.render_text(split_i), \
            "impact：两路径 render_text 应逐字节一致"


def test_messages_verbatim() -> None:
    """② 两类消息**逐字**不变：交叉投喂消息 == 收口前措辞；产出不变量消息 == 收口前措辞。"""
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design, flow_doc, diffs = _fixture(td)

        flow_prepared = flow.prepare(flow_doc, root)
        impact_prepared = impact_analyzer.prepare(root, design)
        drift_prepared = drift.prepare(root, design)
        diff_text = _diff("src/app/api.py", "old\n", "new\n")

        # (a) 消费端交叉投喂：三例消息**逐字**等于期望值
        consume = (
            (drift.analyze_prepared, (flow_prepared,), drift.PREPARED_REQUIRED_KEYS, "drift"),
            (impact_analyzer.analyze_prepared, (drift_prepared, diff_text),
             impact_analyzer.PREPARED_REQUIRED_KEYS, "impact_analyzer"),
            (flow.analyze_prepared, (impact_prepared, diffs["A"]), flow.PREPARED_REQUIRED_KEYS, "flow"),
        )
        for entry, args, keys, producer in consume:
            exc = _capture(entry, *args)
            assert exc is not None, f"{producer} 入口对误传应抛错"
            src = args[0]
            miss = [k for k in keys if k not in src]
            assert str(exc) == _feed_msg(producer, miss), f"{producer} 误传消息应逐字不变：{str(exc)}"

        # (b) 生产端产出不变量：注入后消息**逐字**等于期望值
        for mod, producer, err_type, call in _prepare_cases(root, design, flow_doc):
            original = mod.PREPARED_REQUIRED_KEYS
            for injected in (tuple(original[:-1]), tuple(reversed(original))):
                try:
                    mod.PREPARED_REQUIRED_KEYS = injected
                    exc = _capture(call)
                    assert isinstance(exc, err_type), \
                        f"{producer}.prepare 注入后应抛 {err_type.__name__}，实际 {type(exc).__name__}"
                    assert str(exc) == _prod_msg(producer, tuple(original), injected), \
                        f"{producer} 生产者缺陷消息应逐字不变：{str(exc)}"
                finally:
                    mod.PREPARED_REQUIRED_KEYS = original


def test_unique_implementation() -> None:
    """③ 唯一实现确实成立（**核心证据**）：参数化模板全仓唯一 + 实现模块串唯一 + 各入口只调用共享函数。"""
    # 扫描边界由 `scanscope` **唯一提供**（M23）：全集取 `all_modules()`（含自测文件，因 (a) 需全仓唯一性）
    py_files = scanscope.all_modules()
    assert py_files, "未扫到任何 xprod 源码文件（扫描路径异常）"

    # (a) 参数化模板片段（带 {producer}）**全仓**各只出现 1 处，且只可能在 contract.py
    for tmpl in (_TMPL_FEED, _TMPL_PROD):
        hits = []
        for p in py_files:
            src = p.read_text(encoding="utf-8")
            if tmpl in src:
                hits.append((p.name, src.count(tmpl)))
        assert hits == [("contract.py", 1)], f"参数化模板 {tmpl!r} 应全仓唯一（只在 contract.py 各 1 处），实际 {hits}"

    # (b) **实现模块**（由 `scanscope` 唯一划定）中两串只存在于 contract.py（自测脚本内嵌的是**期望值**，非第二份实现）
    impl = scanscope.impl_modules()
    assert any(p.name == "contract.py" for p in impl), "contract.py 应属实现模块集"
    for token in ("收到非", "属生产者缺陷"):
        for p in impl:
            cnt = p.read_text(encoding="utf-8").count(token)
            if p.name == "contract.py":
                assert cnt == 1, f"contract.py 中 {token!r} 应恰 1 处，实际 {cnt}"
            else:
                assert cnt == 0, f"实现模块 {p.name} 不应含 {token!r}（模板全仓唯一）"

    # (c) 三个 analyze_prepared 调用共享输入校验；三个 prepare 调用共享产出不变量
    for mod in (flow, impact_analyzer, drift):
        assert "require_prepared_keys" in inspect.getsource(mod.analyze_prepared), \
            f"{mod.__name__}.analyze_prepared 应调用 contract.require_prepared_keys"
        assert "assert_produced_keys" in inspect.getsource(mod.prepare), \
            f"{mod.__name__}.prepare 应调用 contract.assert_produced_keys"


def test_production_invariant_effective() -> None:
    """④ 产出不变量仍生效：受控注入 + `try/finally` 还原（沿用 M19 ③）。"""
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design, flow_doc, _diffs = _fixture(td)

        for mod, producer, err_type, call in _prepare_cases(root, design, flow_doc):
            original = mod.PREPARED_REQUIRED_KEYS
            assert list(call()) == list(original), f"{producer}：合法路径应满足契约（注入前基线）"
            for injected in (tuple(original[:-1]), tuple(reversed(original))):
                try:
                    mod.PREPARED_REQUIRED_KEYS = injected
                    exc = _capture(call)
                    assert isinstance(exc, err_type), \
                        f"{producer}.prepare 注入后应抛 {err_type.__name__}，实际 {type(exc).__name__}"
                    msg = str(exc)
                    assert str(original) in msg and str(injected) in msg, f"消息应含两组键序：{msg}"
                    assert "属生产者缺陷" in msg and "非调用方误传" in msg, f"消息应含生产者缺陷定性：{msg}"
                finally:
                    mod.PREPARED_REQUIRED_KEYS = original
            assert list(call()) == list(original), f"{producer}：还原后 prepare 键序应恢复"


def test_contract_regression() -> None:
    """⑤ 既有契约回归：M15 / M16 / M17 / M18 各 10/10（零修订）；M19 在定点替换 ⑥ 后仍 **8/8**。

    注：M19 自测为 8 条（M19 设计稿 §八 ①–⑧），非 10 条——设计稿 §八 ⑤ 曾误写「m18·m19 各 10/10」，
    本自测按**实测**口径断言（M19 = 8/8）。
    """
    if selftest_kit.in_regression():
        return
    for mod, expect in (
        ("selftest_m15", "10/10 passed"),
        ("selftest_m16", "10/10 passed"),
        ("selftest_m17", "10/10 passed"),
        ("selftest_m18", "10/10 passed"),
        ("selftest_m19", "8/8 passed"),
    ):
        rc, out, _err = _run_module(mod)
        tail = _last_line(out)
        assert rc == 0 and tail == expect, f"{mod} 应为 {expect}，实际 rc={rc} tail={tail!r}"


def test_structural_assertions() -> None:
    """⑥ 结构断言稳定化（防复发）：各入口只调用共享函数、不内联模板；contract.py 含两模板各 1 处。"""
    for mod in (flow, impact_analyzer, drift):
        src_ap = inspect.getsource(mod.analyze_prepared)
        assert "收到非" not in src_ap and "属生产者缺陷" not in src_ap, \
            f"{mod.__name__}.analyze_prepared 不得内联消息模板"
        src_prep = inspect.getsource(mod.prepare)
        assert "require_prepared_keys" not in src_prep, \
            f"{mod.__name__}.prepare 不得调用**输入**校验（输入校验属消费端职责）"
    contract_src = (PKG_DIR / "contract.py").read_text(encoding="utf-8")
    assert contract_src.count("收到非") == 1, "contract.py 应含消费端模板恰 1 处"
    assert contract_src.count("属生产者缺陷") == 1, "contract.py 应含生产端模板恰 1 处"


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
        assert code == 0 and out == impact_analyzer.to_json(lib_i).encode("utf-8"), \
            "impact stdout 应与库输出逐字节一致"
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
        test_messages_verbatim,
        test_unique_implementation,
        test_production_invariant_effective,
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
