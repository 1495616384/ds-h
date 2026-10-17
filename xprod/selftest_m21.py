"""M21 自测：把「确定性 JSON 序列化口径的唯一实现收口」的验收点写成可执行断言。

核心思路：**夹具临时自建**（最小代码根 + 设计文档 + 流程文档 + 改动 diff + 分工计划 + 核验程序桩），
使本自测不依赖任何归档基线副本、不依赖网络；`parse` / `dryrun` 两条子命令直接用仓库内既有样例
（`xprod/samples/`）。本文件与产品模块同样不含冻结链目录名字面量（由 M0 自测第三条校验全部
`xprod/**/*.py`，含本文件）。

覆盖（对应 `X产品化-M21设计稿-v1.md` §八 的 ①–⑧）：
    ① 合法路径逐字节不变：**九个**模块的 `to_json(doc)` 与 `textio.to_json(doc)`、以及与**冻结公式**
       `json.dumps(doc, ensure_ascii=False, indent=2) + "\\n"` 的**字面结果**对**多组** `doc`
       （空 / 非 ASCII / 嵌套 / 含列表）**逐字节相同**——收口只搬位置、不改行为；
    ② **唯一实现（结构证据）**：序列化公式片段在**实现模块**（排除 `selftest_*.py`）里**只在**
       `textio.py` 出现**恰 1 处**；九个 `to_json` 源码**含** `textio.to_json`、**不含** `json.dumps`；
    ③ **委派确实生效（核心证据）**：`try/finally` 把 `textio.to_json` 临时换成**哨兵桩** → 九个模块的
       `to_json` **全部返回哨兵**（证明它们真的走共享实现，而非各自本地实现）；`finally` 还原后输出恢复；
    ④ 既有契约回归：`selftest_m1/m5/m10/m11/m14/m15/m16/m17/m18/m19/m20` 各按**实测**条数全绿（**零修订**）；
    ⑤ CLI 与退出码回归：**九个** JSON 子命令（`parse` / `graph` / `impact` / `dryrun` / `guard` /
       `conflict` / `drift` / `sync` / `flow`）正常路径 stdout 与库输出**逐字节一致**、退出码 **0**、
       **无 `\\r\\n`**；错误路径 **1**；用法错误 **2**；
    ⑥ 只读 + 确定性：同输入两次输出逐字节一致；全过程夹具目录复合摘要不变；
    ⑦ **口径本体固化**：非 ASCII **不被转义**、末尾**恰一个**换行、缩进 **2**、键序＝**插入序**；
    ⑧ 全域回归 + 编号无关性：逐模块跑**无需命令行参数**的其余里程碑自测（`selftest` / `m6` / `m7` /
       `m8` / `m9` / `m12` / `m13`）断言全绿（`m2` / `m3` 需命令行传入代码根，由里程碑级全域回归覆盖）。

沿用 M0–M20 约定：不用 `subprocess` 管道，改临时文件重定向（本机沙箱禁建管道）。
"""

from __future__ import annotations

import inspect
import json
import re
import tempfile
from pathlib import Path

from . import (
    conflict,
    drift,
    dryrun,
    flow,
    graph_builder,
    guard,
    impact_analyzer,
    parser,
    scanscope,
    selftest_kit,
    sync,
    textio,
)
from .selftest_kit import cli as _cli, run_module as _run_module, last_line as _last_line, dir_digest as _dir_digest

PKG_DIR = Path(__file__).resolve().parent
SAMPLES = PKG_DIR / "samples"

# 九个曾各自复刻 `to_json` 的模块：名字与对象成对，使失败信息可读（诊断里出现模块名，而非 `<module …>`）
_NAMES = (
    "parser",
    "graph_builder",
    "flow",
    "impact_analyzer",
    "drift",
    "conflict",
    "dryrun",
    "guard",
    "sync",
)
_MODULES = (parser, graph_builder, flow, impact_analyzer, drift, conflict, dryrun, guard, sync)

# 冻结的序列化参数片段：只用于「结构唯一」扫描与「公式对照」，不代表任何实现
_MARK_CALL = "json." + "dumps("
_MARK_ARGS = "ensure_ascii=False, indent=2"

# 多组输入：空 / 非 ASCII / 嵌套 + 键序（"z" 先于 "a" 插入，用于 ⑦ 的键序断言）/ 含列表
_DOCS: tuple[dict, ...] = (
    {},
    {"中文": "值"},
    {"z": 1, "a": {"b": [1, 2, {"c": True}]}},
    {"列表": [1, "二", False], "空": None},
)

_ALL_PASSED = re.compile(r"^(?P<ok>\d+)/(?P<total>\d+) passed$")

# ④ 实测条数（改动前/后一致；M19 = 8 条、M20 = 8 条，非 10 条）
_REGRESSION = {
    "selftest_m1": "7/7",
    "selftest_m5": "13/13",
    "selftest_m10": "11/11",
    "selftest_m11": "10/10",
    "selftest_m14": "10/10",
    "selftest_m15": "10/10",
    "selftest_m16": "10/10",
    "selftest_m17": "10/10",
    "selftest_m18": "10/10",
    "selftest_m19": "8/8",
    "selftest_m20": "8/8",
}

# ⑧ 其余无需命令行参数的自测（与 ④ 互补，合起来覆盖 M0–M20）
_REGRESSION_EXTRA = {
    "selftest": "4/4",
    "selftest_m6": "13/13",
    "selftest_m7": "12/12",
    "selftest_m8": "12/12",
    "selftest_m9": "9/9",
    "selftest_m12": "12/12",
    "selftest_m13": "10/10",
}

_DESIGN = (
    "# 夹具设计文档（M21 自测专用）\n"
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
)

_FLOW = (
    "# 流程夹具（M21 自测专用）\n"
    "\n"
    "## FL-001 — 下单到发货\n"
    "\n"
    "- step:\n"
    "  - S1: 校验库存 @ src/app/api.py\n"
    "  - S2: 扣减库存 @ src/app/core.py\n"
    "  - S3: 发货通知 @ src/app/notify.py\n"
    "- edge:\n"
    "  - S1 -> S2\n"
    "  - S2 -> S3\n"
)

_CHANGES = (
    ("A", "src/app/api.py", "from app.core import X\nA = 1\n"),
    ("B", "src/app/core.py", "X = 2\n"),
)


def _formula(doc: dict) -> str:
    """冻结公式的**字面**写法——九模块收口前的那一行，此处作为对照真值。"""
    return json.dumps(doc, ensure_ascii=False, indent=2) + "\n"


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
        json.dumps({"plan_id": "M21 夹具", "changesets": changesets}, ensure_ascii=False),
        encoding="utf-8",
    )
    return plan


def _checker(td: Path) -> Path:
    """造一个核验程序桩：打印固定文本、退出码 0（供 `guard freeze` 的 CLI 回归用）。"""
    path = td / "checker.py"
    path.write_text("print('checker stub ok')\nraise SystemExit(0)\n", encoding="utf-8")
    return path


def _assert_regression(expected: dict[str, str]) -> None:
    """断言给定模块集合各按**实测**条数全绿（诊断含模块名与实际尾行，便于定位）。"""
    for mod, want in expected.items():
        rc, out, err = _run_module(mod)
        tail = _last_line(out)
        assert rc == 0 and tail == f"{want} passed", \
            f"{mod} 应为 {want} passed，实际 rc={rc} tail={tail!r} stderr={err[-200:]!r}"


def test_legal_path_byte_identical() -> None:
    """① 合法路径逐字节不变：九模块 `to_json` ≡ `textio.to_json` ≡ 冻结公式字面结果。"""
    for doc in _DOCS:
        expected = _formula(doc)
        assert textio.to_json(doc) == expected, "共享实现与冻结公式不一致"
        for name, mod in zip(_NAMES, _MODULES):
            assert mod.to_json(doc) == expected, f"{name}.to_json 与冻结公式不一致"


def test_unique_implementation() -> None:
    """② 唯一实现（结构证据）：公式片段只在 `textio.py`；九处只委派、不自持实现。"""
    hits: list[str] = []
    # 扫描边界由 `scanscope` **唯一提供**（M23）；自测文件是度量器，其内嵌对照公式不属产品实现
    for p in scanscope.impl_modules():
        src = p.read_text(encoding="utf-8")
        if _MARK_CALL in src and _MARK_ARGS in src:
            hits.append(p.name)
    assert hits == ["textio.py"], f"序列化公式在实现模块中应只出现于 textio.py，实际命中 {hits}"

    textio_src = (PKG_DIR / "textio.py").read_text(encoding="utf-8")
    assert textio_src.count(_MARK_CALL) == 1, "共享实现中公式应恰 1 处（不得另留第二份）"

    for name, mod in zip(_NAMES, _MODULES):
        src = inspect.getsource(mod.to_json)
        assert "textio.to_json" in src, f"{name}.to_json 未委派给共享实现"
        assert _MARK_CALL not in src, f"{name}.to_json 仍自持实现（应只委派）"


def test_delegation_effective() -> None:
    """③ 委派确实生效（**核心证据**）：受控注入哨兵桩 + `try/finally` 还原。"""
    sentinel = "«M21 哨兵»"
    original = textio.to_json
    try:
        textio.to_json = lambda doc: sentinel  # type: ignore[assignment]
        for name, mod in zip(_NAMES, _MODULES):
            got = mod.to_json({"x": 1})
            assert got == sentinel, f"{name}.to_json 未走共享实现（实际未拿到哨兵）"
    finally:
        textio.to_json = original  # type: ignore[assignment]

    for doc in _DOCS:
        expected = _formula(doc)
        assert textio.to_json(doc) == expected, "还原后共享实现应恢复逐字节正确"
        for name, mod in zip(_NAMES, _MODULES):
            assert mod.to_json(doc) == expected, f"{name}.to_json 还原后应恢复逐字节正确"


def test_contract_regression() -> None:
    """④ 既有契约回归：`to_json` 的既有消费方全部按实测条数全绿（**零修订**）。"""
    if selftest_kit.in_regression():
        return
    _assert_regression(_REGRESSION)


def test_cli_and_exit_codes() -> None:
    """⑤ CLI 与退出码回归：九个 JSON 子命令逐字节一致、无 CRLF、退出码 0；错误 1；用法 2。"""
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design, flow_doc, diffs = _fixture(td)
        plan = _plan(td, ("A", "B"), diffs)
        checker = _checker(td)

        # parse：直接用仓库既有样例
        sample_design = SAMPLES / "design-sample.md"
        code, out, _err = _cli("parse", str(sample_design))
        assert code == 0 and out == parser.to_json(parser.parse_file(sample_design)).encode("utf-8"), \
            "parse stdout 应与库输出逐字节一致"
        assert b"\r\n" not in out, "stdout 不得被翻译成 CRLF"

        # graph
        code, out, _err = _cli("graph", str(root))
        assert code == 0 and out == graph_builder.to_json(graph_builder.build_graph(root)).encode("utf-8"), \
            "graph stdout 应与库输出逐字节一致"
        assert b"\r\n" not in out

        # impact
        code, out, _err = _cli("impact", str(diffs["A"]), str(root), str(design))
        lib_i = impact_analyzer.analyze_files(diffs["A"], root, design)
        assert code == 0 and out == impact_analyzer.to_json(lib_i).encode("utf-8"), \
            "impact stdout 应与库输出逐字节一致"
        assert b"\r\n" not in out

        # dryrun：直接用仓库既有样例
        sample_scenarios = SAMPLES / "dryrun-scenarios.json"
        code, out, _err = _cli("dryrun", str(sample_scenarios))
        assert code == 0 and out == dryrun.to_json(dryrun.run_scenarios(sample_scenarios)).encode("utf-8"), \
            "dryrun stdout 应与库输出逐字节一致"
        assert b"\r\n" not in out

        # guard（freeze 模式，核验程序为桩）
        code, out, _err = _cli("guard", "freeze", "--checker", str(checker), "--root", str(root))
        lib_g = guard.run_freeze_check(checker, root).to_dict()
        assert code == 0 and out == guard.to_json(lib_g).encode("utf-8"), \
            "guard stdout 应与库输出逐字节一致"
        assert b"\r\n" not in out

        # conflict
        code, out, _err = _cli("conflict", str(plan), str(root), str(design), "--flow", str(flow_doc))
        lib_c = conflict.analyze_plan(plan, root, design, flow_doc)
        assert code == 0 and out == conflict.to_json(lib_c).encode("utf-8"), \
            "conflict stdout 应与库输出逐字节一致"
        assert b"\r\n" not in out

        # drift
        code, out, _err = _cli("drift", str(root), str(design))
        assert code == 0 and out == drift.to_json(drift.analyze(root, design)).encode("utf-8"), \
            "drift stdout 应与库输出逐字节一致"
        assert b"\r\n" not in out

        # sync
        code, out, _err = _cli("sync", str(root), str(design))
        assert code == 0 and out == sync.to_json(sync.snapshot(root, design)).encode("utf-8"), \
            "sync stdout 应与库输出逐字节一致"
        assert b"\r\n" not in out

        # flow
        code, out, _err = _cli("flow", str(flow_doc), str(root), "--diff", str(diffs["A"]))
        lib_f = flow.analyze(flow_doc, root, diffs["A"])
        assert code == 0 and out == flow.to_json(lib_f).encode("utf-8"), \
            "flow stdout 应与库输出逐字节一致"
        assert b"\r\n" not in out

        # 错误路径仍是 1
        bad_design = td / "bad-design.md"
        bad_design.write_text("这一行根本不是设计文档\n", encoding="utf-8")
        assert _cli("drift", str(root), str(bad_design))[0] == 1, "坏设计文档经 drift 应退出码 1"
        assert _cli("parse", str(td / "nope.md"))[0] == 1, "不存在的设计文档经 parse 应退出码 1"
        assert _cli("drift", str(td / "nope"), str(design))[0] == 1, "代码根非目录应退出码 1"

        # 用法错误仍是 2
        assert _cli("drift", str(root))[0] == 2, "drift 参数不足应退出码 2"
        assert _cli("guard", "freeze")[0] == 2, "guard freeze 缺 --checker 应退出码 2"


def test_read_only_and_determinism() -> None:
    """⑥ 只读 + 确定性：夹具目录复合摘要不变；同输入两次逐字节一致。"""
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design, flow_doc, diffs = _fixture(td)
        before = _dir_digest(td)

        for name, mod, doc in (
            ("flow", flow, flow.analyze(flow_doc, root, diffs["A"])),
            ("drift", drift, drift.analyze(root, design)),
            ("impact", impact_analyzer, impact_analyzer.analyze_files(diffs["A"], root, design)),
            ("graph", graph_builder, graph_builder.build_graph(root)),
            ("sync", sync, sync.snapshot(root, design)),
        ):
            assert mod.to_json(doc) == mod.to_json(doc), f"{name}：同输入两次应逐字节一致"

        assert _dir_digest(td) == before, "全过程不得写夹具中的任何一个字节"


def test_canonical_form() -> None:
    """⑦ 口径本体固化：非 ASCII 不转义、末尾恰一换行、缩进 2、键序＝插入序。"""
    out = textio.to_json({"z": 1, "a": {"b": 2}, "中文": "值"})
    assert out == _formula({"z": 1, "a": {"b": 2}, "中文": "值"}), "应与冻结公式一致"
    assert out.startswith('{\n  "z": 1,'), f"键序应为插入序（不得重排）、缩进应为 2：{out[:20]!r}"
    assert out.endswith("}\n") and not out.endswith("\n\n"), "末尾应恰一个换行"
    assert "中文" in out and "\\u" not in out, "非 ASCII 不得被转义"


def test_full_regression_extra() -> None:
    """⑧ 全域回归（其余无需参数的自测）：按实测条数全绿。"""
    if selftest_kit.in_regression():
        return
    _assert_regression(_REGRESSION_EXTRA)


def main() -> int:
    tests = (
        test_legal_path_byte_identical,
        test_unique_implementation,
        test_delegation_effective,
        test_contract_regression,
        test_cli_and_exit_codes,
        test_read_only_and_determinism,
        test_canonical_form,
        test_full_regression_extra,
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
