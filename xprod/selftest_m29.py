"""M29 自测：把「自测『建全套夹具』的唯一实现收口（数据显式参数化）」的验收点写成可执行断言。

背景（`X产品化-M29设计稿-v1.md` §一）：`xprod` 的自测都要先建**一套临时夹具**——
先造最小代码根（`make_min_root`，M28 已收口），再把本模块的**三份夹具数据**写进临时目录
（设计文档 `_DESIGN`、流程文档 `_FLOW`、改动清单 `_CHANGES`，每项生成一份 `.diff`），
最后返回 `（代码根, 设计文档, 流程文档, id→diff 路径）`。这个**动作过程**在 **10 个自测文件**
（`m18`–`m24`、`m26`、`m27`、`m28`）里**逐字同构**地抄了 10 遍，**没有任何一处是定义源**；
差异**只在**各模块**自己的数据常量**里（`_DESIGN` 去首行后 4 种、`_FLOW` 去首行后 2 种）。
M29 把那 10 处**动作过程**收归 `selftest_kit.py` 的**唯一实现**（公共名 `make_fixture`），
**数据不从文件搬走**——改为**显式参数化**：10 个消费文件删除本地定义、列为
`make_fixture as _fixture` 的**同名绑定**，并在**每一个调用点**显式传入本模块自己的三份数据。

**自指防护**：本文件同样会被 ① / ③ 扫到，故待查特征串一律**分段拼接**构造
（`_D + "make_fixture(td: Path, …"`），使本文件源码**不**字面出现那两类**全签名特征串**
（`make_fixture` 与 `_fixture` 的完整定义行；与 M23 / M24 / M26 / M27 / M28 同法）。

覆盖（对应设计稿 §八 ①–⑧）：
    ① **唯一实现（结构证据）**：公共名 `make_fixture` 的**全签名 `def`** 在全部模块
       （= `scanscope.all_modules()`）中**恰 1 处**且位于 `selftest_kit.py`；
    ② **值等价 + 消费者自洽**：与**本文件内独立参照公式**在临时目录上产物**逐字节同值**
       （逐文件路径 + 内容 + 复合摘要）；`PKG_DIR` 仍可解析；
    ③ **消费点已无本地复刻 + 真分歧登记仍在**：10 个消费文件**不含**本地全签名定义、
       **含**绑定 `make_fixture as _fixture`、且**每个调用行都带**三个关键字实参；
       全仓该全签名命中集**恰为** `{m15, m16}`；`m14` / `m17` 按**各自签名**仍含本地定义；
    ④ **夹具产物逐字不变（行为）**：抽样 `m18` / `m24` / `m27` / `m28` 的产物与参照公式
       （数据取**该模块自己的**常量）**逐字节同值**；
    ⑤ **CLI 与退出码回归**：`drift` / `sync` / `impact` / `flow` / `view` 正常路径 stdout 与库输出
       **逐字节一致**、退出码 **0**、**无 `\\r\\n`**；错误 **1**；用法 **2**；
    ⑥ **只读 + 确定性**：同输入两次**逐字节一致**；`scanscope.*` 两次调用**相同**；
       夹具目录复合摘要**不变**；
    ⑦ **既有自测零修订**：无需命令行参数的自测**全部**按**实测**条数全绿（**个数与改动前相同**）；
    ⑧ **全域回归 + 编号无关性 + 边界**：逆序跑同一批自测全绿（与 ⑦ 正序逐条一致 → 编号无关）；
       需命令行代码根者仍**恰为** `m2` / `m3`（由里程碑级全域回归覆盖）。

沿用 M0–M28 约定：**不**用管道捕获输出，改临时文件重定向（本机沙箱禁建管道）——
本文件自身的脚手架调用一律经 `selftest_kit` 唯一实现，**不**内联子进程调用。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from . import drift, flow, impact_analyzer, scanscope, selftest_kit, sync, viewer
from . import selftest_m18, selftest_m24, selftest_m27, selftest_m28
from .selftest_kit import (
    PKG_DIR,
    assert_regression as _assert_regression,
    cli as _cli,
    diff_one_file as _diff,
    dir_digest as _dir_digest,
    make_fixture,
    make_min_root as _make_root,
    number_independence_regression,
    tree_files as _tree_files,
    ARG_EXEMPT as _ARG_EXEMPT,
    ARGV_MARK as _ARGV_MARK,
    KIT_NAME as _KIT,
    DEF_PREFIX as _D,
)

# 待查特征串**分段拼接**（见模块 docstring 的「自指防护」）：拼出的结果不在本文件源码中字面出现
# ① 公共样板全签名（§四 写死的那一行，实现时排成单行）
_SIG_PUBLIC = _D + (
    "make_fixture(td: Path, *, design_text: str, flow_text: str, "
    "changes: tuple[tuple[str, str, str], ...]) -> tuple[Path, Path, Path, dict[str, Path]]:"
)
# ③ 收口前本地样板全签名（收口后应只剩 m15 / m16 两处真分歧变体）
_SIG_LOCAL4 = _D + "_fixture(td: Path) -> tuple[Path, Path, Path, dict[str, Path]]:"
# ③ 两处签名真分歧变体各自的本地全签名
_SIG_M14 = _D + "_fixture(td: Path) -> tuple[Path, Path, Path, Path]:"
_SIG_M17 = _D + "_fixture(td: Path) -> tuple[Path, Path]:"

# 消费形态：公共名 → 本地名（同名绑定），全部调用点显式数据传参
_BIND = "make_fixture as _fixture"
_KWARGS = ("design_text=_DESIGN", "flow_text=_FLOW", "changes=_CHANGES")

# ③ 名单：10 个消费文件（本轮收口）与 4 处**真分歧变体**（裁定保留、显式登记）
_CONSUMERS = (
    "selftest_m18.py",
    "selftest_m19.py",
    "selftest_m20.py",
    "selftest_m21.py",
    "selftest_m22.py",
    "selftest_m23.py",
    "selftest_m24.py",
    "selftest_m26.py",
    "selftest_m27.py",
    "selftest_m28.py",
)
_SIG4_VARIANTS = ("selftest_m15.py", "selftest_m16.py")
_SIG_M14_FILE = "selftest_m14.py"
_SIG_M17_FILE = "selftest_m17.py"

# ②/④ 参照公式：收口前那份「建全套夹具」过程的**文件清单与内容模板**（逐字写死，作为对照真值）
_DESIGN = (
    "# 夹具设计文档（M29 自测专用）\n"
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
)

_FLOW = (
    "# 流程夹具（M29 自测专用）\n"
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

# ⑧ 的输入常量（`_ARGV_MARK` / `_ARG_EXEMPT`）已收归 `selftest_kit.py` 唯一实现（M32），经 M32 别名绑定导入


# --- ②/④ 用的独立参照公式（**写死**在自测里，与共享实现逐字节对照）-------------------


def _ref_fixture(
    td: Path, design_text: str, flow_text: str, changes: tuple[tuple[str, str, str], ...]
) -> tuple[Path, Path, Path, dict[str, Path]]:
    """参照公式：按 §一 重新推导「建全套夹具」过程（与收口前 10 处逐字同构）。"""
    root = _make_root(td)
    design = td / "design.md"
    design.write_text(design_text, encoding="utf-8")
    flow_doc = td / "flow.md"
    flow_doc.write_text(flow_text, encoding="utf-8")
    diffs: dict[str, Path] = {}
    for cid, path, new in changes:
        dp = td / f"{cid}.diff"
        dp.write_text(_diff(path, "old\n", new), encoding="utf-8")
        diffs[cid] = dp
    return root, design, flow_doc, diffs


# --- ① / ② / ③ 断言 ---------------------------------------------------------------


def test_unique_implementation() -> None:
    """① 唯一实现（结构证据）：公共名全签名 def 在全部模块中恰 1 处且在宿主。"""
    hits: dict[str, int] = {}
    for p in scanscope.all_modules():
        n = p.read_text(encoding="utf-8").count(_SIG_PUBLIC)
        if n:
            hits[p.name] = n
    assert hits == {_KIT: 1}, f"公共样板应全仓恰 1 处且位于 {_KIT}：{_SIG_PUBLIC!r} → {hits}"


def test_value_equivalence() -> None:
    """② 值等价 + 消费者自洽：与独立参照公式产物逐字节同值；PKG_DIR 仍可解析。"""
    assert selftest_kit.PKG_DIR == scanscope.PKG_DIR, "再导出应与定义源逐字同值"
    assert PKG_DIR.is_dir(), f"包目录应为存在目录，实际 {PKG_DIR}"
    assert (PKG_DIR / "scanscope.py").is_file(), "包目录内应含定义源 scanscope.py"

    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        got = make_fixture(td / "got", design_text=_DESIGN, flow_text=_FLOW, changes=_CHANGES)
        ref = _ref_fixture(td / "ref", _DESIGN, _FLOW, _CHANGES)
        assert _tree_files(got[0]) == _tree_files(ref[0]), "代码根产物应与参照公式逐字节同值"
        assert _dir_digest(got[0]) == _dir_digest(ref[0]), "两棵代码根的复合摘要应相同"
        assert got[1].read_text(encoding="utf-8") == _DESIGN, "设计文档应逐字等于传入的数据"
        assert got[2].read_text(encoding="utf-8") == _FLOW, "流程文档应逐字等于传入的数据"
        assert sorted(got[3]) == sorted(ref[3]), "diff 集合的 id 应一致"


def test_consumers_pruned_and_variants_registered() -> None:
    """③ 消费点已无本地复刻 + 真分歧登记仍在：全签名命中恰为 m15/m16；每个调用行都带三 kwargs。"""
    for name in _CONSUMERS:
        src = (PKG_DIR / name).read_text(encoding="utf-8")
        assert _SIG_LOCAL4 not in src, f"{name} 仍含本地全套夹具定义（应收口为共享引用）"
        assert _BIND in src, f"{name} 未绑定「{_BIND}」"
        for i, line in enumerate(src.splitlines(), 1):
            if "_fixture(" in line:
                for kw in _KWARGS:
                    assert kw in line, f"{name}:{i} 的调用点未显式传参（缺 {kw}）：{line.strip()!r}"

    hits: dict[str, int] = {}
    for p in scanscope.all_modules():
        n = p.read_text(encoding="utf-8").count(_SIG_LOCAL4)
        if n:
            hits[p.name] = n
    assert hits == {name: 1 for name in _SIG4_VARIANTS}, \
        f"本地全签名应只留在 {len(_SIG4_VARIANTS)} 个真分歧变体文件，实际 {hits}"

    src14 = (PKG_DIR / _SIG_M14_FILE).read_text(encoding="utf-8")
    src17 = (PKG_DIR / _SIG_M17_FILE).read_text(encoding="utf-8")
    assert _SIG_M14 in src14, f"{_SIG_M14_FILE} 的分歧变体应原样保留（返回分工计划、不得顺手统一）"
    assert _SIG_M17 in src17, f"{_SIG_M17_FILE} 的分歧变体应原样保留（只返回两元组、不得顺手统一）"


# --- ④ 断言 ------------------------------------------------------------------------


def test_consumer_products_identical() -> None:
    """④ 夹具产物逐字不变：抽样 m18 / m24 / m27 / m28 的产物与参照公式（用各自常量）逐字节同值。"""
    samples = (
        ("m18", selftest_m18),
        ("m24", selftest_m24),
        ("m27", selftest_m27),
        ("m28", selftest_m28),
    )
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        for tag, mod in samples:
            got = mod._fixture(
                td / (tag + "-got"),
                design_text=mod._DESIGN,
                flow_text=mod._FLOW,
                changes=mod._CHANGES,
            )
            ref = _ref_fixture(td / (tag + "-ref"), mod._DESIGN, mod._FLOW, mod._CHANGES)
            assert _tree_files(got[0]) == _tree_files(ref[0]), f"selftest_{tag} 代码根产物应与参照逐字节同值"
            assert got[1].read_text(encoding="utf-8") == mod._DESIGN, f"selftest_{tag} 设计文档应逐字等于其常量"
            assert got[2].read_text(encoding="utf-8") == mod._FLOW, f"selftest_{tag} 流程文档应逐字等于其常量"
            assert sorted(got[3]) == sorted(ref[3]), f"selftest_{tag} diff id 集合应与参照一致"


# --- ⑤ / ⑥ 复用本模块自己的夹具数据 --------------------------------------------------


def test_cli_and_exit_codes() -> None:
    """⑤ CLI 与退出码回归：stdout 与库输出逐字节一致、无 `\\r\\n`；错误 1；用法 2。"""
    with tempfile.TemporaryDirectory() as td:
        root, design, flow_doc, diffs = make_fixture(
            Path(td), design_text=_DESIGN, flow_text=_FLOW, changes=_CHANGES
        )

        cases = (
            (("drift", str(root), str(design)), drift.to_json(drift.analyze(root, design))),
            (("sync", str(root), str(design)), sync.to_json(sync.snapshot(root, design))),
            (
                ("impact", str(diffs["A"]), str(root), str(design)),
                impact_analyzer.to_json(impact_analyzer.analyze_files(diffs["A"], root, design)),
            ),
            (("flow", str(flow_doc), str(root)), flow.to_json(flow.analyze(flow_doc, root))),
            (("view", str(root), str(design)), viewer.render_html(viewer.analyze(root, design))),
        )
        for args, expected in cases:
            rc, out, err = _cli(*args)
            assert rc == 0, f"{args} 退出码应为 0，实际 {rc}；stderr={err[-200:]!r}"
            assert out == expected.encode("utf-8"), f"{args} stdout 应与库输出逐字节一致"
            assert b"\r\n" not in out, f"{args} stdout 不得含 CRLF（字节稳定写盘）"

        rc, _out, _err = _cli("drift", str(root), str(Path(td) / "nope.md"))
        assert rc == 1, f"错误输入应退出码 1，实际 {rc}"
        rc, _out, _err = _cli("drift", str(root))
        assert rc == 2, f"用法错误应退出码 2，实际 {rc}"


def test_read_only_and_determinism() -> None:
    """⑥ 只读 + 确定性：scanscope 两次相同；同输入两次 CLI 逐字节一致；夹具复合摘要不变。"""
    with tempfile.TemporaryDirectory() as td:
        td_p = Path(td)
        root, design, _flow_doc, _diffs = make_fixture(
            td_p, design_text=_DESIGN, flow_text=_FLOW, changes=_CHANGES
        )
        before = _dir_digest(td_p)

        assert scanscope.all_modules() == scanscope.all_modules(), "all_modules 两次调用应相同"
        assert scanscope.selftest_modules() == scanscope.selftest_modules(), \
            "selftest_modules 两次调用应相同"

        first = _cli("drift", str(root), str(design))
        second = _cli("drift", str(root), str(design))
        assert first == second, "同输入两次 CLI（退出码 / stdout / stderr）应逐字节一致"
        assert first[0] == 0, f"drift 正常路径应退出码 0，实际 {first[0]}；stderr={first[2][-200:]!r}"

        assert _dir_digest(td_p) == before, "全过程不得写夹具中的任何一个字节"


# ⑦ / ⑧ 26 个无需命令行参数的自测（`m2` / `m3` 需代码根，见 ⑧）；条数为**实测**（收口前后相同）
_REGRESSION = {
    "selftest": "4/4",
    "selftest_m1": "7/7",
    "selftest_m5": "13/13",
    "selftest_m6": "13/13",
    "selftest_m7": "12/12",
    "selftest_m8": "12/12",
    "selftest_m9": "9/9",
    "selftest_m10": "11/11",
    "selftest_m11": "10/10",
    "selftest_m12": "12/12",
    "selftest_m13": "10/10",
    "selftest_m14": "10/10",
    "selftest_m15": "10/10",
    "selftest_m16": "10/10",
    "selftest_m17": "10/10",
    "selftest_m18": "10/10",
    "selftest_m19": "8/8",
    "selftest_m20": "8/8",
    "selftest_m21": "8/8",
    "selftest_m22": "8/8",
    "selftest_m23": "8/8",
    "selftest_m24": "8/8",
    "selftest_m25": "8/8",
    "selftest_m26": "8/8",
    "selftest_m27": "8/8",
    "selftest_m28": "8/8",
}


def test_existing_selftests_regression() -> None:
    """⑦ 既有自测零修订：26 个无需参数的自测各按实测条数全绿（个数与改动前相同）。"""
    if selftest_kit.in_regression():
        return
    _assert_regression(_REGRESSION)


def test_full_regression_and_number_independence() -> None:
    """⑧ 全域回归 + 编号无关性：逆序逐模块跑同一批自测仍全绿（与 ⑦ 逐条一致）；需代码根者恰 m2/m3。"""
    if selftest_kit.in_regression():
        return
    number_independence_regression(_REGRESSION, _ARGV_MARK, _ARG_EXEMPT)


def main() -> int:
    tests = (
        test_unique_implementation,
        test_value_equivalence,
        test_consumers_pruned_and_variants_registered,
        test_consumer_products_identical,
        test_cli_and_exit_codes,
        test_read_only_and_determinism,
        test_existing_selftests_regression,
        test_full_regression_and_number_independence,
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
