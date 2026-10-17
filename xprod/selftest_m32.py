"""M32 自测：把「⑧ 编号无关性所用『输入常量』的唯一实现收口（同名别名绑定）」的验收点写成可执行断言。

背景（`X产品化-M32设计稿-v1.md` §一）：M31 已把 ⑧ 的**遍历过程**（`test_full_regression_and_number_independence`）
收归 `selftest_kit.py` 唯一实现，但 ⑧ 的**输入常量**——判定「哪些自测需要命令行代码根」的特征串 `_ARGV_MARK`
（值 `"sys" + ".argv"`）与豁免名单 `_ARG_EXEMPT`（值 `("selftest_m2.py", "selftest_m3.py")`）——仍在
**8 个**自测文件（`m24`–`m31`）里各写一遍，**没有任何一处是定义源**；8 处的**值完全相同**，差异**仅在注释与写法顺序**，
属**已发生的复刻漂移**。M32 把这两件收归 `selftest_kit.py` 的**唯一实现**（公共名 `ARGV_MARK` / `ARG_EXEMPT`），
8 个消费文件删除本地定义、在既有 `from .selftest_kit import …` 中**追加同名别名绑定**
（`ARGV_MARK as _ARGV_MARK` / `ARG_EXEMPT as _ARG_EXEMPT`）——因输入是**纯字面量常量**（不随模块变化），
故走 M30 式**零包装、零调用点改动**（不需要 M31 的「薄包装」形态）。

**自指防护**：本文件同样会被 ① 与既有结构断言扫到，故待查特征串一律**分段拼接**构造
（`"ARGV" + "_MARK"`、`"^" + _A_PUB + " = "`），使本文件源码**不**字面出现
「行首的公共 / 本地常量定义」与「取命令行参数」的特征串（与 M23–M31 同法）。

覆盖（对应设计稿 §七 ①–⑧）：
    ① **唯一实现（结构证据）**：行首锚定的 `ARGV_MARK = ` / `ARG_EXEMPT = ` 在
       `scanscope.selftest_modules()` 中**各恰 1 处**且均位于 `selftest_kit.py`；
       行首锚定的 `_ARGV_MARK = ` / `_ARG_EXEMPT = ` 在自测文件中**各恰 0 处**；
    ② **值等价**：`kit.ARGV_MARK == "sys" + ".argv"`、`kit.ARG_EXEMPT == ("selftest_m2.py", "selftest_m3.py")`
       （与收口前字面量逐值相同）；`PKG_DIR` 仍可解析、宿主文件仍在；
    ③ **绑定同源**：`m24`–`m31` 的 `_ARGV_MARK` / `_ARG_EXEMPT` 与宿主**同一对象**（别名绑定而非本地复刻）；
    ④ **调用点未改**：8 文件内的调用点表达式与收口前**逐字相同**（对照写死的表达式清单，非按处数计数）；
    ⑤ **既有断言仍成立**：`m24` 的脚手架 needle、`m25` 的守卫形态、`m26` / `m27` 的消费点与导入存在性断言全绿；
    ⑥ **只读 + 确定性**：夹具复合摘要不变；`scanscope.*` 两次调用逐条相同；常量读取稳定；
    ⑦ **既有自测零修订**：29 个无需参数的自测各按**实测**条数全绿（经共享 `assert_regression`）；
    ⑧ **全域回归 + 编号无关性**：逆序跑同一批自测全绿（与 ⑦ 逐条一致）；需代码根者仍恰为 `m2` / `m3`。

沿用 M0–M31 约定：**不**用管道捕获输出，改临时文件重定向（本机沙箱禁建管道）——
本文件自身的脚手架调用一律经 `selftest_kit` 唯一实现，**不**内联子进程调用。
"""

from __future__ import annotations

import re
import tempfile
from pathlib import Path

from . import scanscope, selftest_kit
from . import (
    selftest_m24,
    selftest_m25,
    selftest_m26,
    selftest_m27,
    selftest_m28,
    selftest_m29,
    selftest_m30,
    selftest_m31,
)
from .selftest_kit import (
    PKG_DIR,
    assert_regression,
    dir_digest as _dir_digest,
    make_fixture as _fixture,
    number_independence_regression,
    ARG_EXEMPT as _ARG_EXEMPT,
    ARGV_MARK as _ARGV_MARK,
    KIT_NAME as _KIT,
)

# 待查特征串**分段拼接**（见模块 docstring 的「自指防护」）：拼出的结果不在本文件源码中字面出现
_A_PUB = "ARGV" + "_MARK"                 # 公共常量名（⑧ 的特征串）
_A_EX = "ARG" + "_EXEMPT"                 # 公共豁免名单名
_L_PUB = "_" + _A_PUB                    # 收口前的本地名
_L_EX = "_" + _A_EX
_RE_PUB_MARK = "^" + _A_PUB + " = "       # 行首锚定：公共常量定义（①）
_RE_PUB_EX = "^" + _A_EX + " = "
_RE_L_MARK = "^" + _L_PUB + " = "         # 行首锚定：本地常量定义（①，收口后应 0 处）
_RE_L_EX = "^" + _L_EX + " = "
_NIR = "number" + "_independence_regression"
_NIR_CALL_EXPR = _NIR + "(_REGRESSION, " + _L_PUB + ", " + _L_EX + ")"   # ④ 的调用点真值

# ③ 8 个消费文件与其模块对象（断言绑定与宿主**同一对象**）
_BOUND = (
    ("selftest_m24.py", selftest_m24),
    ("selftest_m25.py", selftest_m25),
    ("selftest_m26.py", selftest_m26),
    ("selftest_m27.py", selftest_m27),
    ("selftest_m28.py", selftest_m28),
    ("selftest_m29.py", selftest_m29),
    ("selftest_m30.py", selftest_m30),
    ("selftest_m31.py", selftest_m31),
)

# ④ 调用点真值清单（**逐字写死**，收口前后相同；表达式而非处数）
_CALLPOINTS = (
    ("selftest_m24.py", (
        '_ARGV_MARK in p.read_text(encoding="utf-8")',
        "sorted([_KIT_NAME, *_ARG_EXEMPT])",
        "list(_ARG_EXEMPT)",
    )),
    ("selftest_m25.py", (
        '_ARGV_MARK in p.read_text(encoding="utf-8")',
        "list(_ARG_EXEMPT)",
    )),
    ("selftest_m26.py", (_NIR_CALL_EXPR,)),
    ("selftest_m27.py", (_NIR_CALL_EXPR,)),
    ("selftest_m28.py", (_NIR_CALL_EXPR,)),
    ("selftest_m29.py", (_NIR_CALL_EXPR,)),
    ("selftest_m30.py", (_NIR_CALL_EXPR,)),
    ("selftest_m31.py", (_NIR_CALL_EXPR,)),
)


# --- ① 断言 ------------------------------------------------------------------------


def test_unique_implementation() -> None:
    """① 唯一实现：公共常量各恰 1 处且在宿主；自测文件中本地常量各 0 处。"""
    for pat in (_RE_PUB_MARK, _RE_PUB_EX):
        hits: dict[str, int] = {}
        for p in scanscope.selftest_modules():
            n = len(re.findall(pat, p.read_text(encoding="utf-8"), re.M))
            if n:
                hits[p.name] = n
        assert hits == {_KIT: 1}, f"公共常量应全仓恰 1 处且位于 {_KIT}：{pat!r} → {hits}"

    for pat in (_RE_L_MARK, _RE_L_EX):
        hits = {}
        for p in scanscope.selftest_modules():
            n = len(re.findall(pat, p.read_text(encoding="utf-8"), re.M))
            if n:
                hits[p.name] = n
        assert hits == {}, f"自测文件中不得再定义本地常量（应收口为共享引用）：{pat!r} → {hits}"


# --- ② 断言 ------------------------------------------------------------------------


def test_value_equivalence() -> None:
    """② 值等价：公共常量与收口前字面量逐值相同；`PKG_DIR` 仍可解析；宿主文件仍在。"""
    assert selftest_kit.ARGV_MARK == "sys" + ".argv", \
        f"特征串应与收口前字面量逐值相同，实际 {selftest_kit.ARGV_MARK!r}"
    assert selftest_kit.ARG_EXEMPT == ("selftest_m2.py", "selftest_m3.py"), \
        f"豁免名单应与收口前字面量逐值相同，实际 {selftest_kit.ARG_EXEMPT!r}"
    assert _ARGV_MARK == selftest_kit.ARGV_MARK, "本文件引用的特征串应与定义源同值"
    assert _ARG_EXEMPT == selftest_kit.ARG_EXEMPT, "本文件引用的豁免名单应与定义源同值"
    assert PKG_DIR.is_dir(), f"包目录应为存在目录，实际 {PKG_DIR}"
    assert (PKG_DIR / _KIT).is_file(), f"包目录内应含唯一实现宿主 {_KIT}"


# --- ③ 断言 ------------------------------------------------------------------------


def test_binding_identity() -> None:
    """③ 绑定同源：8 个消费文件的 `_ARGV_MARK` / `_ARG_EXEMPT` 与宿主**同一对象**。"""
    for name, mod in _BOUND:
        assert mod._ARGV_MARK is selftest_kit.ARGV_MARK, \
            f"{name} 的特征串应经别名绑定指向宿主同一对象（不得本地复刻）"
        assert mod._ARG_EXEMPT is selftest_kit.ARG_EXEMPT, \
            f"{name} 的豁免名单应经别名绑定指向宿主同一对象（不得本地复刻）"


# --- ④ 断言 ------------------------------------------------------------------------


def test_callpoints_unchanged() -> None:
    """④ 调用点未改：8 文件内的调用点表达式与收口前**逐字相同**。"""
    for name, exprs in _CALLPOINTS:
        src = (PKG_DIR / name).read_text(encoding="utf-8")
        for expr in exprs:
            assert expr in src, f"{name} 的调用点应逐字保留，实际缺失：{expr!r}"


# --- ⑤ 断言 ------------------------------------------------------------------------


def test_existing_assertions_still_green() -> None:
    """⑤ 既有断言仍成立：m24 脚手架 needle、m25 守卫形态、m26 / m27 消费点与导入存在性断言全绿。"""
    selftest_m24.test_consumers_no_local_replication()
    selftest_m25.test_guard_shape()
    selftest_m26.test_unique_implementation()
    selftest_m27.test_unique_implementation()


# --- ⑥ 只读 + 确定性：本模块自己的三份夹具数据 ------------------------------

_DESIGN = (
    "# 夹具设计文档（M32 自测专用）\n"
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
    "# 流程夹具（M32 自测专用）\n"
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


def test_read_only_and_determinism() -> None:
    """⑥ 只读 + 确定性：夹具复合摘要不变；`scanscope.*` 两次调用逐条相同。"""
    with tempfile.TemporaryDirectory() as td:
        td_p = Path(td)
        _fixture(td_p, design_text=_DESIGN, flow_text=_FLOW, changes=_CHANGES)
        before = _dir_digest(td_p)

        assert scanscope.all_modules() == scanscope.all_modules(), "all_modules 两次调用应相同"
        assert scanscope.selftest_modules() == scanscope.selftest_modules(), \
            "selftest_modules 两次调用应相同"
        assert _ARGV_MARK == selftest_kit.ARGV_MARK, "常量读取应稳定"
        assert _ARG_EXEMPT == selftest_kit.ARG_EXEMPT, "豁免名单读取应稳定"

        assert _dir_digest(td_p) == before, "全过程不得写夹具中的任何一个字节"


# --- ⑦ / ⑧ 29 个无需命令行参数的自测（`m2` / `m3` 需代码根，见 ⑧）；条数为**实测** ------------


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
    "selftest_m30": "8/8",
    "selftest_m31": "8/8",
}


def test_existing_selftests_regression() -> None:
    """⑦ 既有自测零修订：29 个无需参数的自测各按实测条数全绿（经共享 `assert_regression`）。"""
    if selftest_kit.in_regression():
        return
    assert_regression(_REGRESSION)


def test_full_regression_and_number_independence() -> None:
    """⑧ 全域回归 + 编号无关性：逆序逐模块跑同一批自测仍全绿（与 ⑦ 逐条一致）；需代码根者恰 m2/m3。"""
    if selftest_kit.in_regression():
        return
    number_independence_regression(_REGRESSION, _ARGV_MARK, _ARG_EXEMPT)


def main() -> int:
    tests = (
        test_unique_implementation,
        test_value_equivalence,
        test_binding_identity,
        test_callpoints_unchanged,
        test_existing_assertions_still_green,
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
