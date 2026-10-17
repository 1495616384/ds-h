"""M30 自测：把「自测『全域回归判定』的唯一实现收口（同名绑定，零调用点改动）」的验收点写成可执行断言。

背景（`X产品化-M30设计稿-v1.md` §一）：`xprod` 的自测都要「判全域回归是否全绿」，做法是三件小事——
正则常量 `_ALL_PASSED`、末行判定 `_all_passed(tail)`、集合断言 `_assert_regression(expected)`。
这三件在 **7 个自测文件**（`m18`、`m19`、`m20`、`m21`、`m22`、`m23`、`m24`）里**各自复刻**，
共 **12 处定义**、**没有任何一处是定义源**；实测已出现**死代码复刻**（`m19` / `m20` 定义了
`_all_passed` 却从不调用，`m21` / `m22` 定义了 `_ALL_PASSED` 却从不使用）。M30 把这三件收归
`selftest_kit.py` 的**唯一实现**（公共名 `ALL_PASSED` / `all_passed` / `assert_regression`），
7 个消费文件删除本地定义，改为**同名绑定**（`all_passed as _all_passed` /
`assert_regression as _assert_regression`）——因输入全是**显式参数或无参常量**，故**调用点一字不改**。

**本轮与设计稿 §四 / §八 的**口径校正**（以实测为准）**：设计稿原按「每个本地定义各配一条别名绑定」
列出 `m18` 加 `_ALL_PASSED` + `_all_passed`、`m19` / `m20` 亦同。实测 `_ALL_PASSED` **只**在
`_all_passed` 内部被引用，`m19` / `m20` 的 `_all_passed` **从不被调用**——故若照原稿绑定，会**立刻
制造新的死引用**（正是本轮要消除的东西）。校正后的实际绑定：`m18` 加 `all_passed as _all_passed`；
`m19` / `m20` **无**绑定；`m21` / `m22` / `m23` / `m24` 各加 `assert_regression as _assert_regression`。
本文件 ③ 相应改为 **M27 式「引用了则必须绑定」**（而非「逐文件都要有绑定」）。

**自指防护**：本文件同样会被 ① / ③ 扫到，故待查特征串一律**分段拼接**构造
（`_D + "all" + "_passed(tail: str) -> bool:"`），使本文件源码**不**字面出现那 6 类**全签名特征串**
（`ALL_PASSED` / `all_passed` / `assert_regression` 及其带下划线的旧名；与 M23 / M24 / M27 / M29 同法）。

覆盖（对应设计稿 §八 ①–⑧）：
    ① **唯一实现（结构证据）**：3 个公共名的**全签名**在全部模块（= `scanscope.all_modules()`）中
       **各恰 1 处**且均位于 `selftest_kit.py`；自测文件中**不得**再出现 3 个旧全签名；
    ② **值等价 + 消费者自洽**：`all_passed` 与**本文件内独立参照公式**（不依赖正则）在多组输入上
       **逐条同结论**；`ALL_PASSED` 与共享宿主**同一对象**；`PKG_DIR` 仍可解析；
    ③ **消费点已无本地复刻 + 登记项仍在**：7 个消费文件**不含**旧全签名、**引用了则必须绑定**
       对应别名；§1.4 登记的 5 个名字**仍按实测处数存在**（本文件自身除外）；
    ④ **行为逐字不变（热路径证据）**：`m18` / `m23` / `m24` 的绑定**就是**共享实现（同一对象），
       且「全绿 / 未全绿 / 缺模块」三例结论与独立参照公式**逐条相同**；
    ⑤ **CLI 与退出码回归**：`drift` / `sync` / `impact` / `flow` / `view` 正常路径 stdout 与库输出
       **逐字节一致**、退出码 **0**、**无 `\\r\\n`**；错误 **1**；用法 **2**；
    ⑥ **只读 + 确定性**：同输入两次**逐字节一致**；`scanscope.*` 两次调用**相同**；夹具目录复合摘要**不变**；
    ⑦ **既有自测零修订**：无需命令行参数的自测**全部**按**实测**条数全绿（**个数与改动前相同**）；
    ⑧ **全域回归 + 编号无关性 + 边界**：逆序跑同一批自测全绿（与 ⑦ 正序逐条一致 → 编号无关）；
       需命令行代码根者仍**恰为** `m2` / `m3`（由里程碑级全域回归覆盖）。

沿用 M0–M29 约定：**不**用管道捕获输出，改临时文件重定向（本机沙箱禁建管道）——
本文件自身的脚手架调用一律经 `selftest_kit` 唯一实现，**不**内联子进程调用。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from . import drift, flow, impact_analyzer, scanscope, selftest_kit, sync, viewer
from . import selftest_m18, selftest_m23, selftest_m24
from .selftest_kit import (
    ALL_PASSED,
    PKG_DIR,
    all_passed,
    assert_regression,
    capture_raises as _capture,
    cli as _cli,
    dir_digest as _dir_digest,
    last_line as _last_line,
    make_fixture,
    run_module as _run_module,
)

# 宿主文件名（唯一实现所在）与本文件名（③ 的登记项计数须排除自身）
_KIT = "selftest_kit.py"
_SELF = "selftest_m30.py"

# 待查特征串**分段拼接**（见模块 docstring 的「自指防护」）：拼出的结果不在本文件源码中字面出现
_D = "def "
_UND = "_"
_RE_SRC = r'r"^(?P<ok>\d+)/(?P<total>\d+) passed$"'

# ① 3 个公共名的全签名（§四 写死的那三行）
_SIG_CONST = "ALL" + "_PASSED" + " = re.compile(" + _RE_SRC + ")"
_SIG_ALL = _D + "all" + "_passed(tail: str) -> bool:"
_SIG_ASSERT = _D + "assert" + "_regression(expected: dict[str, str]) -> None:"

# ③ 收口前 3 个本地名的全签名（收口后应全仓 0 处）
_OLD_CONST = _UND + _SIG_CONST
_OLD_ALL = _D + _UND + "all" + "_passed(tail: str) -> bool:"
_OLD_ASSERT = _D + _UND + "assert" + "_regression(expected: dict[str, str]) -> None:"

# ③ 消费形态：本地名 → （引用特征串, 别名绑定串）——M27 式「引用了则必须绑定」
_BINDINGS = (
    (_UND + "all" + "_passed", _UND + "all" + "_passed(", "all" + "_passed as " + _UND + "all" + "_passed"),
    (
        _UND + "assert" + "_regression",
        _UND + "assert" + "_regression(",
        "assert" + "_regression as " + _UND + "assert" + "_regression",
    ),
)

# ③ 名单：7 个消费文件（本轮收口）
_CONSUMERS = (
    "selftest_m18.py",
    "selftest_m19.py",
    "selftest_m20.py",
    "selftest_m21.py",
    "selftest_m22.py",
    "selftest_m23.py",
    "selftest_m24.py",
)

# ③ §1.4 登记保留的名字（**不**收口、留给 M31）：必须仍按实测处数存在（计数不含本文件）
_REGISTERED = (
    (
        "def test_full_regression_extra(",
        {"selftest_m21.py": 1, "selftest_m22.py": 1, "selftest_m23.py": 1},
    ),
    (
        "def test_full_regression_and_number_independence(",
        {"selftest_m26.py": 1, "selftest_m27.py": 1, "selftest_m28.py": 1, "selftest_m29.py": 1},
    ),
    (
        "def test_existing_selftests_regression(",
        {
            "selftest_m23.py": 1,
            "selftest_m24.py": 1,
            "selftest_m26.py": 1,
            "selftest_m27.py": 1,
            "selftest_m28.py": 1,
            "selftest_m29.py": 1,
        },
    ),
    ("def _entry(", {"selftest_m10.py": 1, "selftest_m11.py": 1}),
)
_MAIN_NEEDLE = "def main("
_MAIN_TOTAL = 30        # 实测：本文件之外含 `def main(` 的文件数（29 个自测 + __main__.py）

# ② 多组输入：含全绿 / 零比零 / 未全绿 / 非 `N/N` 形状 / 空串 / 前后空白（参照公式不依赖正则，独立推导）
_TAILS = (
    "3/3 passed",
    "0/0 passed",
    "2/3 passed",
    "10/10 passed",
    "1/2 passed",
    "3 of 3 passed",
    "passed",
    "",
    " 3/3 passed",
    "3/3 passed ",
    "٣/٣ passed",     # 阿拉伯-印度数字：`\\d` 亦命中，参照公式须一致
)

_ARGV_MARK = "sys" + ".argv"          # 「取命令行参数」特征串（⑧）
_ARG_EXEMPT = ("selftest_m2.py", "selftest_m3.py")

# ⑤ / ⑥ 用的夹具数据（本模块自己的三份；与收口前的自测同形，仅题头不同）
_DESIGN = (
    "# 夹具设计文档（M30 自测专用）\n"
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
    "# 流程夹具（M30 自测专用）\n"
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


# --- ② / ④ 用的独立参照公式（**写死**在自测里，与共享实现逐条对照）---------------------


def _ref_all_passed(tail: str) -> bool:
    """参照公式：**不依赖正则**地独立推导「`N/N passed` 且两数相等」（与共享实现逐条对照）。"""
    suffix = " passed"
    if not tail.endswith(suffix):
        return False
    parts = tail[: -len(suffix)].split("/")
    if len(parts) != 2 or not all(p.isdigit() for p in parts):
        return False
    return int(parts[0]) == int(parts[1])


def _ref_assert_raises(expected: dict[str, str]) -> bool:
    """参照公式：**独立实现**地推导「集合断言是否会抛」（任一模块 rc≠0 或尾行不符即应抛）。"""
    for mod, want in expected.items():
        rc, out, _err = _run_module(mod)
        if rc != 0 or _last_line(out) != f"{want} passed":
            return True
    return False


# --- ① / ② / ③ 断言 ---------------------------------------------------------------


def test_unique_implementation() -> None:
    """① 唯一实现（结构证据）：3 个公共名全签名各恰 1 处且在宿主；旧全签名在自测文件中 0 处。"""
    for sig in (_SIG_CONST, _SIG_ALL, _SIG_ASSERT):
        hits: dict[str, int] = {}
        for p in scanscope.all_modules():
            n = p.read_text(encoding="utf-8").count(sig)
            if n:
                hits[p.name] = n
        assert hits == {_KIT: 1}, f"公共判定应全仓恰 1 处且位于 {_KIT}：{sig!r} → {hits}"

    for p in scanscope.selftest_modules():
        src = p.read_text(encoding="utf-8")
        for sig in (_OLD_CONST, _OLD_ALL, _OLD_ASSERT):
            assert sig not in src, f"自测文件中不得再定义本地判定：{p.name} → {sig!r}"


def test_value_equivalence() -> None:
    """② 值等价 + 消费者自洽：与独立参照公式逐条同结论；公共常量同源；PKG_DIR 仍可解析。"""
    assert selftest_kit.PKG_DIR == scanscope.PKG_DIR, "再导出应与定义源逐字同值"
    assert PKG_DIR.is_dir(), f"包目录应为存在目录，实际 {PKG_DIR}"
    assert (PKG_DIR / "scanscope.py").is_file(), "包目录内应含定义源 scanscope.py"
    assert selftest_kit.ALL_PASSED is ALL_PASSED, "公共常量应与共享宿主同一对象（同源）"

    for tail in _TAILS:
        assert all_passed(tail) == _ref_all_passed(tail), f"末行判定应与参照公式同结论：{tail!r}"

    # 逐条明示四类结论（值等价，而非仅对象同一）
    assert all_passed("3/3 passed") is True
    assert all_passed("0/0 passed") is True
    assert all_passed("2/3 passed") is False
    assert all_passed("3 of 3 passed") is False
    assert all_passed("") is False


def test_consumers_pruned_and_registered() -> None:
    """③ 消费点已无本地复刻（引用了则必须绑定）+ §1.4 登记项仍按实测处数存在。"""
    for name in _CONSUMERS:
        src = (PKG_DIR / name).read_text(encoding="utf-8")
        for sig in (_OLD_CONST, _OLD_ALL, _OLD_ASSERT):
            assert sig not in src, f"{name} 仍含本地判定定义（应收口为共享引用）：{sig!r}"
        for _local, ref, bind in _BINDINGS:
            if ref in src:
                assert bind in src, f"{name} 引用了 {ref}(…) 却未绑定「{bind}」"

    for needle, want in _REGISTERED:
        hits: dict[str, int] = {}
        for p in scanscope.all_modules():
            if p.name == _SELF:
                continue
            n = p.read_text(encoding="utf-8").count(needle)
            if n:
                hits[p.name] = n
        assert hits == want, f"登记项应原样保留（计数不含本文件）：{needle!r} → {hits}"

    main_total = sum(
        p.read_text(encoding="utf-8").count(_MAIN_NEEDLE)
        for p in scanscope.all_modules()
        if p.name != _SELF
    )
    assert main_total == _MAIN_TOTAL, \
        f"`{_MAIN_NEEDLE}` 处数应仍为实测 {_MAIN_TOTAL}（不含本文件），实际 {main_total}"


# --- ④ 断言 ------------------------------------------------------------------------


def test_consumer_behavior_identical() -> None:
    """④ 行为逐字不变：消费点绑定的**就是**共享实现；全绿 / 未全绿 / 缺模块三例与参照同结论。"""
    assert selftest_m18._all_passed is selftest_kit.all_passed, "m18 的末行判定应绑定共享实现（同一对象）"
    assert selftest_m23._assert_regression is selftest_kit.assert_regression, "m23 应绑定共享实现（同一对象）"
    assert selftest_m24._assert_regression is selftest_kit.assert_regression, "m24 应绑定共享实现（同一对象）"

    cases = (
        ({"selftest_m1": "7/7"}, False),          # 全绿：不抛
        ({"selftest_m1": "99/99"}, True),         # 未全绿（条数不符）：应抛
        ({"selftest_no_such": "1/1"}, True),      # 缺模块（rc≠0）：应抛
    )
    for expected, want_raise in cases:
        got = _capture(selftest_m24._assert_regression, dict(expected))
        raised = got is not None
        assert raised == want_raise, f"{expected} 结论应为 raised={want_raise}，实际 {got!r}"
        if want_raise:
            assert type(got) is AssertionError, f"{expected} 应抛 AssertionError，实际 {type(got)}"
        assert raised == _ref_assert_raises(dict(expected)), \
            f"{expected} 结论应与独立参照公式一致"


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


# ⑦ / ⑧ 27 个无需命令行参数的自测（`m2` / `m3` 需代码根，见 ⑧）；条数为**实测**（收口前后相同）
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
    "selftest_m29": "8/8",
}


def test_existing_selftests_regression() -> None:
    """⑦ 既有自测零修订：27 个无需参数的自测各按实测条数全绿（个数与改动前相同）。"""
    if selftest_kit.in_regression():
        return
    for mod, want in _REGRESSION.items():
        rc, out, err = _run_module(mod)
        tail = _last_line(out)
        assert rc == 0 and tail == f"{want} passed", \
            f"{mod} 应为 {want} passed，实际 rc={rc} tail={tail!r} stderr={err[-200:]!r}"


def test_full_regression_and_number_independence() -> None:
    """⑧ 全域回归 + 编号无关性：逆序逐模块跑同一批自测仍全绿（与 ⑦ 逐条一致）；需代码根者恰 m2/m3。"""
    if selftest_kit.in_regression():
        return
    # 需命令行代码根的自测恰为 `m2` / `m3`，由里程碑级全域回归（regress.py 传基线根）覆盖，此处跳过
    arg_mods = sorted(
        p.name for p in scanscope.selftest_modules() if _ARGV_MARK in p.read_text(encoding="utf-8")
    )
    assert arg_mods == list(_ARG_EXEMPT), f"需命令行代码根的自测应恰为 m2 / m3，实际 {arg_mods}"

    for mod in reversed(list(_REGRESSION)):
        rc, out, err = _run_module(mod)
        want = f"{_REGRESSION[mod]} passed"
        tail = _last_line(out)
        assert rc == 0 and tail == want, \
            f"{mod} 逆序应全绿（{want}，与 ⑦ 正序一致），实际 rc={rc} tail={tail!r} stderr={err[-200:]!r}"


def main() -> int:
    tests = (
        test_unique_implementation,
        test_value_equivalence,
        test_consumers_pruned_and_registered,
        test_consumer_behavior_identical,
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
