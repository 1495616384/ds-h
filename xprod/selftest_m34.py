"""M34 自测：把「自测目录树摊平」的唯一实现收口，并固化 §一 的**收口链收敛裁定**。

背景（`X产品化-M34设计稿-v1.md` §一；实现期以**实测**为准）：把目录树摊成
`(相对路径, 内容)` 列表的**只读对照工具**此前由 `m28` 建「最小代码根」时引入、又被 `m29` 建
「全套夹具」时**逐字节复制**一份（2 处 1 组、无唯一归属）。M34 把它收归 `selftest_kit.py`
**唯一实现**（公共名 `tree_files`）：消费端 `m28` / `m29` 删除本地同名函数定义、在既有
`from .selftest_kit import …` 中**追加同名别名绑定**——输入只有 `root: Path`、**不随模块变化**，
故走 M24 / M27 式**零包装、零调用点改动**。

**裁定（本里程碑的独立结论）**：除该项外，§一 1.2 的**其余 5 项**虽逐字同构但**不可收口**，
本文件 ③ 按**显式名单**登记——差异核心夹具常量（`{m12, m13}`）、自指防护拼接常量（`{m31, m32}`）、
入口常量与入口函数（`{m2, m3}`）、两处 M31 明文既定形态遍历骨架（`{m21–m23}`、`{m26–m34}`）。
登记按 **AST 名字**统计（不受源码内字符串字面量干扰），从而**以证据宣告收口链（M24–M34）收敛**。
（本文件自身按既定形态自持后者之一，故该组登记为 **post-M34 真值** `{m26–m34}`；§一 1.2 在
post-M33 树上实测为 `{m26–m33}`，口径校正见笔三。）

**自指防护**：本文件同样会被多份既有结构断言扫到，故所有待查特征串一律**分段拼接**构造
（`"tree" + "_files"`、`"_DIFF" + "_CORE"`、`"_" + "NIR"`、`"R" + "OOT"` …），使本文件源码
**不**字面出现这些特征串（与 M23–M33 同法）。

覆盖（对应设计稿 §七 ①–⑧）：
  ① **唯一实现 + 旧写法收敛**：公共名全签名定义全仓恰 1 处且在宿主；自测文件中本地同名函数定义 0 处；
  ② **值等价 + 消费者自洽**：共享实现与 `m28` / `m29` 的绑定在临时目录上**逐字节同值**，
     且均与**独立参照公式**同值；`PKG_DIR` 仍可解析、宿主文件仍在；
  ③ **绑定同源 + 裁定登记**：`m28` / `m29` 的绑定与宿主**同一对象**；§一 1.2 的 5 项不收口裁定
     按**显式名单**登记（AST 口径）；
  ④ **调用点未改**：`m28` / `m29` 内该工具的调用点与收口前**逐字相同**（对照写死的表达式清单）；
  ⑤ **既有断言仍成立**：`m24` ④、`m25` ①②、`m26`–`m32` 唯一实现与消费点断言、`m30` ③、
     `m31` ①③、`m33` ①③ 全绿；
  ⑥ **只读 + 确定性**：夹具复合摘要不变；`scanscope.*` 两次调用逐条相同；同输入两次该工具同值；
  ⑦ **既有自测零修订**：31 个无需参数的自测各按**实测**条数全绿（经共享 `assert_regression`）；
  ⑧ **全域回归 + 编号无关性**：**逆序**跑同一批自测仍全绿（与 ⑦ 逐条一致）；需代码根者仍恰为 `m2` / `m3`。

沿用 M0–M33 约定：**不**用管道捕获输出，改临时文件重定向（本机沙箱禁建管道）——
本文件自身的脚手架调用一律经 `selftest_kit` 唯一实现，**不**内联子进程调用。
"""

from __future__ import annotations

import ast
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
    selftest_m33,
)
from .selftest_kit import (
    PKG_DIR,
    assert_regression,
    dir_digest as _dir_digest,
    make_min_root as _make_root,
    number_independence_regression,
    ARG_EXEMPT as _ARG_EXEMPT,
    ARGV_MARK as _ARGV_MARK,
    DEF_PREFIX as _D,
)

# --- 待查特征串**分段拼接**（见模块 docstring 的「自指防护」）：拼出的结果不在本文件源码中字面出现 ----
_TREE = "tree" + "_files"                      # 本轮收口的公共名
_SIG_TREE = _D + _TREE + "(root: Path) -> list[tuple[str, str]]:"   # ① 公共名全签名（定义锚点）
_OLD_TREE = _D + "_" + _TREE + "("             # ① 收口前的本地同名函数定义（应收口后全仓 0 处）

# ③ 登记用的 5 项**不收口**名字（AST 口径：函数名按顶层定义、常量名按顶层赋值）
_N_DIFF = "_DIFF" + "_CORE"                    # 差异核心夹具常量（`m12` / `m13` 各自的输入样本）
_N_NIR_CONST = "_" + "NIR"                     # 自指防护拼接常量（`m31` / `m32`）
_N_ROOT = "R" + "OOT"                          # 入口常量（连同入口函数，`m2` / `m3`）
_N_EXTRA = "test_full" + "_regression_extra"   # M31 明文保留不收口的遍历骨架（`m21`–`m23`）
_N_BOTH = "test_full" + "_regression" + "_and_number" + "_independence"   # 同上（`m26`–`m34`）

# ② 参照清单：**独立写死**的「最小代码根」文件清单（不复用共享夹具构造，故可作对照真值）
_REF_FILES = (
    ("src/app/__init__.py", ""),
    ("src/app/api.py", "from app.core import X\nA = 0\n"),
    ("src/app/core.py", "X = 1\n"),
    ("src/app/notify.py", "N = 1\n"),
    ("docs/guide.md", "# 指南\n"),
    ("docs/spec.md", "# 规格\n"),
)

# ③ 5 项不收口裁定的**显式名单**（`_N_BOTH` 真值随里程碑推进至 `{m26–m37}`，含本文件 `selftest_m34.py`）
_KEPT_DIFF = ("selftest_m12.py", "selftest_m13.py")
_KEPT_NIR = ("selftest_m31.py", "selftest_m32.py")
_KEPT_ROOT = ("selftest_m2.py", "selftest_m3.py")
_KEPT_EXTRA = ("selftest_m21.py", "selftest_m22.py", "selftest_m23.py")
_KEPT_BOTH = tuple("selftest_m%d.py" % i for i in range(26, 38))

# ④ 调用点真值清单（**逐字写死**，收口前后相同；表达式而非处数）
_CALLPOINTS = (
    ("selftest_m28.py", (
        "_tree_files(got) == _tree_files(ref)",
        'ref = _tree_files(_ref_make_root(td / "ref"))',
        "got = _tree_files(mod._make_root(td / tag))",
    )),
    ("selftest_m29.py", (
        "_tree_files(got[0]) == _tree_files(ref[0])",
    )),
)


# --- ② / ③ 用的只读 AST 与参照工具 -------------------------------------------------


def _ref_tree_files(root: Path) -> list[tuple[str, str]]:
    """参照公式：**独立实现**地把目录树摊成 `(相对路径, 内容)` 列表（不复用共享实现，故可作对照真值）。"""
    out: list[tuple[str, str]] = []
    for q in root.rglob("*"):
        if q.is_file():
            out.append((q.relative_to(root).as_posix(), q.read_bytes().decode("utf-8")))
    return sorted(out, key=lambda pair: pair[0])


def _def_files(func: str) -> dict[str, int]:
    """按 AST 统计「顶层函数定义名 = `func`」的文件 → 处数（不受源码内字符串字面量干扰）。"""
    hits: dict[str, int] = {}
    for p in scanscope.all_modules():
        tree = ast.parse(p.read_text(encoding="utf-8"))
        n = sum(1 for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == func)
        if n:
            hits[p.name] = n
    return hits


def _assign_files(name: str) -> dict[str, int]:
    """按 AST 统计「顶层赋值目标名 = `name`」的文件 → 处数（同一口径，避开源码内字符串干扰）。"""
    hits: dict[str, int] = {}
    for p in scanscope.all_modules():
        tree = ast.parse(p.read_text(encoding="utf-8"))
        n = sum(
            1
            for node in tree.body
            if isinstance(node, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == name for t in node.targets)
        )
        if n:
            hits[p.name] = n
    return hits


# --- ① 断言 ------------------------------------------------------------------------


def test_unique_implementation() -> None:
    """① 唯一实现 + 旧写法收敛：公共名全签名全仓恰 1 处且在宿主；本地同名函数定义全仓 0 处。"""
    hits: dict[str, int] = {}
    for p in scanscope.all_modules():
        n = p.read_text(encoding="utf-8").count(_SIG_TREE)
        if n:
            hits[p.name] = n
    assert hits == {selftest_kit.KIT_NAME: 1}, \
        f"公共名全签名应全仓恰 1 处且位于宿主：{_SIG_TREE!r} → {hits}"

    old: dict[str, int] = {}
    for p in scanscope.selftest_modules():
        n = p.read_text(encoding="utf-8").count(_OLD_TREE)
        if n:
            old[p.name] = n
    assert old == {}, f"自测文件中不得再定义本地同名函数（应收口为共享引用）：{_OLD_TREE!r} → {old}"


# --- ② 断言 ------------------------------------------------------------------------


def test_value_equivalence() -> None:
    """② 值等价 + 消费者自洽：共享实现与独立参照公式逐字节同值；`m28` / `m29` 的绑定同值。"""
    assert PKG_DIR.is_dir(), f"包目录应为存在目录，实际 {PKG_DIR}"
    assert (PKG_DIR / selftest_kit.KIT_NAME).is_file(), "包目录内应含唯一实现宿主文件"

    with tempfile.TemporaryDirectory() as td_s:
        root = _make_root(Path(td_s) / "root")
        ref = _ref_tree_files(root)
        assert ref, "参照公式应至少产出 1 条记录（否则该断言为空真）"
        assert selftest_kit.tree_files(root) == ref, "共享实现应与独立参照公式逐字节同值"
        assert selftest_m28._tree_files(root) == ref, "m28 的绑定应与独立参照公式逐字节同值"
        assert selftest_m29._tree_files(root) == ref, "m29 的绑定应与独立参照公式逐字节同值"


# --- ③ 断言 ------------------------------------------------------------------------


def test_binding_identity_and_rulings_registered() -> None:
    """③ 绑定同源 + 裁定登记：两处绑定与宿主同一对象；5 项不收口裁定按显式名单登记（AST 口径）。"""
    assert selftest_m28._tree_files is selftest_kit.tree_files, \
        "m28 的绑定应指向宿主同一对象（别名绑定而非本地复刻）"
    assert selftest_m29._tree_files is selftest_kit.tree_files, \
        "m29 的绑定应指向宿主同一对象（别名绑定而非本地复刻）"

    assert _assign_files(_N_DIFF) == {name: 1 for name in _KEPT_DIFF}, \
        f"差异核心夹具常量应原样保留（不收口）：实际 {_assign_files(_N_DIFF)}"
    assert _assign_files(_N_NIR_CONST) == {name: 1 for name in _KEPT_NIR}, \
        f"自指防护拼接常量应原样保留（不收口）：实际 {_assign_files(_N_NIR_CONST)}"
    assert _assign_files(_N_ROOT) == {name: 1 for name in _KEPT_ROOT}, \
        f"入口常量应原样保留（不收口）：实际 {_assign_files(_N_ROOT)}"
    assert _def_files(_N_EXTRA) == {name: 1 for name in _KEPT_EXTRA}, \
        f"既定形态遍历骨架应原样保留（不收口）：实际 {_def_files(_N_EXTRA)}"
    assert _def_files(_N_BOTH) == {name: 1 for name in _KEPT_BOTH}, \
        f"既定形态遍历骨架应原样保留（不收口）：实际 {_def_files(_N_BOTH)}"


# --- ④ 断言 ------------------------------------------------------------------------


def test_callpoints_unchanged() -> None:
    """④ 调用点未改：`m28` / `m29` 内的调用点表达式与收口前**逐字相同**（对照写死的清单）。"""
    for name, exprs in _CALLPOINTS:
        src = (PKG_DIR / name).read_text(encoding="utf-8")
        for expr in exprs:
            assert expr in src, f"{name} 的调用点应逐字保留，实际缺失：{expr!r}"


# --- ⑤ 断言 ------------------------------------------------------------------------


def test_existing_assertions_still_green() -> None:
    """⑤ 既有断言仍成立：m24 ④、m25 ①②、m26–m32 唯一实现与消费点、m30 ③、m31 ①③、m33 ①③ 全绿。"""
    selftest_m24.test_consumers_no_local_replication()
    selftest_m25.test_in_regression_single_source()
    selftest_m25.test_guard_shape()
    selftest_m26.test_unique_implementation()
    selftest_m27.test_unique_implementation()
    selftest_m28.test_unique_implementation()
    selftest_m28.test_consumers_pruned_and_variants_registered()
    selftest_m29.test_unique_implementation()
    selftest_m29.test_consumers_pruned_and_variants_registered()
    selftest_m30.test_unique_implementation()
    selftest_m30.test_consumers_pruned_and_registered()
    selftest_m31.test_unique_implementation()
    selftest_m31.test_thin_wrapper_shape()
    selftest_m31.test_consumers_pruned_and_registered()
    selftest_m32.test_unique_implementation()
    selftest_m33.test_unique_implementation()
    selftest_m33.test_binding_identity_and_changes_registered()


# --- ⑥ 只读 + 确定性 ---------------------------------------------------------------


def test_read_only_and_determinism() -> None:
    """⑥ 只读 + 确定性：夹具复合摘要不变；`scanscope.*` 两次调用逐条相同；同输入两次该工具同值。"""
    with tempfile.TemporaryDirectory() as td:
        td_p = Path(td)
        root = _make_root(td_p / "root")
        before = _dir_digest(td_p)

        assert scanscope.all_modules() == scanscope.all_modules(), "all_modules 两次调用应相同"
        assert scanscope.selftest_modules() == scanscope.selftest_modules(), \
            "selftest_modules 两次调用应相同"

        first = selftest_kit.tree_files(root)
        second = selftest_kit.tree_files(root)
        assert first == second, "同输入两次该工具应逐字节同值"
        assert first == _ref_tree_files(root), "读取结果应与独立参照公式同值"

        assert _dir_digest(td_p) == before, "全过程不得写夹具中的任何一个字节"


# --- ⑦ / ⑧ 31 个无需命令行参数的自测（`m2` / `m3` 需代码根，见 ⑧）；条数为**实测** ------------


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
    "selftest_m33": "8/8",
}


def test_existing_selftests_regression() -> None:
    """⑦ 既有自测零修订：31 个无需参数的自测各按实测条数全绿（经共享 `assert_regression`）。"""
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
        test_binding_identity_and_rulings_registered,
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
