"""M31 自测：把「自测『全域回归＋编号无关性』与『夹具记录渲染』的唯一实现收口」的验收点写成可执行断言。

背景（`X产品化-M31设计稿-v1.md` §一；实现期以**实测**裁定、口径校正见 §三）：两件与产品逻辑无关的
事此前被各自复刻——一是「⑧ 全域回归＋编号无关性」（`test_full_regression_and_number_independence`，
`m26`–`m30` 五处**原始源段逐字节相同**），二是「⑤ 夹具记录渲染」（本地 `_entry` + 局部常量 `_HEAD`，
`m10`/`m11` 两处逐字同构）；另有 `test_existing_selftests_regression` 出现**两种形态**（`m23`/`m24`
委派 `assert_regression`，`m26`–`m30` **内联同一循环**）——形态分叉本身即已发生的复刻漂移。

M31 把这两件收归 `selftest_kit.py` 的**唯一实现**（公共名 `number_independence_regression` / `entry`，
常量 `HEAD`）：② 消费点改为**本地同名薄包装**（守卫 + 恰一条委派），③ 改用 M30 已收口的
`assert_regression`（`m26`–`m30` 去掉内联循环），⑤ 走**同名别名绑定**（`entry as _entry`，零包装、零调用点改动）。

**实现期如实校正（以实测为准；笔三回写设计稿 / 路线图）**：
  * `test_full_regression_extra`（`m21`–`m23`）**保留不收口，不并入共享过程**——`m25` 的结构断言
    把「守卫总数」写死为 16（含该 3 处骨架的守卫），把守卫外移会使该计数塌缩；故此处只把
    「3 处骨架逐字同构」固化为**受检查的不变量**（复刻 → 登记 + 一致性断言）；
  * ③ **不动 `m23`/`m24`**——`m30` 的 ④ 断言 `selftest_m23._assert_regression is selftest_kit.assert_regression`
    与 `selftest_m24._assert_regression is …`，若改调共享过程会失去该引用而使判据失真；
  * 早退守卫**仍留消费端**（宿主**不**自持早退判定、也**不**读环境变量），故 `m25` 的
    「早退判定唯一归属」这一已固化不变量原样成立；③ 的两种调用拼写（本地名 / 公共名）**如实登记**。

**M37 口径收窄（以实测为准；笔三回写设计稿 / 路线图）**：「逐字同构」的真值由「**整段源码（含 docstring）**」
收窄为「**函数体（去 docstring）的原始源段**」——旧名 `_segment` 改名为新名 `_body_segment`（**改名而非同名
换语义**，避免同名绑定掩盖口径演进）。**代码**仍按**口径 A（原始源段逐字节相同）**比较（强判据**原样保留**，
未降级为 `ast.unparse`）；被**释放**的 **docstring** 改为**按模块登记真值**（`_DOC_TPL` / `_DOC_MARK` /
`_DOC_EXTRA`），从此各模块可**各自写对本模块标号**；`m35` / `m36` 两处被旧判据**锁坏**的标号如实按各自真值校正。

**自指防护**：本文件同样会被多份既有结构断言扫到，故所有待查特征串一律**分段拼接**构造
（`_D + "_" + _ENTRY + "("`、`"reversed(list(_REG" + "RESSION))"` …），使本文件源码**不**字面出现
这些特征串，避免把度量器自身算成假命中（与 M23 / M24 / M25 / M29 / M30 同法）。

覆盖（对应设计稿 §七 ①–⑧ 的实现期口径）：
  ① **唯一实现 + 旧写法收敛**：`number_independence_regression` / `entry` / `HEAD` 全仓各恰 1 处且在宿主；
     旧写法（本地渲染**定义**、局部常量、两处内联循环写法）全仓 0 处；各消费点已引用共享实现。
     其中「本地渲染定义 0 处」按 AST **定义处数**统计——`m30` 的登记表里本就写着该名字的字面量
     （那是**登记项**，不是第二份实现），按文本计数会把它误算成复刻；
  ② **值等价 + 绑定同源**：`entry` 与**独立参照公式**逐字同值（多组输入含中文 / 空锚）；`HEAD` 为写死的
     四行常量；`m10`/`m11` 的绑定**就是**共享实现（同一对象）；
  ③ **薄包装形态 + 逐字同构**：②/③ 的体恰为「守卫 + 单条委派」（AST 证据，已无内联循环）；
    ② 的 12 处、① 的 3 处**函数体（去 docstring）的原始源段逐字节相同**（M37 口径收窄后）；
    ③ 的两种调用拼写显式登记；docstring **不再**被逐字锁定，改为**按模块登记真值**（`_DOC_TPL` /
    `_DOC_MARK` / `_DOC_EXTRA`）；
  ④ **消费点已无本地复刻 + 登记项真值**：`m10`/`m11` 不再自持渲染实现；各测试名的**定义处数**按新真值登记
    （按 AST 统计定义，不受源码内字符串字面量干扰）；
  ⑤ **CLI 与退出码回归**：`drift` / `sync` / `impact` / `flow` / `view` 正常路径 stdout 与库输出
    **逐字节一致**、退出码 **0**、**无 `\\r\\n`**；错误 **1**；用法 **2**；
  ⑥ **只读 + 确定性**：`entry` 两次相同；`scanscope.*` 两次调用相同；同输入两次 CLI 逐字节一致；夹具摘要不变；
  ⑦ **既有自测零修订**：28 个无需参数的自测各按**实测**条数全绿（经 M30 唯一实现 `assert_regression`）；
  ⑧ **全域回归 + 编号无关性**：**逆序**跑同一批自测仍全绿（与 ⑦ 逐条一致）；需代码根者仍恰为 `m2` / `m3`。

沿用 M0–M30 约定：**不**用管道捕获输出，改临时文件重定向（本机沙箱禁建管道）——
本文件自身的脚手架调用一律经 `selftest_kit` 唯一实现，**不**内联子进程调用。
"""

from __future__ import annotations

import ast
import tempfile
from pathlib import Path

from . import drift, flow, impact_analyzer, scanscope, selftest_kit, sync, viewer
from . import selftest_m10, selftest_m11
from .selftest_kit import (
    PKG_DIR,
    assert_regression,
    cli as _cli,
    dir_digest as _dir_digest,
    entry,
    make_fixture as _fixture,
    number_independence_regression,
    ARG_EXEMPT as _ARG_EXEMPT,
    ARGV_MARK as _ARGV_MARK,
    KIT_NAME as _KIT,
    DEF_PREFIX as _D,
)

# 待查特征串**分段拼接**（见模块 docstring 的「自指防护」）：拼出的结果不在本文件源码中字面出现
_ENTRY = "entry"
_NIR = "number" + "_independence_regression"
_EXTRA = "test_full" + "_regression_extra"
_BOTH = "test_full" + "_regression_and_number_independence"
_EXIST = "test_existing" + "_selftests_regression"
_A_LOCAL = "_" + "assert" + "_regression"
_A_PUBLIC = "assert" + "_regression"
_IR = "in" + "_regression"

# ① 唯一实现：三个公共名 / 常量的**定义锚点**（全签名首行，避免多行签名被换行截断）
_SIG_NIR = _D + _NIR + "("
_SIG_ENTRY = _D + _ENTRY + "("
_SIG_HEAD = "HEAD" + " = ("

# ① 收口前的旧写法（应全仓 0 处）：本地渲染定义、局部常量、两处内联回归循环写法
_OLD_ENTRY = _D + "_" + _ENTRY + "("
_OLD_HEAD = "_HEAD" + " = ("
_OLD_ITEMS = "_REG" + "RESSION.items()"        # ③ 收口前的内联循环写法（`for mod, want in …items()`）
_OLD_REVERSE = "reversed(list(_REG" + "RESSION))"   # ② 收口前的内联逆序遍历写法

# M37 口径收窄：新旧名（均**分段拼接**，避免度量器自身字面命中）与两个口径的取证调用
_BODY_SEG = "_body" + "_segment"          # 收窄后的新名（口径 A：**函数体去 docstring**的原始源段）
_OLD_SEG = "_" + "segment"                # 收窄前的旧名（应收窄后全仓**定义 0 处 / 引用 0 处**）
_GET_SEG = "get_source" + "_segment"      # 口径 A 取证调用（`ast.get_source_segment`）
_UNPARSE = "un" + "parse"                 # 口径 B（仅作形态证据，**不**作「逐字同构」判据）

# ① 消费点「已引用共享实现」的特征串
_NIR_CALL = _NIR + "("
_ASSERT_CALL = _A_PUBLIC + "("
_BIND_ENTRY = _ENTRY + " as _" + _ENTRY

# ③ 名单与形态：② = 本地同名薄包装的 6 处；③ = 8 处；① = 明文**保留不收口**的 3 处
_CONSUMERS_2 = (
    "selftest_m26.py",
    "selftest_m27.py",
    "selftest_m28.py",
    "selftest_m29.py",
    "selftest_m30.py",
    "selftest_m31.py",
    "selftest_m32.py",
    "selftest_m33.py",
    "selftest_m34.py",
    "selftest_m35.py",
    "selftest_m36.py",
    "selftest_m37.py",
)
_CONSUMERS_3 = (
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
    "selftest_m34.py",
    "selftest_m35.py",
    "selftest_m36.py",
    "selftest_m37.py",
)
_CONSUMERS_5 = ("selftest_m10.py", "selftest_m11.py")
_KEPT_1 = ("selftest_m21.py", "selftest_m22.py", "selftest_m23.py")

# ③ 的**两种调用拼写**如实登记（`m23`–`m29` 用本地别名，`m30`–`m37` 用公共名）——
# 登记而非「统一改写法」：两种拼写都只是同一份共享实现的引用，改写法会碰到 `m30` ④ 的同一对象断言。
_SPELLING_3 = {
    "selftest_m23.py": _A_LOCAL,
    "selftest_m24.py": _A_LOCAL,
    "selftest_m26.py": _A_LOCAL,
    "selftest_m27.py": _A_LOCAL,
    "selftest_m28.py": _A_LOCAL,
    "selftest_m29.py": _A_LOCAL,
    "selftest_m30.py": _A_PUBLIC,
    "selftest_m31.py": _A_PUBLIC,
    "selftest_m32.py": _A_PUBLIC,
    "selftest_m33.py": _A_PUBLIC,
    "selftest_m34.py": _A_PUBLIC,
    "selftest_m35.py": _A_PUBLIC,
    "selftest_m36.py": _A_PUBLIC,
    "selftest_m37.py": _A_PUBLIC,
}
_UNPARSED_2 = f"{_NIR}(_REGRESSION, _ARGV_MARK, _ARG_EXEMPT)"
_UNPARSED_EXTRA = f"{_A_LOCAL}(_REGRESSION_EXTRA)"

# ④ 登记项：**测试名的定义处数**（按 AST 统计，不受源码内字符串字面量干扰）
_REGISTERED = (
    (_EXTRA, {"selftest_m21.py": 1, "selftest_m22.py": 1, "selftest_m23.py": 1}),
    (_BOTH, {name: 1 for name in _CONSUMERS_2}),
    (_EXIST, {name: 1 for name in _CONSUMERS_3}),
    ("_" + _ENTRY, {}),      # 本地渲染名已被收口为宿主唯一实现，故定义处数**应为 0**（真值更新，非放宽）
)

# ③（M37）docstring 的**按模块登记真值**：各处只有「两个标号」可不同，其余文字**逐字相同**；
# 键集必须**恰等于** `_CONSUMERS_2`——docstring 由此从「被逐字锁定的字面」改为「按模块登记的受检查真值」。
_DOC_TPL = "{own} 全域回归 + 编号无关性：逆序逐模块跑同一批自测仍全绿（与 {ref} 逐条一致）；需代码根者恰 m2/m3。"
_DOC_MARK = {
    "selftest_m26.py": ("⑧", "⑦"), "selftest_m27.py": ("⑧", "⑦"), "selftest_m28.py": ("⑧", "⑦"),
    "selftest_m29.py": ("⑧", "⑦"), "selftest_m30.py": ("⑧", "⑦"), "selftest_m31.py": ("⑧", "⑦"),
    "selftest_m32.py": ("⑧", "⑦"), "selftest_m33.py": ("⑧", "⑦"), "selftest_m34.py": ("⑧", "⑦"),
    "selftest_m35.py": ("⑩", "⑨"), "selftest_m36.py": ("⑩", "⑨"), "selftest_m37.py": ("⑧", "⑦"),
}
_DOC_EXTRA = "⑧ 全域回归（其余无需参数的自测）：按实测条数全绿。"

# ⑧ 的输入常量（`_ARGV_MARK` / `_ARG_EXEMPT`）已收归 `selftest_kit.py` 唯一实现（M32），经 M32 别名绑定导入


# --- ② 用的独立参照公式（**写死**在自测里，与共享实现逐字对照）-------------------------


def _ref_entry(cid: str, title: str, anchors: tuple[str, ...]) -> str:
    """参照公式：**独立实现**地按既定版式拼一条夹具记录（不复用 `HEAD`，故可作对照真值）。"""
    rows = [f"### {cid} — {title}"]
    rows += ["- type: 数据完整性", "- invariant: 示例不变量", "- change_control: free", "- severity: normal"]
    rows.append("- evidence:")
    rows += [f"  - {a}" for a in anchors]
    rows.append("- action_policy: 警告")
    return "\n".join(rows) + "\n"


# --- ③ 用的 AST 工具（只读）--------------------------------------------------------


def _func_node(name: str, func: str) -> ast.FunctionDef:
    """取某自测文件里名为 `func` 的**顶层**函数定义节点（未找到即失败，不作静默跳过）。"""
    tree = ast.parse((PKG_DIR / name).read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == func:
            return node
    raise AssertionError(f"{name} 未定义测试 {func}（收口后应仍存在该测试）")


def _body_without_doc(node: ast.FunctionDef) -> list[ast.stmt]:
    """函数体去掉文档串后的语句序列（守卫不改变 `__doc__`，故按**可执行语句**比对）。"""
    body = list(node.body)
    first = body[0] if body else None
    if (
        isinstance(first, ast.Expr)
        and isinstance(first.value, ast.Constant)
        and isinstance(first.value.value, str)
        and len(body) > 1
    ):
        body = body[1:]
    return body


def _is_guard(stmt: ast.stmt) -> bool:
    """是否为早退守卫：`if selftest_kit.in_regression(): return`（条件**恰是**该唯一判定调用）。"""
    if not isinstance(stmt, ast.If) or stmt.orelse:
        return False
    if len(stmt.body) != 1 or not isinstance(stmt.body[0], ast.Return) or stmt.body[0].value is not None:
        return False
    test = stmt.test
    return (
        isinstance(test, ast.Call)
        and isinstance(test.func, ast.Attribute)
        and test.func.attr == _IR
        and isinstance(test.func.value, ast.Name)
        and test.func.value.id == "selftest_kit"
        and not test.args
        and not test.keywords
    )


def _assert_wrapper(name: str, func: str, callee: str, unparsed: str) -> None:
    """③ 形态证据：体**恰**为「守卫 + 单条委派」；委派即共享过程调用、实参逐字为冻结快照 / 边界数据。"""
    body = _body_without_doc(_func_node(name, func))
    assert len(body) == 2, \
        f"{name}.{func} 的体应恰为「守卫 + 单条委派」2 步（内联循环已收敛），实际 {len(body)} 步"
    assert _is_guard(body[0]), f"{name}.{func} 首步应为早退守卫（经 selftest_kit 判定，不自行读环境变量）"
    step = body[1]
    assert isinstance(step, ast.Expr) and isinstance(step.value, ast.Call), \
        f"{name}.{func} 次步应恰为一条调用，实际 {ast.unparse(step)!r}"
    callee_node = step.value.func
    assert isinstance(callee_node, ast.Name) and callee_node.id == callee, \
        f"{name}.{func} 应委派 {callee}(…)，实际 {ast.unparse(step)!r}"
    assert ast.unparse(step) == unparsed, \
        f"{name}.{func} 的委派实参应逐字为 {unparsed!r}，实际 {ast.unparse(step)!r}"


def _body_segment(name: str, func: str) -> str:
    """取某测试函数的**函数体（去 docstring）的原始源段**（口径 A：逐字节），用于「逐字同构」的等价判定。

    M37 口径收窄：真值由「整段源码（含 docstring）」收窄为「函数体」——**代码**仍按口径 A 比较，
    被释放的 docstring 改由 `_DOC_TPL` / `_DOC_MARK` / `_DOC_EXTRA` 按模块登记并断言。
    """
    src = (PKG_DIR / name).read_text(encoding="utf-8")
    body = _body_without_doc(_func_node(name, func))
    return "\n".join(ast.get_source_segment(src, stmt) or "" for stmt in body)


def _doc_of(name: str, func: str) -> str:
    """取某测试函数的 **docstring 原文**（未清洗、逐字），用于「按模块登记真值」的比对（与 `_body_segment` 互补）。"""
    return ast.get_docstring(_func_node(name, func), clean=False) or ""


def _name_refs(name: str) -> dict[str, int]:
    """按 AST 统计「标识符 `name`（`ast.Name` 或属性名）的引用」的文件 → 处数（不受源码内字符串字面量干扰）。"""
    hits: dict[str, int] = {}
    for p in scanscope.all_modules():
        tree = ast.parse(p.read_text(encoding="utf-8"))
        n = sum(
            1
            for node in ast.walk(tree)
            if (isinstance(node, ast.Name) and node.id == name)
            or (isinstance(node, ast.Attribute) and node.attr == name)
        )
        if n:
            hits[p.name] = n
    return hits


def _def_files(func: str) -> dict[str, int]:
    """按 AST 统计「顶层函数定义名 = `func`」的文件 → 处数（不受源码内字符串字面量干扰）。"""
    hits: dict[str, int] = {}
    for p in scanscope.all_modules():
        tree = ast.parse(p.read_text(encoding="utf-8"))
        n = sum(1 for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == func)
        if n:
            hits[p.name] = n
    return hits


# --- ① 断言 ------------------------------------------------------------------------


def test_unique_implementation() -> None:
    """① 唯一实现 + 旧写法收敛：3 个公共名全仓各恰 1 处且在宿主；旧写法全仓 0 处；消费点已引用。"""
    for sig in (_SIG_NIR, _SIG_ENTRY, _SIG_HEAD):
        hits: dict[str, int] = {}
        for p in scanscope.all_modules():
            n = p.read_text(encoding="utf-8").count(sig)
            if n:
                hits[p.name] = n
        assert hits == {_KIT: 1}, f"公共实现应全仓恰 1 处且位于 {_KIT}：{sig!r} → {hits}"

    # 本地渲染定义的「0 处」按**定义**统计而非文本统计：`m30` 的登记表里本就写着该名字的字面量
    # （那是**登记项**，不是第二份实现）——按文本计数会把它误算成复刻（与 M30 的「全签名按定义计」同口径）
    entry_defs = _def_files("_" + _ENTRY)
    assert entry_defs == {}, f"本地渲染定义应全仓 0 处（按定义统计）：{entry_defs}"

    # M37 口径收窄：旧名应收窄后全仓**定义 0 处 / 引用 0 处**。按 **AST** 统计而非文本计数——
    # 新名 `_body_segment` 与旧名 `_segment` 有子串包含关系，文本计数会把新名误算成旧名命中。
    old_defs = _def_files(_OLD_SEG)
    assert old_defs == {}, f"收窄前旧名应全仓定义 0 处（按 AST）：{old_defs}"
    old_refs = _name_refs(_OLD_SEG)
    assert old_refs == {}, f"收窄前旧名应全仓引用 0 处（按 AST）：{old_refs}"

    # 强判据未降级：`_body_segment` 体内**恰 1** 处口径 A（`ast.get_source_segment`）、**零**处口径 B（`ast.unparse`）
    seg_node = _func_node("selftest_m31.py", _BODY_SEG)
    n_a = sum(1 for n in ast.walk(seg_node) if isinstance(n, ast.Attribute) and n.attr == _GET_SEG)
    n_b = sum(1 for n in ast.walk(seg_node) if isinstance(n, ast.Attribute) and n.attr == _UNPARSE)
    assert (n_a, n_b) == (1, 0), \
        f"`{_BODY_SEG}` 体内应恰 1 处口径 A（`{_GET_SEG}`）、0 处口径 B（`{_UNPARSE}`），实际 {(n_a, n_b)}"

    for sig in (_OLD_HEAD, _OLD_ITEMS, _OLD_REVERSE):
        hits = {}
        for p in scanscope.all_modules():
            n = p.read_text(encoding="utf-8").count(sig)
            if n:
                hits[p.name] = n
        assert hits == {}, f"收口前的旧写法应全仓 0 处：{sig!r} → {hits}"

    for name in _CONSUMERS_2:
        assert _NIR_CALL in (PKG_DIR / name).read_text(encoding="utf-8"), \
            f"{name} 未引用共享过程 {_NIR}(…)"
    for name in _CONSUMERS_3:
        assert _ASSERT_CALL in (PKG_DIR / name).read_text(encoding="utf-8"), \
            f"{name} 未引用共享断言 {_ASSERT_CALL}…"
    for name in _CONSUMERS_5:
        assert _BIND_ENTRY in (PKG_DIR / name).read_text(encoding="utf-8"), f"{name} 未绑定「{_BIND_ENTRY}」"


# --- ② 断言 ------------------------------------------------------------------------


def test_value_equivalence() -> None:
    """② 值等价 + 绑定同源：`entry` 与独立参照公式逐字同值；`HEAD` 为写死四行；m10/m11 绑定即共享实现。"""
    assert selftest_m10._entry is selftest_kit.entry, "m10 的记录渲染应绑定共享实现（同一对象）"
    assert selftest_m11._entry is selftest_kit.entry, "m11 的记录渲染应绑定共享实现（同一对象）"

    expected_head = (
        "- type: 数据完整性\n"
        "- invariant: 示例不变量\n"
        "- change_control: free\n"
        "- severity: normal\n"
    )
    assert selftest_kit.HEAD == expected_head, f"HEAD 应为写死的四行常量，实际 {selftest_kit.HEAD!r}"

    samples = (
        ("SY-001", "精确锚 core.py", ("src/app/core.py",)),
        ("OK-002", "前缀锚 docs/", ("docs/",)),
        ("X-003", "无斜杠锚", ("just-a-token",)),
        ("A-004", "空锚集合", ()),
        ("条目", "中文标题", ("证据 原文", "second/anchor")),
    )
    for cid, title, anchors in samples:
        assert entry(cid, title, anchors) == _ref_entry(cid, title, anchors), \
            f"entry 与参照公式不一致：{cid!r} / {title!r} / {anchors!r}"

    first = entry("SY-001", "精确锚 core.py", ("src/app/core.py",))
    assert first == entry("SY-001", "精确锚 core.py", ("src/app/core.py",)), "同类输入两次应逐字相同"


# --- ③ 断言 ------------------------------------------------------------------------


def test_thin_wrapper_shape() -> None:
    """③ 薄包装形态 + 逐字同构：体恰为「守卫 + 单条委派」；② 12 处、① 3 处**函数体**源段逐字节相同；
    docstring 按模块登记真值；拼写已登记。"""
    assert set(_SPELLING_3) == set(_CONSUMERS_3), \
        f"③ 的调用拼写登记应与消费文件名单一一对应，实际 {sorted(_SPELLING_3)} vs {sorted(_CONSUMERS_3)}"

    for name in _CONSUMERS_2:
        _assert_wrapper(name, _BOTH, _NIR, _UNPARSED_2)
    segs_2 = {_body_segment(name, _BOTH) for name in _CONSUMERS_2}
    assert len(segs_2) == 1, \
        f"② 的 {len(_CONSUMERS_2)} 处骨架应逐字同构（**函数体**原始源段逐字节相同），实际 {len(segs_2)} 种"

    for name in _CONSUMERS_3:
        _assert_wrapper(name, _EXIST, _SPELLING_3[name], f"{_SPELLING_3[name]}(_REGRESSION)")

    # ① `test_full_regression_extra` **保留不收口**：仍委派 `assert_regression(_REGRESSION_EXTRA)`，未改接线到共享过程
    for name in _KEPT_1:
        _assert_wrapper(name, _EXTRA, _A_LOCAL, _UNPARSED_EXTRA)
    segs_1 = {_body_segment(name, _EXTRA) for name in _KEPT_1}
    assert len(segs_1) == 1, f"① 的 {len(_KEPT_1)} 处骨架应逐字同构，实际 {len(segs_1)} 种"

    # M37 ①：收窄后的「函数体」串**不含**任何 docstring 标号字符——直接证据：docstring 已不参与判据
    for seg in segs_2 | segs_1:
        assert "⑧" not in seg and "⑩" not in seg, \
            f"收窄后的「函数体」串不得含 docstring 标号字符，实际 {seg!r}"

    # M37 ③：docstring 由「被逐字锁定的字面」改为「**按模块登记真值**」——键集恰等消费名单，逐条逐字比对
    assert set(_DOC_MARK) == set(_CONSUMERS_2), \
        f"`_DOC_MARK` 键集应恰等消费名单，实际 {sorted(_DOC_MARK)} vs {sorted(_CONSUMERS_2)}"
    for name in _CONSUMERS_2:
        own, ref = _DOC_MARK[name]
        want = _DOC_TPL.format(own=own, ref=ref)
        assert _doc_of(name, _BOTH) == want, \
            f"{name}.{_BOTH} 的 docstring 应逐字为该模块真值，实际 {_doc_of(name, _BOTH)!r}"
    for name in _KEPT_1:
        assert _doc_of(name, _EXTRA) == _DOC_EXTRA, \
            f"{name}.{_EXTRA} 的 docstring 应逐字为 {_DOC_EXTRA!r}，实际 {_doc_of(name, _EXTRA)!r}"
    marks = {v[0] for v in _DOC_MARK.values()}
    assert len(marks) >= 2, f"docstring 首标号应实测至少 2 组（锁定已释放），实际 {sorted(marks)}"


# --- ④ 断言 ------------------------------------------------------------------------


def test_consumers_pruned_and_registered() -> None:
    """④ 消费点已无本地复刻 + 登记项真值：m10/m11 不再自持渲染实现；各测试名定义处数按新真值登记。"""
    for name in _CONSUMERS_5:
        src = (PKG_DIR / name).read_text(encoding="utf-8")
        assert _OLD_ENTRY not in src, f"{name} 仍自持本地渲染定义（应收口为共享引用）"
        assert _OLD_HEAD not in src, f"{name} 仍自持局部常量（应收口为共享常量）"
        assert _BIND_ENTRY in src, f"{name} 未绑定「{_BIND_ENTRY}」"

    for func, want in _REGISTERED:
        hits = _def_files(func)
        assert hits == want, f"登记项应恰按新真值存在（按定义统计）：{func!r} → {hits}"


# --- ⑤ / ⑥ 用的夹具数据（本模块自己的三份；与其余自测同形，仅题头不同）------------------


_DESIGN = (
    "# 夹具设计文档（M31 自测专用）\n"
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
    "# 流程夹具（M31 自测专用）\n"
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
        root, design, flow_doc, diffs = _fixture(
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
    """⑥ 只读 + 确定性：`entry` 两次相同；scanscope 两次相同；同输入两次 CLI 逐字节一致；夹具摘要不变。"""
    with tempfile.TemporaryDirectory() as td:
        td_p = Path(td)
        root, design, _flow_doc, _diffs = _fixture(
            td_p, design_text=_DESIGN, flow_text=_FLOW, changes=_CHANGES
        )
        before = _dir_digest(td_p)

        assert entry("SY-001", "精确锚 core.py", ("src/app/core.py",)) == \
            entry("SY-001", "精确锚 core.py", ("src/app/core.py",)), "共享渲染两次调用应逐字相同"
        assert scanscope.all_modules() == scanscope.all_modules(), "all_modules 两次调用应相同"
        assert scanscope.selftest_modules() == scanscope.selftest_modules(), "selftest_modules 两次调用应相同"

        first = _cli("drift", str(root), str(design))
        second = _cli("drift", str(root), str(design))
        assert first == second, "同输入两次 CLI（退出码 / stdout / stderr）应逐字节一致"
        assert first[0] == 0, f"drift 正常路径应退出码 0，实际 {first[0]}；stderr={first[2][-200:]!r}"

        assert _dir_digest(td_p) == before, "全过程不得写夹具中的任何一个字节"


# --- ⑦ / ⑧ 28 个无需命令行参数的自测（`m2` / `m3` 需代码根，见 ⑧）；条数为**实测** ------------


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
}


def test_existing_selftests_regression() -> None:
    """⑦ 既有自测零修订：28 个无需参数的自测各按实测条数全绿（经共享 `assert_regression`）。"""
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
        test_thin_wrapper_shape,
        test_consumers_pruned_and_registered,
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
