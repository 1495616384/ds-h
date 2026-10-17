"""M28 自测：把「自测夹具『最小代码根构造』的唯一实现收口」的验收点写成可执行断言。

背景（`X产品化-M28设计稿-v1.md` §一）：`xprod` 的自测文件都要先造一份「最小代码根」
（`td/root` 下的目录骨架 + `api.py`/`core.py`/`notify.py` + `docs/guide.md`/`docs/spec.md`
两个非 `.py` 载体），才能让依赖图有模块名可解析、有节点可用。这个造根动作 `_make_root(td)`
在 **19 个自测文件**里各写了一遍：其中 **10 处**（`m17`–`m24`、`m26`、`m27`）**逐字同构**
（AST 归一化后含签名与文档串完全一致），另 **9 处**（`m8`–`m16`）是**同名同签名但文件集各不相同**
的**真分歧变体**（`m10`/`m11` 特意不建 `core.py`、`m12` 不建 `__init__.py`、`m13`/`m14` 多 `report.py`……）。
M28 把那 **10 处逐字同构**收归 `selftest_kit.py` 的**唯一实现**（公共名 `make_min_root`），
10 个消费文件删除本地 `def`、改为在既有 `from .selftest_kit import …` 中**追加
`make_min_root as _make_root`**（**同名绑定**，故调用点 `_make_root(td)` 一字不改、产物逐字节不变）。

**自指防护**：本文件同样会被 ① / ③ 扫到，故待查特征串一律**分段拼接**构造
（`_D + "make_min_root(td: Path) -> Path:"`），使本文件源码**不**字面出现
「`def <公共名>(…)`」与「`def _make_root(…)`」这两类特征串（与 M23 / M24 / M26 / M27 同法）。

覆盖（对应设计稿 §八 ①–⑧）：
    ① **唯一实现（结构证据）**：公共名 `make_min_root` 的**全签名 `def`** 在全部模块
       （= `scanscope.all_modules()`）中**恰 1 处**且位于 `selftest_kit.py`；
    ② **值等价 + 消费者自洽**：`make_min_root` 与**本文件内独立参照实现**在临时目录上产物
       **逐字节同值**（逐文件路径 + 内容 + 复合摘要）；`PKG_DIR` 仍可解析；
    ③ **消费点已无本地复刻 + 分歧变体登记仍在**：10 个消费文件**不含**本地 `def _make_root`、
       **含**绑定 `make_min_root as _make_root`；`m8`–`m16`**仍含**本地 `def _make_root`；
       全仓本地名 `_make_root` 的**全签名** `def` 命中集**恰为** `{m8…m16}` 这 9 个文件；
    ④ **夹具产物逐字不变（行为）**：抽样 `m18` / `m24` / `m27` 的 `_make_root` 产物与参照**逐字节同值**；
    ⑤ **CLI 与退出码回归**：`drift` / `sync` / `impact` / `flow` / `view` 正常路径 stdout 与库输出
       **逐字节一致**、退出码 **0**、**无 `\\r\\n`**；错误 **1**；用法 **2**；
    ⑥ **只读 + 确定性**：同输入两次**逐字节一致**；`scanscope.*` 两次调用**相同**；
       夹具目录复合摘要**不变**；
    ⑦ **既有自测零修订**：无需命令行参数的自测**全部**按**实测**条数全绿（**个数与改动前相同**）；
    ⑧ **全域回归 + 编号无关性 + 边界**：逆序跑同一批自测全绿（与 ⑦ 正序逐条一致 → 编号无关）；
       需命令行代码根者仍**恰为** `m2` / `m3`（由里程碑级全域回归覆盖）。

沿用 M0–M27 约定：**不**用管道捕获输出，改临时文件重定向（本机沙箱禁建管道）——
本文件自身的脚手架调用一律经 `selftest_kit` 唯一实现，**不**内联子进程调用。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from . import drift, flow, impact_analyzer, scanscope, selftest_kit, sync, viewer
from . import selftest_m18, selftest_m24, selftest_m27
from .selftest_kit import (
    PKG_DIR,
    assert_regression as _assert_regression,
    cli as _cli,
    diff_one_file as _diff,
    dir_digest as _dir_digest,
    make_fixture as _fixture,
    make_min_root as _make_root,
    number_independence_regression,
)

# 宿主文件名（唯一实现所在）
_KIT = "selftest_kit.py"

# 待查特征串**分段拼接**（见模块 docstring 的「自指防护」）：拼出的结果不在本文件源码中字面出现
_D = "def "
_SIG_PUBLIC = _D + "make_min_root(td: Path) -> Path:"
_SIG_LOCAL = _D + "_make_root(td: Path) -> Path:"

# 消费形态：公共名 → 本地名（同名绑定），全部调用点一字不改
_BIND = "make_min_root as _make_root"

# ①/③ 名单：10 个消费文件（本轮收口）与 9 处**真分歧变体**（裁定保留、显式登记）
_CONSUMERS = (
    "selftest_m17.py",
    "selftest_m18.py",
    "selftest_m19.py",
    "selftest_m20.py",
    "selftest_m21.py",
    "selftest_m22.py",
    "selftest_m23.py",
    "selftest_m24.py",
    "selftest_m26.py",
    "selftest_m27.py",
)
_VARIANTS = tuple("selftest_m%d.py" % i for i in range(8, 17))

# ②/④ 参照公式：收口前那份最小代码根的**文件清单与内容**（逐字写死，作为对照真值）
_REF_FILES = (
    ("src/app/__init__.py", ""),
    ("src/app/api.py", "from app.core import X\nA = 0\n"),
    ("src/app/core.py", "X = 1\n"),
    ("src/app/notify.py", "N = 1\n"),
    ("docs/guide.md", "# 指南\n"),
    ("docs/spec.md", "# 规格\n"),
)

_ARGV_MARK = "sys" + ".argv"          # 「取命令行参数」特征串（⑧）
_ARG_EXEMPT = ("selftest_m2.py", "selftest_m3.py")


# --- ②/④ 用的独立参照实现（**写死**在自测里，与样板逐字节对照）-------------------------


def _ref_make_root(td: Path) -> Path:
    """参照公式：按写死的清单建最小代码根（与收口前 10 处逐字同构）。"""
    root = td / "root"
    (root / "src" / "app").mkdir(parents=True)
    (root / "docs").mkdir(parents=True)
    for rel, text in _REF_FILES:
        (root / rel).write_text(text, encoding="utf-8")
    return root


def _tree_files(root: Path) -> list[tuple[str, str]]:
    """把目录树摊成 `(相对路径, 内容)` 列表（只读、按路径排序）——逐字节比对用。"""
    return [
        (p.relative_to(root).as_posix(), p.read_bytes().decode("utf-8"))
        for p in sorted(q for q in root.rglob("*") if q.is_file())
    ]


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
    """② 值等价 + 消费者自洽：与独立参照产物逐字节同值；PKG_DIR 仍可解析。"""
    assert selftest_kit.PKG_DIR == scanscope.PKG_DIR, "再导出应与定义源逐字同值"
    assert PKG_DIR.is_dir(), f"包目录应为存在目录，实际 {PKG_DIR}"
    assert (PKG_DIR / "scanscope.py").is_file(), "包目录内应含定义源 scanscope.py"

    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        got = _make_root(td / "got")
        ref = _ref_make_root(td / "ref")
        assert _tree_files(got) == _tree_files(ref), "make_min_root 产物应与参照清单逐字节同值"
        assert _dir_digest(got) == _dir_digest(ref), "两棵树的复合摘要应相同"


def test_consumers_pruned_and_variants_registered() -> None:
    """③ 消费点已无本地复刻 + 分歧变体登记仍在：命中集恰为 m8–m16；10 消费文件已绑定别名。"""
    for name in _CONSUMERS:
        src = (PKG_DIR / name).read_text(encoding="utf-8")
        assert _SIG_LOCAL not in src, f"{name} 仍含本地制造根定义（应收口为共享引用）"
        assert _BIND in src, f"{name} 未绑定「{_BIND}」"

    for name in _VARIANTS:
        src = (PKG_DIR / name).read_text(encoding="utf-8")
        assert _SIG_LOCAL in src, f"{name} 的分歧变体应原样保留（不在收口口径内、不得顺手统一）"

    hits: dict[str, int] = {}
    for p in scanscope.selftest_modules():
        n = p.read_text(encoding="utf-8").count(_SIG_LOCAL)
        if n:
            hits[p.name] = n
    assert hits == {name: 1 for name in _VARIANTS}, \
        f"本地 `_make_root` 全签名应只留在 {len(_VARIANTS)} 个分歧变体文件，实际 {hits}"


# --- ④ 断言 ------------------------------------------------------------------------


def test_consumer_products_identical() -> None:
    """④ 夹具产物逐字不变：抽样 m18 / m24 / m27 的 `_make_root` 产物与参照逐字节同值。"""
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        ref = _tree_files(_ref_make_root(td / "ref"))
        for tag, mod in (("m18", selftest_m18), ("m24", selftest_m24), ("m27", selftest_m27)):
            got = _tree_files(mod._make_root(td / tag))
            assert got == ref, f"selftest_{tag} 的 _make_root 产物应与参照清单逐字节同值"


# --- ⑤ / ⑥ 复用的夹具（与 M23 / M24 / M26 / M27 同构）-------------------------------


_DESIGN = (
    "# 夹具设计文档（M28 自测专用）\n"
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
    "# 流程夹具（M28 自测专用）\n"
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


def test_cli_and_exit_codes() -> None:
    """⑤ CLI 与退出码回归：stdout 与库输出逐字节一致、无 `\\r\\n`；错误 1；用法 2。"""
    with tempfile.TemporaryDirectory() as td:
        root, design, flow_doc, diffs = _fixture(Path(td), design_text=_DESIGN, flow_text=_FLOW, changes=_CHANGES)

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
        root, design, _flow_doc, _diffs = _fixture(td_p, design_text=_DESIGN, flow_text=_FLOW, changes=_CHANGES)
        before = _dir_digest(td_p)

        assert scanscope.all_modules() == scanscope.all_modules(), "all_modules 两次调用应相同"
        assert scanscope.selftest_modules() == scanscope.selftest_modules(), \
            "selftest_modules 两次调用应相同"

        first = _cli("drift", str(root), str(design))
        second = _cli("drift", str(root), str(design))
        assert first == second, "同输入两次 CLI（退出码 / stdout / stderr）应逐字节一致"
        assert first[0] == 0, f"drift 正常路径应退出码 0，实际 {first[0]}；stderr={first[2][-200:]!r}"

        assert _dir_digest(td_p) == before, "全过程不得写夹具中的任何一个字节"


# ⑦ / ⑧ 25 个无需命令行参数的自测（`m2` / `m3` 需代码根，见 ⑧）；条数为**实测**（收口前后相同）
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
}


def test_existing_selftests_regression() -> None:
    """⑦ 既有自测零修订：25 个无需参数的自测各按实测条数全绿（个数与改动前相同）。"""
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
