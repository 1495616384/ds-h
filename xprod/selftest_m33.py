"""M33 自测：把「宿主文件名 / 定义前缀」两件字面量常量的唯一实现收口（同名别名绑定）的验收点写成可执行断言。

背景（`X产品化-M33设计稿-v1.md` §一）：两件**纯字面量常量**此前被各消费文件各写一遍、且连本地名都不统一——
「宿主文件名」有 `_KIT`（8 处，`m25`–`m32`）+ `_KIT_NAME`（1 处，`m24`）；「定义前缀」有 `_D`（5 处，`m27`–`m31`）
+ `_DEF_PREFIX`（1 处，`m24`）——**共 15 处定义、没有任何一处是定义源**。M33 把这两件收归 `selftest_kit.py`
的**唯一实现**（公共名 `KIT_NAME` / `DEF_PREFIX`），9 个消费文件删除本地定义、在既有 `from .selftest_kit import …`
中**追加同名别名绑定**——因输入是**纯字面量常量**（不随模块变化），故走 M30 / M32 式**零包装、零调用点改动**。

**实测裁定（以实测为准；§三 方案 C 被否）**：`_CHANGES` 是**2 个语义不同的真数据变体**——组 A
（`m14` / `m15` / `m16`）为 **5 元**、组 B（`m18`–`m24`、`m26`–`m33`）为 **2 元**；两组**不是**同一份数据的两种
写法（造几个 diff、跑几个改动），合并会**改变夹具产物**，故按 M28 / M29 先例「**分歧变体显式登记、不收口**」——
本文件 ③ 只把两组的**文件集与元数**固化为结构断言。`_REGRESSION` / `_DESIGN` / `_FLOW` / `main()` 属逐模块
**数据**或形态各异，**留本地**。

**自指防护**：本文件同样会被多份既有结构断言扫到，故所有待查特征串一律**分段拼接**构造
（`"selftest" + "_kit.py"`、`"def" + " "`、`"KIT" + "_NAME"`、`"^" + _N_PUB + " = "` …），使本文件源码
**不**字面出现这些特征串（与 M23–M32 同法）。

覆盖（对应设计稿 §七 ①–⑧）：
  ① **唯一实现 + 旧写法收敛**：行首锚定的 `KIT_NAME =` / `DEF_PREFIX =` 在自测模块中**各恰 1 处**且均在宿主；
     自测文件中行首锚定的 `_KIT =` / `_D =` / `_KIT_NAME =` / `_DEF_PREFIX =` **各恰 0 处**；且**字面量口径**核对：
     两件字面量的**定义处**只应在宿主恰 1 处、消费文件 0 处。
  ② **值等价**：`kit.KIT_NAME` / `kit.DEF_PREFIX` 与收口前两件字面量逐值相同（分段拼接的判据常量在源码内）。
  ③ **绑定同源 + `_CHANGES` 裁定登记**：`m25`–`m32` 的 `_KIT`、`m24` 的 `_KIT_NAME`、`m27`–`m31` 的 `_D`、
     `m24` 的 `_DEF_PREFIX` 与宿主**同一对象**；`_CHANGES` 的 **2 组**按**显式名单**登记（组 A → 5 元、组 B → 2 元），
     且定义文件集恰为两组之并（**不**存在跨组的第三种写法）。
  ④ **调用点未改**：9 文件内 `_KIT` / `_KIT_NAME` / `_D` / `_DEF_PREFIX` 的调用点与收口前**逐字相同**（对照清单）。
  ⑤ **既有断言仍成立**：`m24` ④、`m25` ②、`m26`–`m32` 的唯一实现 / 全签名计数、`m30` ③ 与 `m31` ③ 全绿。
  ⑥ **只读 + 确定性**：夹具复合摘要不变；`scanscope.*` 两次调用逐条相同；常量读取稳定。
  ⑦ **既有自测零修订**：30 个无需参数的自测各按**实测**条数全绿（经共享 `assert_regression`）。
  ⑧ **全域回归 + 编号无关性**：逆序跑同一批自测全绿（与 ⑦ 逐条一致）；需代码根者仍恰为 `m2` / `m3`。

沿用 M0–M32 约定：**不**用管道捕获输出，改临时文件重定向（本机沙箱禁建管道）——
本文件自身的脚手架调用一律经 `selftest_kit` 唯一实现，**不**内联子进程调用。
"""

from __future__ import annotations

import ast
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
    selftest_m32,
)
from .selftest_kit import (
    PKG_DIR,
    assert_regression,
    dir_digest as _dir_digest,
    make_fixture as _fixture,
    number_independence_regression,
    ARG_EXEMPT as _ARG_EXEMPT,
    ARGV_MARK as _ARGV_MARK,
)

# --- 待查特征串**分段拼接**（见模块 docstring 的「自指防护」）：拼出的结果不在本文件源码中字面出现 ----
_L_KIT = "selftest" + "_kit.py"      # 「宿主文件名」字面量（① 的字面量口径）
_L_DEF = "def" + " "                 # 「定义前缀」字面量
_N_PUB_KIT = "KIT" + "_NAME"         # 公共常量名（①）
_N_PUB_DEF = "DEF" + "_PREFIX"
_N_LOC_KIT = "_" + "KIT"             # 收口前本地名：`_KIT`（`m25`–`m32`）
_N_LOC_DEF = "_" + "D"               # 收口前本地名：`_D`（`m27`–`m31`）
_N_LOC_KIT_NAME = "_" + _N_PUB_KIT
_N_LOC_DEF_PREFIX = "_" + _N_PUB_DEF
_ANY_ASSIGN = r"^[A-Za-z_][A-Za-z0-9_]* = "   # 行首锚定：任意顶层常量赋值

# ① 公共常量定义（行首锚定）与收口前的四个本地名定义（收口后应 0 处）
_RE_PUB = (
    re.compile("^" + _N_PUB_KIT + " = ", re.M),
    re.compile("^" + _N_PUB_DEF + " = ", re.M),
)
_RE_LOCAL = (
    re.compile("^" + _N_LOC_KIT + " = ", re.M),
    re.compile("^" + _N_LOC_DEF + " = ", re.M),
    re.compile("^" + _N_LOC_KIT_NAME + " = ", re.M),
    re.compile("^" + _N_LOC_DEF_PREFIX + " = ", re.M),
)
# ① 字面量口径：两件字面量的**赋值定义**（行首锚定）
_RE_LIT_KIT = re.compile(_ANY_ASSIGN + re.escape('"' + _L_KIT + '"'), re.M)
_RE_LIT_DEF = re.compile(_ANY_ASSIGN + re.escape('"' + _L_DEF + '"'), re.M)

# ③ 绑定同源名单（消费文件与其模块对象）——`_KIT` 8 处、`_D` 5 处、`m24` 另占两类
_KIT_CONSUMERS = (
    ("selftest_m25.py", selftest_m25),
    ("selftest_m26.py", selftest_m26),
    ("selftest_m27.py", selftest_m27),
    ("selftest_m28.py", selftest_m28),
    ("selftest_m29.py", selftest_m29),
    ("selftest_m30.py", selftest_m30),
    ("selftest_m31.py", selftest_m31),
    ("selftest_m32.py", selftest_m32),
)
_D_CONSUMERS = (
    ("selftest_m27.py", selftest_m27),
    ("selftest_m28.py", selftest_m28),
    ("selftest_m29.py", selftest_m29),
    ("selftest_m30.py", selftest_m30),
    ("selftest_m31.py", selftest_m31),
)

# ③ `_CHANGES` 裁定登记：**2 个真数据变体**（显式名单；**不收口**）——组 A 5 元、组 B 2 元
_CH_NAME = "_CHAN" + "GES"
_CH_A_FILES = ("selftest_m14.py", "selftest_m15.py", "selftest_m16.py")
_CH_B_FILES = (
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
    "selftest_m29.py",
    "selftest_m30.py",
    "selftest_m31.py",
    "selftest_m32.py",
    "selftest_m33.py",
)

# ④ 调用点真值清单（**逐字写死**，收口前后相同；表达式而非处数）
_CALLPOINTS = (
    ("selftest_m24.py", (
        'f"{_DEF_PREFIX}{n}("',
        "p.name != _KIT_NAME",
        "sorted([_KIT_NAME, *_ARG_EXEMPT])",
    )),
    ("selftest_m25.py", ("defs == [_KIT]", "lits == {_KIT: 2}")),
    ("selftest_m26.py", ("_EXCLUDE = {_KIT}",)),
    ("selftest_m27.py", ('_D + "diff_one_file(path: str, old: str, new: str) -> str:"',)),
    ("selftest_m28.py", (
        '_SIG_PUBLIC = _D + "make_min_root(td: Path) -> Path:"',
        '_SIG_LOCAL = _D + "_make_root(td: Path) -> Path:"',
    )),
    ("selftest_m29.py", (
        '_SIG_LOCAL4 = _D + "_fixture(td: Path) -> tuple[Path, Path, Path, dict[str, Path]]:"',
    )),
    ("selftest_m30.py", ('_D + "all" + "_passed(tail: str) -> bool:"',)),
    ("selftest_m31.py", ('_SIG_NIR = _D + _NIR + "("',)),
    ("selftest_m32.py", ("(PKG_DIR / _KIT).is_file()",)),
)


# --- ① 断言 ------------------------------------------------------------------------


def test_unique_implementation() -> None:
    """① 唯一实现：公共常量各恰 1 处且在宿主；自测文件中四个本地名各 0 处；字面量口径同真值。"""
    for pat in _RE_PUB:
        hits: dict[str, int] = {}
        for p in scanscope.selftest_modules():
            n = len(pat.findall(p.read_text(encoding="utf-8")))
            if n:
                hits[p.name] = n
        assert hits == {selftest_kit.KIT_NAME: 1}, \
            f"公共常量定义应全仓恰 1 处且位于宿主：{pat.pattern!r} → {hits}"

    for pat in _RE_LOCAL:
        hits = {}
        for p in scanscope.selftest_modules():
            n = len(pat.findall(p.read_text(encoding="utf-8")))
            if n:
                hits[p.name] = n
        assert hits == {}, f"自测文件中不得再定义本地常量（应收口为共享引用）：{pat.pattern!r} → {hits}"

    for pat, lit in ((_RE_LIT_KIT, _L_KIT), (_RE_LIT_DEF, _L_DEF)):
        hits = {}
        for p in scanscope.selftest_modules():
            n = len(pat.findall(p.read_text(encoding="utf-8")))
            if n:
                hits[p.name] = n
        assert hits == {selftest_kit.KIT_NAME: 1}, \
            f"字面量 {lit!r} 的定义处应只在宿主恰 1 处，实际 {hits}"
        for p in scanscope.selftest_modules():
            if p.name == selftest_kit.KIT_NAME:
                continue
            assert not pat.search(p.read_text(encoding="utf-8")), \
                f"消费文件 {p.name} 不得再自定义字面量 {lit!r}（应收口为共享引用）"


# --- ② 断言 ------------------------------------------------------------------------


def test_value_equivalence() -> None:
    """② 值等价：公共常量与收口前字面量逐值相同；`PKG_DIR` 仍可解析；宿主文件仍在。"""
    assert selftest_kit.KIT_NAME == _L_KIT, \
        f"宿主文件名应与收口前字面量逐值相同，实际 {selftest_kit.KIT_NAME!r}"
    assert selftest_kit.DEF_PREFIX == _L_DEF, \
        f"定义前缀应与收口前字面量逐值相同，实际 {selftest_kit.DEF_PREFIX!r}"
    assert PKG_DIR.is_dir(), f"包目录应为存在目录，实际 {PKG_DIR}"
    assert (PKG_DIR / selftest_kit.KIT_NAME).is_file(), "包目录内应含唯一实现宿主文件"


# --- ③ 断言 ------------------------------------------------------------------------


def _arity(name: str) -> int | None:
    """取某自测文件顶层 `_CHANGES` 的**元数**（按 AST 读值；未定义即返回 `None`，不作静默跳过）。"""
    for node in ast.parse((PKG_DIR / name).read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id == _CH_NAME:
                    return len(node.value.elts) if isinstance(node.value, ast.Tuple) else -1
    return None


def test_binding_identity_and_changes_registered() -> None:
    """③ 绑定同源 + `_CHANGES` 裁定登记：9 处别名绑定指向宿主同一对象；2 组真数据变体显式登记。"""
    for name, mod in _KIT_CONSUMERS:
        assert mod._KIT is selftest_kit.KIT_NAME, \
            f"{name} 的宿主文件名应经别名绑定指向宿主同一对象（不得本地复刻）"
    for name, mod in _D_CONSUMERS:
        assert mod._D is selftest_kit.DEF_PREFIX, \
            f"{name} 的定义前缀应经别名绑定指向宿主同一对象（不得本地复刻）"
    assert selftest_m24._KIT_NAME is selftest_kit.KIT_NAME, \
        "m24 的宿主文件名应经别名绑定指向宿主同一对象"
    assert selftest_m24._DEF_PREFIX is selftest_kit.DEF_PREFIX, \
        "m24 的定义前缀应经别名绑定指向宿主同一对象"

    arities_a = {name: _arity(name) for name in _CH_A_FILES}
    arities_b = {name: _arity(name) for name in _CH_B_FILES}
    assert set(arities_a.values()) == {5}, f"组 A 应为 5 元的真数据变体，实际 {arities_a}"
    assert set(arities_b.values()) == {2}, f"组 B 应为 2 元的真数据变体，实际 {arities_b}"

    defs = {
        p.name for p in scanscope.selftest_modules() if _arity(p.name) is not None
    }
    assert defs == set(_CH_A_FILES) | set(_CH_B_FILES), \
        f"`{_CH_NAME}` 的定义文件集应恰为两组登记名单之并（不得出现第三种写法），实际 {sorted(defs)}"


# --- ④ 断言 ------------------------------------------------------------------------


def test_callpoints_unchanged() -> None:
    """④ 调用点未改：9 文件内的调用点表达式与收口前**逐字相同**（对照写死的清单，非处数计数）。"""
    for name, exprs in _CALLPOINTS:
        src = (PKG_DIR / name).read_text(encoding="utf-8")
        for expr in exprs:
            assert expr in src, f"{name} 的调用点应逐字保留，实际缺失：{expr!r}"


# --- ⑤ 断言 ------------------------------------------------------------------------


def test_existing_assertions_still_green() -> None:
    """⑤ 既有断言仍成立：m24 ④、m25 ②、m26–m32 唯一实现 / 全签名计数、m30 ③ 与 m31 ③ 全绿。"""
    selftest_m24.test_consumers_no_local_replication()
    selftest_m25.test_guard_shape()
    selftest_m26.test_unique_implementation()
    selftest_m27.test_unique_implementation()
    selftest_m28.test_unique_implementation()
    selftest_m29.test_unique_implementation()
    selftest_m30.test_unique_implementation()
    selftest_m30.test_consumers_pruned_and_registered()
    selftest_m31.test_unique_implementation()
    selftest_m31.test_thin_wrapper_shape()
    selftest_m32.test_unique_implementation()


# --- ⑥ 只读 + 确定性：本模块自己的三份夹具数据 ------------------------------

_DESIGN = (
    "# 夹具设计文档（M33 自测专用）\n"
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
    "# 流程夹具（M33 自测专用）\n"
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
    """⑥ 只读 + 确定性：夹具复合摘要不变；`scanscope.*` 两次调用逐条相同；常量读取稳定。"""
    with tempfile.TemporaryDirectory() as td:
        td_p = Path(td)
        _fixture(td_p, design_text=_DESIGN, flow_text=_FLOW, changes=_CHANGES)
        before = _dir_digest(td_p)

        assert scanscope.all_modules() == scanscope.all_modules(), "all_modules 两次调用应相同"
        assert scanscope.selftest_modules() == scanscope.selftest_modules(), \
            "selftest_modules 两次调用应相同"
        assert selftest_kit.KIT_NAME == _L_KIT and selftest_kit.DEF_PREFIX == _L_DEF, \
            "常量读取应稳定且与收口前字面量逐值相同"

        assert _dir_digest(td_p) == before, "全过程不得写夹具中的任何一个字节"


# --- ⑦ / ⑧ 30 个无需命令行参数的自测（`m2` / `m3` 需代码根，见 ⑧）；条数为**实测** ------------


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
    "selftest_m32": "8/8",
}


def test_existing_selftests_regression() -> None:
    """⑦ 既有自测零修订：30 个无需参数的自测各按实测条数全绿（经共享 `assert_regression`）。"""
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
        test_binding_identity_and_changes_registered,
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
