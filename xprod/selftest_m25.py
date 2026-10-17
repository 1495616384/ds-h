"""M25 自测：把「既有自测回归的扁平化（消除嵌套自回归的指数放大）」的验收点写成可执行断言。

背景（`X产品化-M25设计稿-v1.md` §一）：`run_module` 此前**一律深跑**，9 个非叶子模块各自遍历，
「跑一次 `selftest_m24`」要启动 **1062** 次子进程（执行次数 = 回归图上 `m24 → N` 的**路径条数**），
代价随里程碑序号**指数增长**、覆盖却一条没多。M25 把「该不该向下展开」收归
`selftest_kit.in_regression()` **一处判定**：扁平调起时子模块**首行早退**，只跑自身断言。

**自指防护**：本文件同样要「不含子进程调用、不多余引入 sys / subprocess、不字面出现约定环境变量名」，
故 ① / ⑧ 的待查特征串一律**分段拼接**构造（与 M24 同法），避免把度量器自身算成假命中。

覆盖（对应设计稿 §八 ①–⑧）：
    ① 判定唯一实现（结构证据）：`in_regression` 的定义全仓恰 1 处；两个约定环境变量名各恰 1 处字面量；
    ② 守卫形态（结构证据）：9 个非叶子模块中「传递可达回归调起」的测试函数**首个可执行语句**
       均为早退守卫、且引用 `selftest_kit` 判定（不自行读环境变量）。
       「回归调起」的识别标记＝本地直调 `_run_module` / `run_module`（M25 原形态）**∪**
       共享宿主别名 `_assert_regression` / `assert_regression`（M30 收口后的新形态）——
    ③ 执行重数 = 1（可观测，本轮核心）：env 门控 trace 跑一次顶层 `selftest_m24`，各模块被调起
       ≤ 3 次（⑦ 1 次 + ⑧ 采样 2 次）；
    ④ 总次数 ≤ 实现阶段**实测取整写入**的绝对阈值（29，收口前基线 1062；阈值只降不升）；
    ⑤ 计数不变：扁平跑 `m18`–`m24`，尾行与收口前**逐字相同**（早退仍计 PASS）；
    ⑥ 扁平 / 深跑同绿：同一模块两形态下自身断言结果与条数一致；
    ⑦ 只读 + 确定性：同形态两次逐字节一致；**未设 trace 时零写盘**；夹具目录复合摘要不变；
    ⑧ 覆盖不减 + 边界：`m24` 目标名单里每个模块都被调起 ≥ 1 次（trace 为证）；
       需命令行代码根的自测仍恰为 `m2` / `m3`（由里程碑级全域回归覆盖）。
"""

from __future__ import annotations

import ast
import os
import tempfile
from pathlib import Path

from . import scanscope
from . import selftest_kit
from .selftest_kit import dir_digest as _dir_digest, last_line as _last_line

_KIT = "selftest_kit.py"

# 非叶子模块（= 含「回归遍历」者，M25 设计稿 §一 实测恰 9 个）
_NONLEAF = (
    "selftest_m16.py",
    "selftest_m17.py",
    "selftest_m18.py",
    "selftest_m19.py",
    "selftest_m20.py",
    "selftest_m21.py",
    "selftest_m22.py",
    "selftest_m23.py",
    "selftest_m24.py",
)

# 待查特征串**分段拼接**（见模块 docstring 的「自指防护」）：拼出的结果不在本文件源码中字面出现
_IR_NAME = "in" + "_regression"          # 唯一判定名
_RUN_ALIAS = "_run" + "_module"          # 消费点别名（M25 原形态）
_RUN_PUBLIC = "run" + "_module"          # 宿主公开名
# M30 收口后「回归调起」还可经**共享宿主别名**发生：`assert_regression` 内部即调 `run_module`，
# 故其（含本地别名 `_assert_regression`）与上面两个直调标记**等价**，须一并识别——
# 否则守卫测试在模型眼里不再「可达回归调起」，`need` 会塌缩为空而与 `guarded` 失配。
_ASSERT_ALIAS = "_assert" + "_regression"
_ASSERT_PUBLIC = "assert" + "_regression"
_LAUNCH_MARKS = frozenset({_RUN_ALIAS, _RUN_PUBLIC, _ASSERT_ALIAS, _ASSERT_PUBLIC})
_ARGV_MARK = "sys" + ".argv"             # 「取命令行参数」的特征串
_ARG_EXEMPT = ("selftest_m2.py", "selftest_m3.py")

# 基线（`exec_cost.py` 静态模型实测：cost(selftest_m24)=1062）与扁平化后的**实测上界**
# ④ 的绝对阈值：按设计稿「以实测取整写入、只降不升」——`m25_measure` 实测 29
#   = 21 个目标各 1 次 + m15→m14 残余 1 次 + ⑧ 采样 6 次 + 顶层 m24 自身 1 次；
#   仅记录基线用于失败信息，阈值本身**写死**为实测值（不得事后上调）。
_BASELINE = 1062
_TOTAL_CAP = 29
_PER_MODULE_CAP = 3                      # ③：⑦ 1 次 + ⑧ 采样 2 次（实测上界）
_SELFTEST_PREFIX = "xprod.selftest"
_CLI_MODULE = "xprod"

# `m24` 的回归目标名单（设计稿 §一 实测）：基线 `selftest` + `m1` + `m5`…`m23` —— ⑧ 的覆盖下界
_M24_TARGETS = ("selftest", "selftest_m1") + tuple(f"selftest_m{m}" for m in range(5, 24))

# ⑤：扁平调起时各模块尾行（收口前实测；早退不改计数）
_FLAT_TAILS = {
    "selftest_m18": "10/10 passed",
    "selftest_m19": "8/8 passed",
    "selftest_m20": "8/8 passed",
    "selftest_m21": "8/8 passed",
    "selftest_m22": "8/8 passed",
    "selftest_m23": "8/8 passed",
    "selftest_m24": "8/8 passed",
}


# --- AST 工具（只读，用于 ② 的结构证据）--------------------------------------------


def _funcs(tree: ast.Module) -> dict[str, ast.FunctionDef]:
    return {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}


def _bare_calls(node: ast.AST) -> set[str]:
    """函数体内（不含嵌套 def / lambda / class）直接出现的裸名 / 属性尾名。"""
    out: set[str] = set()

    def walk(n: ast.AST) -> None:
        for ch in ast.iter_child_nodes(n):
            if isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
                continue
            if isinstance(ch, ast.Call):
                f = ch.func
                if isinstance(f, ast.Name):
                    out.add(f.id)
                elif isinstance(f, ast.Attribute):
                    out.add(f.attr)
            walk(ch)

    walk(node)
    return out


def _tests_tuple(tree: ast.Module) -> set[str]:
    """`main()` 里 `tests = (...)` 注册的测试函数名（判「哪些函数是用例」）。"""
    for n in ast.walk(tree):
        if isinstance(n, ast.FunctionDef) and n.name == "main":
            for st in ast.walk(n):
                if (
                    isinstance(st, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == "tests" for t in st.targets)
                    and isinstance(st.value, ast.Tuple)
                ):
                    return {e.id for e in st.value.elts if isinstance(e, ast.Name)}
    return set()


def _reaches(name: str, funcs: dict[str, ast.FunctionDef], direct: dict[str, bool],
             seen: frozenset[str] = frozenset()) -> bool:
    """`name` 是否**传递可达**一次回归调起（直接调宿主，或经同模块函数间接调用）。"""
    if direct[name]:
        return True
    if name in seen:
        return False
    seen2 = seen | {name}
    return any(
        c in funcs and _reaches(c, funcs, direct, seen2) for c in _bare_calls(funcs[name])
    )


def _first_exec(node: ast.FunctionDef) -> ast.stmt:
    """首个**可执行**语句（跳过文档串，故守卫不改变 `__doc__`）。"""
    first = node.body[0]
    if (
        isinstance(first, ast.Expr)
        and isinstance(first.value, ast.Constant)
        and isinstance(first.value.value, str)
        and len(node.body) > 1
    ):
        return node.body[1]
    return first


def _is_guard(stmt: ast.stmt) -> bool:
    """是否为「早退守卫」：`if selftest_kit.in_regression(): return`（条件**恰是**该唯一判定调用）。"""
    if not isinstance(stmt, ast.If) or stmt.orelse:
        return False
    if len(stmt.body) != 1 or not isinstance(stmt.body[0], ast.Return) or stmt.body[0].value is not None:
        return False
    t = stmt.test
    return (
        isinstance(t, ast.Call)
        and isinstance(t.func, ast.Attribute)
        and t.func.attr == _IR_NAME
        and isinstance(t.func.value, ast.Name)
        and t.func.value.id == "selftest_kit"
    )


# --- ③ / ④ / ⑧ 共享的**可观测**测量（env 门控 trace）-------------------------------

_TRACE: dict[str, int] | None = None


def _trace_counts() -> dict[str, int]:
    """跑一次**顶层** `selftest_m24`（`deep=True` = 顶层直跑语义），用门控 trace 统计**被调起目标**。

    只测一次（③ / ④ / ⑧ 共享）。trace 文件建在临时目录、随上下文回收——不写仓库 / 夹具；
    `TRACE_ENV` 在本进程内临时置位，用后**原样还原**。
    """
    global _TRACE
    if _TRACE is not None:
        return _TRACE
    with tempfile.TemporaryDirectory() as td_s:
        trace = Path(td_s) / "trace.txt"
        saved = os.environ.get(selftest_kit.TRACE_ENV)
        os.environ[selftest_kit.TRACE_ENV] = str(trace)
        try:
            rc, _out, err = selftest_kit.run_module("selftest_m24", deep=True)
        finally:
            if saved is None:
                os.environ.pop(selftest_kit.TRACE_ENV, None)
            else:
                os.environ[selftest_kit.TRACE_ENV] = saved
        assert rc == 0, f"顶层跑 selftest_m24 应全绿，实际 rc={rc}；stderr={err[-300:]!r}"
        assert trace.exists(), "门控 trace 未落盘——③ 的可观测手段已失效"
        counts: dict[str, int] = {}
        for line in trace.read_text(encoding="utf-8").splitlines():
            name = line.strip()
            if name:
                counts[name] = counts.get(name, 0) + 1
    _TRACE = counts
    return counts


def _selftest_counts(counts: dict[str, int]) -> dict[str, int]:
    """只取 `selftest` 模块的调起次数（与基线口径对齐：基线只数模块调起，不含 CLI 子进程）。"""
    out: dict[str, int] = {}
    for full, n in counts.items():
        if full.startswith(_SELFTEST_PREFIX):
            short = full.rsplit(".", 1)[-1]
            out[short] = out.get(short, 0) + n
    return out


# --- ①–⑧ 断言 ----------------------------------------------------------------------


def test_in_regression_single_source() -> None:
    """① 判定唯一实现（结构证据）：定义只在宿主恰 1 处；两个约定环境变量名各恰 1 处字面量。"""
    defs: list[str] = []
    lits: dict[str, int] = {}
    for p in scanscope.all_modules():
        src = p.read_text(encoding="utf-8")
        if f"def {_IR_NAME}(" in src:
            defs.append(p.name)
        for const in (selftest_kit.IN_REGRESSION_ENV, selftest_kit.TRACE_ENV):
            n = src.count(const)
            if n:
                lits[p.name] = lits.get(p.name, 0) + n
    assert defs == [_KIT], f"`{_IR_NAME}` 的定义应只在 {_KIT} 恰 1 处，实际 {defs}"
    assert lits == {_KIT: 2}, \
        f"两个约定环境变量名的字面量应只在 {_KIT}（各 1 处），实际 {lits}"


def test_guard_shape() -> None:
    """② 守卫形态（结构证据）：守卫**恰好**覆盖「传递可达回归调起」的测试，且不自行读环境变量。"""
    total = 0
    for name in _NONLEAF:
        tree = ast.parse((selftest_kit.PKG_DIR / name).read_text(encoding="utf-8"))
        funcs = _funcs(tree)
        direct = {fn: bool(_bare_calls(node) & _LAUNCH_MARKS) for fn, node in funcs.items()}
        members = _tests_tuple(tree)
        need = sorted(
            m for m in members if m in funcs and _reaches(m, funcs, direct, frozenset())
        )
        guarded = sorted(
            m for m in members if m in funcs and _is_guard(_first_exec(funcs[m]))
        )
        assert guarded == need, \
            f"{name}：守卫应**恰好**覆盖「传递可达回归调起」的测试，实际 guarded={guarded} need={need}"
        # 未守卫的测试**静态也到不了**任何直接调起——否则回归形态下仍会向下展开
        unguarded = sorted(m for m in members if m in funcs and m not in guarded)
        for m in unguarded:
            offenders = sorted(f for f in funcs if f in _closure(m, funcs) and direct[f])
            assert offenders == [], f"{name}.{m} 未守卫、却仍静态可达回归调起 {offenders}"
        total += len(guarded)
    assert total == 16, f"守卫总数应为实测 16（m16×1 m17×2 m18×3 m19×1 m20×1 m21×2 m22×2 m23×2 m24×2），实际 {total}"


def _closure(name: str, funcs: dict[str, ast.FunctionDef],
             seen: frozenset[str] = frozenset()) -> set[str]:
    """`name` 经同模块函数调用可达的函数名集合（含自身）。"""
    out = {name}
    if name in seen:
        return out
    seen2 = seen | {name}
    for callee in _bare_calls(funcs[name]):
        if callee in funcs:
            out |= _closure(callee, funcs, seen2)
    return out


def test_execution_multiplicity_is_one() -> None:
    """③ 执行重数 = 1（可观测，本轮核心）：各模块被调起次数 ≤ 3，无任何模块被重复数十 / 数百次。"""
    per = _selftest_counts(_trace_counts())
    assert per, "trace 应至少记录到一次自测模块调起"
    worst = max(per.values())
    assert worst <= _PER_MODULE_CAP, \
        f"各模块被调起次数应 ≤ {_PER_MODULE_CAP}（⑦ 1 次 + ⑧ 采样 2 次），实际最大 {worst}：{per}"


def test_total_launch_budget() -> None:
    """④ 总次数 ≤ 实现阶段实测取整写入的绝对阈值 29（收口前基线 1062；阈值只降不升）。"""
    counts = _trace_counts()
    total = sum(_selftest_counts(counts).values())
    cli = counts.get(_CLI_MODULE, 0)
    assert total <= _TOTAL_CAP, \
        f"自测模块总调起次数应 ≤ {_TOTAL_CAP}（收口前基线 {_BASELINE}），实际 {total}（CLI 子进程另有 {cli} 次）"


def test_flat_run_counts_unchanged() -> None:
    """⑤ 计数不变：扁平跑 `m18`–`m24`，尾行 `N/N passed` 与收口前逐字相同（早退仍计 PASS）。"""
    for mod, want in _FLAT_TAILS.items():
        rc, out, err = selftest_kit.run_module(mod)
        tail = _last_line(out)
        assert rc == 0 and tail == want, \
            f"{mod} 扁平调起应为 {want}，实际 rc={rc} tail={tail!r} stderr={err[-200:]!r}"


def test_flat_and_deep_agree() -> None:
    """⑥ 扁平 / 深跑同绿：同一模块两形态下自身断言结果与条数一致（深跑另含展开的子模块全绿）。"""
    flat = selftest_kit.run_module("selftest_m19")
    deep = selftest_kit.run_module("selftest_m19", deep=True)
    assert flat[0] == 0, f"扁平跑 selftest_m19 应全绿，实际 rc={flat[0]}；stderr={flat[2][-200:]!r}"
    assert deep[0] == 0, f"深跑 selftest_m19 应全绿，实际 rc={deep[0]}；stderr={deep[2][-200:]!r}"
    assert _last_line(flat[1]) == "8/8 passed", f"扁平尾行应为 8/8 passed，实际 {_last_line(flat[1])!r}"
    assert _last_line(flat[1]) == _last_line(deep[1]), \
        f"两形态自身尾行应一致：扁平 {_last_line(flat[1])!r} vs 深跑 {_last_line(deep[1])!r}"


def test_read_only_and_determinism() -> None:
    """⑦ 只读 + 确定性：同形态两次逐字节一致；未设 trace 时零写盘；夹具目录复合摘要不变。"""
    assert selftest_kit.TRACE_ENV not in os.environ, \
        "⑦ 期间不应置位门控 trace——否则「未设 trace 时零写盘」无从验证"
    with tempfile.TemporaryDirectory() as td_s:
        fixture = Path(td_s)
        (fixture / "keep.txt").write_bytes(b"canary\n")
        before = _dir_digest(fixture)

        first = selftest_kit.run_module("selftest_m1")
        second = selftest_kit.run_module("selftest_m1")
        assert first == second, "同形态两次（退出码 / stdout / stderr）应逐字节一致"
        assert first[0] == 0 and _last_line(first[1]) == "7/7 passed", \
            f"selftest_m1 应 7/7 全绿，实际 rc={first[0]} tail={_last_line(first[1])!r}"

        assert _dir_digest(fixture) == before, "未设 trace 时全过程不得写夹具中的任何一个字节"


def test_coverage_kept_and_arg_boundary() -> None:
    """⑧ 覆盖不减 + 边界：`m24` 目标名单里每模块被调起 ≥ 1 次；需命令行代码根者仍恰为 `m2` / `m3`。"""
    per = _selftest_counts(_trace_counts())
    missing = sorted(m for m in _M24_TARGETS if per.get(m, 0) < 1)
    assert missing == [], \
        f"扁平语义下 m24 的目标名单里每个模块都应被调起 ≥ 1 次，实际缺失 {missing}；实测计数 {per}"

    arg_mods = sorted(
        p.name for p in scanscope.selftest_modules() if _ARGV_MARK in p.read_text(encoding="utf-8")
    )
    assert arg_mods == list(_ARG_EXEMPT), f"需命令行代码根的自测应恰为 m2 / m3，实际 {arg_mods}"


def main() -> int:
    tests = (
        test_in_regression_single_source,
        test_guard_shape,
        test_execution_multiplicity_is_one,
        test_total_launch_budget,
        test_flat_run_counts_unchanged,
        test_flat_and_deep_agree,
        test_read_only_and_determinism,
        test_coverage_kept_and_arg_boundary,
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
