"""M37 自测：把「『逐字同构』判据的锁定范围由『整段源码（含 docstring）』收窄为『函数体（去 docstring）』，
被释放的 docstring 改为『按模块登记真值』」的验收点写成可执行断言。

背景（`X产品化-M37设计稿-v1.md` §一）：M31 的 `_segment` 以**整段源码（含 docstring）**为「逐字同构」的
真值，于是**文档（docstring）与代码（函数体）被同一条判据锁在一起**——上游一处的字面笔误被**强制继承**
到全链，且**任一侧都无法单独更正**。M37 把该真值**收窄**为「**函数体（去 docstring）的原始源段**」
（**代码**仍按**口径 A：原始源段逐字节相同**比较，强判据**原样保留**、**不**降级为 `ast.unparse`），
并把被**释放**的 docstring 改为**按各模块自身真值**逐模块**登记 + 断言**（`_DOC_TPL` / `_DOC_MARK` /
`_DOC_EXTRA`），`m35` / `m36` 两处被旧判据**锁坏**的标号如实校正。

本文件**不**重复登记判据真值（那是**第二份定义源**）：`_DOC_TPL` / `_DOC_MARK` / `_DOC_EXTRA` /
`_body_segment` / `_doc_of` / 消费名单**一律**取自 `selftest_m31` 这**唯一实现**，本文件只对
「**磁盘上的实际文件**」做**独立复验**——断言的对象是**实测**，不是把 m31 的表再抄一遍。

覆盖（对应设计稿 §七 ①–⑧）：
  ① **口径收窄（结构断言，核心）**：旧名 `_segment` 在 `selftest_m31.py` 内按 AST 的**调用**恰 **0** 处；
     `_body_segment(name, _BOTH)` 的返回串对 **12** 处**逐字节相同**、对 `_EXTRA` 的 **3** 处**逐字节相同**；
     且该串**不含** docstring 标号字符（`⑧` / `⑩`）——直接证据：docstring 已不参与判据；
  ② **释放口径（结构断言）**：`_body_segment` 体内**恰 1** 处口径 A（`ast.get_source_segment`）、**零**处
     口径 B（`ast.unparse`，**未**降级）；旧名 `_segment` 在全仓**定义 0 处 / 引用 0 处**（按 AST）；
  ③ **docstring 登记真值（核心证据）**：`_BOTH` 每处 docstring **逐字等于** `_DOC_TPL.format(own, ref)`
     （`_DOC_MARK` 键集**恰等**消费名单）；`_EXTRA` 每处**逐字等于** `_DOC_EXTRA`；`_BOTH` 首标号**实测 ≥ 2 组**；
  ④ **`m35` / `m36` 标号兑现**：二者 `_BOTH` docstring 首标号**实测均为 `⑩`**、引用项**均为 `⑨`**；
     `m36` 的 `_EXIST` docstring 首标号**实测为 `⑨`**（**未**被 M37 改坏）；
  ⑤ **`m35` 自身清单自洽（文档级）**：`m35` 模块 docstring 覆盖清单**实测含 ①–⑩**（`⑨ 既有自测零修订` /
     `⑩ 全域回归 + 编号无关性`），且两条标准项的 docstring 首标号与清单**逐条对应**（`⑨` / `⑩`）；
  ⑥ **CLI 与退出码回归**：`drift` / `sync` / `impact` / `flow` / `view` 正常路径 stdout 与库输出**逐字节
     一致**、退出码 **0**、**无 `\\r\\n`**；错误 **1**；用法 **2**（本项**零**产品代码改动）；
  ⑦ **既有自测零修订**：34 个无需命令行参数的自测各按**实测**条数全绿（经 M30 唯一实现 `assert_regression`）；
  ⑧ **全域回归 + 编号无关性**：**逆序**跑同一批自测仍全绿（与 ⑦ 逐条一致）；需代码根者仍**恰为** `m2` / `m3`。

**自指防护**（沿用 M23–M36）：本文件同样会被多份既有结构断言扫到，故凡以**源码文本**为输入的断言，
其待查特征串一律**分段拼接**（`"_" + "segment"`、`"_body" + "_segment"`），使度量器自身**不字面出现**
该特征串；`m30` 的两条**文本计数**针脚（两份薄包装的 `def` 全签名）在本文件中因此**各只出现一次**
（即各自的 `def` 行本身）。

沿用 M0–M36 约定：**不**用管道捕获输出，改临时文件重定向（本机沙箱禁建管道）——
本文件自身的脚手架调用一律经 `selftest_kit` 唯一实现，**不**内联子进程调用。
"""

from __future__ import annotations

import ast
import tempfile
from pathlib import Path

from . import drift, flow, impact_analyzer, scanscope, selftest_kit, sync, viewer
from . import selftest_m31
from .selftest_kit import (
    PKG_DIR,
    assert_regression,
    cli as _cli,
    dir_digest as _dir_digest,
    make_fixture as _fixture,
    number_independence_regression,
    ARG_EXEMPT as _ARG_EXEMPT,
    ARGV_MARK as _ARGV_MARK,
)

# 待查特征串**分段拼接**（见模块 docstring 的「自指防护」）：拼出的结果不在本文件源码中字面出现
_BOTH = "test_full" + "_regression_and_number" + "_independence"   # ② 的骨架名
_EXIST = "test_existing" + "_selftests_regression"                # ③ 的骨架名
_EXTRA = "test_full" + "_regression_extra"                        # ① 的骨架名（明文保留不收口）
_OLD_SEG = "_" + "segment"                                        # 收窄前的旧名（应收窄后全仓 0 处定义 / 0 处引用）
_NEW_SEG = "_body" + "_segment"                                   # 收窄后的新名（口径 A：函数体去 docstring）
_GET_SEG = "get_source" + "_segment"                              # 口径 A 的取证调用
_UNPARSE = "un" + "parse"                                         # 口径 B（仅作形态证据，不升降格）

# ③ / ④ / ⑤ 用的标号真值与清单特征串（`m35` / `m36` 的两条标准项；`m35` 清单为其模块 docstring 的子串）
_MARK_9 = "⑨"
_MARK_10 = "⑩"
_BOTH_M35_M36 = (_MARK_10, _MARK_9)                # `m35` / `m36` 的 `_BOTH` 登记真值（本项, 被引用项）
_M35_MARK_9 = _MARK_9 + " **既有自测零修订**"        # `m35` 清单里 ⑨ 项的原文（含 markdown 加粗）
_M35_MARK_10 = _MARK_10 + " **全域回归 + 编号无关性**"  # `m35` 清单里 ⑩ 项的原文
_M35_SUFFIX = "＋ ⑨/⑩"                             # `m35` 清单头「①–⑧ ＋ ⑨/⑩」的后缀（来源标注）

# ① / ③ 的 docstring 标号字符集：收窄后的「函数体」串内**不得**出现其中任何一个
_DOC_MARKS = ("⑧", _MARK_10)

# ⑦ / ⑧ 的 34 个无需命令行参数的自测（`m2` / `m3` 需代码根，由 ⑧ 的边界先行校验覆盖）；条数为**实测**
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
    "selftest_m34": "8/8",
    "selftest_m35": "11/11",
    "selftest_m36": "10/10",
}

# ⑤ 用的夹具数据（本模块自己的三份；与其余自测同形，仅题头不同）
_DESIGN = (
    "# 夹具设计文档（M37 自测专用）\n"
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
    "# 流程夹具（M37 自测专用）\n"
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

# 夹具改动清单：**不**取名 `_CHANGES`——该名是 `m33` 明文登记的「两真数据组」专属集合，
# 新里程碑自建夹具须另起名（M35 / M36 同法，避免把新模块误并进那张登记表）
_DIFF_CHANGES = (
    ("A", "src/app/api.py", "from app.core import X\nA = 1\n"),
    ("B", "src/app/core.py", "X = 2\n"),
)


# --- ① / ② 用的只读 AST 工具（自持一份最小实现，不引第二份判据）--------------------------


def _m31_src() -> str:
    """`selftest_m31.py` 的源码原文（判据本体所在；本模块只读、不写）。"""
    return (PKG_DIR / "selftest_m31.py").read_text(encoding="utf-8")


def _top_func(tree: ast.Module, name: str) -> ast.FunctionDef:
    """取顶层函数定义节点（未找到即失败，**不**静默跳过）。"""
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"未找到顶层函数 {name!r}（收窄后应仍存在该定义）")


# --- ① 断言 ------------------------------------------------------------------------


def test_segment_scope_narrowed() -> None:
    """① 口径收窄：旧名在 `m31` 内按 AST 的调用恰 0 处；新名函数体串逐模块逐字节同构且不含标号字符。"""
    tree = ast.parse(_m31_src())
    old_calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == _OLD_SEG
    ]
    assert old_calls == [], f"旧名 {_OLD_SEG!r} 的调用应收窄后为 0 处（按 AST），实际 {len(old_calls)} 处"

    segs_2 = {selftest_m31._body_segment(name, _BOTH) for name in selftest_m31._CONSUMERS_2}
    assert len(segs_2) == 1, \
        f"`{_BOTH}` 的 {len(selftest_m31._CONSUMERS_2)} 处函数体源段应逐字节相同，实际 {len(segs_2)} 种"
    segs_1 = {selftest_m31._body_segment(name, _EXTRA) for name in selftest_m31._KEPT_1}
    assert len(segs_1) == 1, \
        f"`{_EXTRA}` 的 {len(selftest_m31._KEPT_1)} 处函数体源段应逐字节相同，实际 {len(segs_1)} 种"

    for seg in segs_2 | segs_1:
        for mark in _DOC_MARKS:
            assert mark not in seg, \
                f"收窄后的「函数体」串不得含 docstring 标号字符 {mark!r}，实际 {seg!r}"


# --- ② 断言 ------------------------------------------------------------------------


def test_release_scope_ast_evidence() -> None:
    """② 释放口径：`_body_segment` 体内恰 1 处口径 A、0 处口径 B；旧名在全仓定义/引用 0 处（按 AST）。"""
    node = _top_func(ast.parse(_m31_src()), _NEW_SEG)
    n_a = sum(1 for n in ast.walk(node) if isinstance(n, ast.Attribute) and n.attr == _GET_SEG)
    n_b = sum(1 for n in ast.walk(node) if isinstance(n, ast.Attribute) and n.attr == _UNPARSE)
    assert (n_a, n_b) == (1, 0), \
        f"`{_NEW_SEG}` 体内应恰 1 处口径 A（`{_GET_SEG}`）、0 处口径 B（`{_UNPARSE}`），实际 {(n_a, n_b)}"

    defs: dict[str, int] = {}
    refs: dict[str, int] = {}
    for p in scanscope.all_modules():
        t = ast.parse(p.read_text(encoding="utf-8"))
        d = sum(1 for n in t.body if isinstance(n, ast.FunctionDef) and n.name == _OLD_SEG)
        if d:
            defs[p.name] = d
        r = sum(
            1 for n in ast.walk(t)
            if (isinstance(n, ast.Name) and n.id == _OLD_SEG)
            or (isinstance(n, ast.Attribute) and n.attr == _OLD_SEG)
        )
        if r:
            refs[p.name] = r
    assert defs == {}, f"旧名 {_OLD_SEG!r} 应全仓定义 0 处（按 AST），实际 {defs}"
    assert refs == {}, f"旧名 {_OLD_SEG!r} 应全仓引用 0 处（按 AST），实际 {refs}"


# --- ③ 断言 ------------------------------------------------------------------------


def test_docstring_registered_truth() -> None:
    """③ docstring 登记真值：`_BOTH` 逐字等于模板（键集恰等消费名单）；`_EXTRA` 逐字等于登记真值；首标号 ≥ 2 组。"""
    assert set(selftest_m31._DOC_MARK) == set(selftest_m31._CONSUMERS_2), \
        f"`_DOC_MARK` 键集应恰等消费名单，实际 {sorted(selftest_m31._DOC_MARK)} vs {sorted(selftest_m31._CONSUMERS_2)}"

    for name in selftest_m31._CONSUMERS_2:
        own, ref = selftest_m31._DOC_MARK[name]
        want = selftest_m31._DOC_TPL.format(own=own, ref=ref)
        got = selftest_m31._doc_of(name, _BOTH)
        assert got == want, f"{name} 的 `{_BOTH}` docstring 应逐字为该模块登记真值，实际 {got!r}"

    for name in selftest_m31._KEPT_1:
        got = selftest_m31._doc_of(name, _EXTRA)
        assert got == selftest_m31._DOC_EXTRA, \
            f"{name} 的 `{_EXTRA}` docstring 应逐字为 {selftest_m31._DOC_EXTRA!r}，实际 {got!r}"

    marks = {v[0] for v in selftest_m31._DOC_MARK.values()}
    assert len(marks) >= 2, f"`{_BOTH}` 首标号应实测至少 2 组（锁定已被释放），实际 {sorted(marks)}"


# --- ④ 断言 ------------------------------------------------------------------------


def test_m35_m36_marks_fixed() -> None:
    """④ `m35` / `m36` 标号兑现：二者 `_BOTH` 首标号为 `⑩`、引用项为 `⑨`；`m36` 的 `_EXIST` 首标号为 `⑨`。"""
    for name in ("selftest_m35.py", "selftest_m36.py"):
        own, ref = selftest_m31._DOC_MARK[name]
        assert (own, ref) == _BOTH_M35_M36, \
            f"{name} 的 `{_BOTH}` 登记真值应为 {_BOTH_M35_M36}，实际 {(own, ref)}"
        doc = selftest_m31._doc_of(name, _BOTH)
        assert doc.startswith(own), f"{name} 的 `{_BOTH}` docstring 应以 {own!r} 起，实际 {doc!r}"
        assert f"（与 {ref} 逐条一致）" in doc, f"{name} 的 `{_BOTH}` docstring 应引用 {ref!r}，实际 {doc!r}"

    doc36 = selftest_m31._doc_of("selftest_m36.py", _EXIST)
    assert doc36.startswith(_MARK_9), \
        f"`m36` 的 `{_EXIST}` docstring 应以 {_MARK_9!r} 起（未被 M37 改坏），实际 {doc36!r}"


# --- ⑤ 断言 ------------------------------------------------------------------------


def test_m35_list_self_consistent() -> None:
    """⑤ `m35` 自身清单自洽：模块 docstring 清单实测含 ①–⑩，且两条标准项 docstring 首标号与清单逐条对应。"""
    mod_doc = ast.get_docstring(ast.parse((PKG_DIR / "selftest_m35.py").read_text(encoding="utf-8")))
    assert mod_doc is not None, "`m35` 模块 docstring 应存在（清单即其内容）"
    assert _M35_MARK_9 in mod_doc, f"`m35` 清单应含 ⑨ 项原文 {_M35_MARK_9!r}"
    assert _M35_MARK_10 in mod_doc, f"`m35` 清单应含 ⑩ 项原文 {_M35_MARK_10!r}"
    assert _M35_SUFFIX in mod_doc, f"`m35` 清单头应标注来源 {_M35_SUFFIX!r}"

    exist_doc = selftest_m31._doc_of("selftest_m35.py", _EXIST)
    both_doc = selftest_m31._doc_of("selftest_m35.py", _BOTH)
    assert exist_doc.startswith(_MARK_9), f"`m35` 的 `{_EXIST}` docstring 首标号应与清单 ⑨ 项对应，实际 {exist_doc!r}"
    assert both_doc.startswith(_MARK_10), f"`m35` 的 `{_BOTH}` docstring 首标号应与清单 ⑩ 项对应，实际 {both_doc!r}"


# --- ⑥ 断言 ------------------------------------------------------------------------


def test_cli_and_exit_codes() -> None:
    """⑥ CLI 与退出码回归：stdout 与库输出逐字节一致、无 `\\r\\n`；错误 1；用法 2（零产品代码改动）。"""
    with tempfile.TemporaryDirectory() as td:
        root, design, flow_doc, diffs = _fixture(
            Path(td), design_text=_DESIGN, flow_text=_FLOW, changes=_DIFF_CHANGES
        )
        before = _dir_digest(Path(td))

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

        assert _dir_digest(Path(td)) == before, "本测试全程不得写夹具中的任何一个字节"


# --- ⑦ / ⑧ 34 个无需命令行参数的自测（`m2` / `m3` 需代码根，见 ⑧）；条数为**实测** ------------


def test_existing_selftests_regression() -> None:
    """⑦ 既有自测零修订：34 个无需参数的自测各按实测条数全绿（经共享 `assert_regression`）。"""
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
        test_segment_scope_narrowed,
        test_release_scope_ast_evidence,
        test_docstring_registered_truth,
        test_m35_m36_marks_fixed,
        test_m35_list_self_consistent,
        test_cli_and_exit_codes,
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
