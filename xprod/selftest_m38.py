"""M38 自测：把「『新增里程碑连带影响预检』从人工纪律固化为可执行的『针脚预检机具』」的验收点写成断言。

背景（`X产品化-M38设计稿-v1.md` §一）：M35 与 M37 的复盘各登记一条「加固」——新增拼接常量须用全仓既有
扫描正则自检；新建顶层常量前须与全仓既有「名字 → 文件集」登记表逐名比对——而两条**至今只是路线图里的
文字**，全仓没有一个可执行机具。于是新模块能**静默**闯进别人的登记集合（M37 实测：夹具常量沿用
`_CHANGES` 撞进 `m33` 的 `^_CHANGES = ` 定义文件集）或被别人的扫描正则命中（M35 实测：`m35` 的
`_RENDER_ENTRY = "def " + …` 撞进 `m33` 的 `_RE_LIT_DEF`），两者**只有跑一次全域回归才暴露**。

M38 把「候选源码片段会不会被既有全仓扫描看见」这一步固化为宿主 `selftest_kit.py` 的**唯一实现**
（`scan_needles` / `unfoldable_patterns` / `precheck_fragment`）：针脚全集由 AST **机械推导**（**不手写
名单**，故不随仓增长而陈旧），候选片段做 R（正则针脚）/ N（名字针脚）两维命中判定。**命中 ≠ 失败**——
机具只列出命中项（含来源文件），是「改名避让」还是「登记为该登记表的真值更新项」由**人**裁定。

本文件**不**重复登记针脚真值（那是**第二份定义源**）：三个公共名一律取自宿主，本文件只做**独立复验**
——断言的对象是**磁盘上的实测**，不是把宿主的表再抄一遍。

**自指防护**：本文件同样会被多份既有结构断言（含本里程碑的机具自身）扫到，故凡**将作为候选片段**的
特征串一律**在函数内分段拼接**构造（**不**落模块级常量），使度量器自身**不**字面出现这些特征串、
**不**成为针脚来源、也**不**把回放断言做成同义反复。

覆盖（对应设计稿 §七 ①–⑧）：
  ① **唯一实现 + 机械推导**：三名在宿主各恰 1 处（按 AST 顶层定义计）；针脚集非空、来源真实、两次相同、
     且含宿主与经典登记源 `m33`；
  ② **历史漏判回放（核心证据）**：R 维——M35 收口前的字面量行命中、来源**含** `m33`、模式串含
     `= "def\ "`；N 维——`_CHANGES` 顶层赋值名命中、来源**含** `m33`；
  ③ **不得误报 + dogfooding（核心反向证据）**：两条历史漏判的**改动后**形态两维恰空；本里程碑**新增**的顶层
     名字（3 个公共名 + 本文件顶层名中**非**两个 M31 既定骨架名者）经 `precheck_fragment` **两键俱为空列表**；
     两个既定骨架名的命中**如实列出**、且其连带影响**已**按登记表更新真值（**无**未处置的静默命中，见函数 docstring）；
  ④ **只读 + 确定性 + 取证顺序**：基线**先于**被测动作采集；各两次调用相同；全程不写盘；非法语法抛
     `SyntaxError`（**不**静默）；
  ⑤ **不可折叠不得静默**：`unfoldable_patterns()` 的项数与其登记内容一致（实测 **0** 项；非空即须逐项登记）；
  ⑥ **CLI 与退出码回归**：`drift` / `sync` / `impact` / `flow` / `view` 正常路径 stdout 与库输出**逐字节
     一致**、退出码 **0**、**无 `\\r\\n`**；错误 **1**；用法 **2**（本项**零**产品代码改动）；
  ⑦ **既有自测零修订**：35 个无需命令行参数的自测各按**实测**条数全绿（经 M30 唯一实现 `assert_regression`）；
  ⑧ **全域回归 + 编号无关性**：**逆序**跑同一批自测仍全绿（与 ⑦ 逐条一致）；需代码根者仍**恰为** `m2` / `m3`。

沿用 M0–M37 约定：**不**用管道捕获输出，改临时文件重定向（本机沙箱禁建管道）——本文件自身的脚手架
调用一律经 `selftest_kit` 唯一实现，**不**内联子进程调用。
"""

from __future__ import annotations

import ast
import tempfile
from pathlib import Path

from . import drift, flow, impact_analyzer, scanscope, selftest_kit, sync, viewer
from . import selftest_m30, selftest_m31, selftest_m34
from .selftest_kit import (
    PKG_DIR,
    assert_regression,
    capture_raises as _capture,
    cli as _cli,
    dir_digest as _dir_digest,
    make_fixture as _fixture,
    number_independence_regression,
    ARG_EXEMPT as _ARG_EXEMPT,
    ARGV_MARK as _ARGV_MARK,
)

# ⑤ 的实测登记：不可折叠的 `re.compile` 实参**项数**（本仓实况实测 0；非空即须逐项登记，**不得**静默丢弃）
_UNFOLDABLE_TOTAL = 0

# 本文件名（供只读自身源码用；**不**经任何登记表）
_HERE = "selftest_m38.py"

# ⑦ / ⑧ 的 35 个无需命令行参数的自测（`m2` / `m3` 需代码根，由 ⑧ 的边界先行校验覆盖）；条数为**实测**
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
    "selftest_m37": "8/8",
}

# ⑥ 用的夹具数据（本模块自己的三份；与其余自测同形，仅题头不同）。夹具改动清单**不**取名 `_CHANGES`
# ——该名是 `m33` 明文登记的「两真数据组」专属集合，新里程碑自建夹具须另起名（M35–M37 同法）。
_DESIGN = (
    "# 夹具设计文档（M38 自测专用）\n"
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
    "# 流程夹具（M38 自测专用）\n"
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

_DIFF_CHANGES = (
    ("A", "src/app/api.py", "from app.core import X\nA = 1\n"),
    ("B", "src/app/core.py", "X = 2\n"),
)


# --- ① / ③ 用的只读工具（自持一份最小实现，不引第二份判据）------------------------------


def _def_sites(func: str) -> dict[str, int]:
    """按 AST 统计「顶层函数定义名 = `func`」的文件 → 处数（**不**受源码内字符串字面量干扰）。"""
    hits: dict[str, int] = {}
    for path in scanscope.all_modules():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        n = sum(1 for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == func)
        if n:
            hits[path.name] = n
    return hits


def _public_names() -> tuple[str, str, str]:
    """三个公共名（**函数内分段拼接**，见模块 docstring 的「自指防护」）；供 ① 计数与 ③ dogfooding 复用。"""
    return ("scan" + "_needles", "unfoldable" + "_patterns", "pre" + "check_fragment")


def _own_top_names() -> list[str]:
    """本文件的**顶层**赋值目标名 ∪ 顶层函数名（dogfooding 候选；只读本文件，**不**落模块级常量）。"""
    tree = ast.parse((PKG_DIR / _HERE).read_text(encoding="utf-8"))
    names: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            names.append(node.name)
        elif isinstance(node, ast.Assign):
            names += [t.id for t in node.targets if isinstance(t, ast.Name)]
    return names


# --- ① 断言 ------------------------------------------------------------------------


def test_unique_implementation_and_mechanical_derivation() -> None:
    """① 唯一实现 + 机械推导：三名在宿主各恰 1 处（按 AST）；针脚集非空 / 来源真实 / 两次相同。"""
    for func in _public_names():
        assert _def_sites(func) == {selftest_kit.KIT_NAME: 1}, \
            f"公共实现 {func}(…) 应在 {selftest_kit.KIT_NAME} 恰 1 处（按 AST 顶层定义计），实际 {_def_sites(func)}"

    rows = selftest_kit.scan_needles()
    assert rows, "机械推导的针脚集不得为空（为空即后续断言空真）"
    assert rows == tuple(sorted(set(rows))), "针脚集应按「来源, 值」排序去重（两次调用逐项相同的前提）"
    assert rows == selftest_kit.scan_needles(), "两次调用应逐项相同（会话内不缓存）"

    sources = {f for f, _v in rows}
    assert all((PKG_DIR / f).is_file() for f in sources), f"来源文件应真实存在：{sorted(sources)}"
    assert sources <= {p.name for p in scanscope.selftest_modules()}, \
        "来源应全部落在自测域（边界取 M23 唯一实现，本机具不复刻该判定）"
    assert selftest_kit.KIT_NAME in sources, "宿主自身应在来源之列（其模块级常量本就是针脚）"
    assert "selftest_m33.py" in sources, "经典「名字 → 文件集」登记源应在来源之列"


# --- ② 断言 ------------------------------------------------------------------------


def test_historical_miss_replay() -> None:
    """② 历史漏判回放：M35（R）/ M37（N）两处**改动前**形态各自命中，来源**含** `m33`。"""
    hist_r = ("_RENDER" + "_ENTRY = "
              + '"def "' + " + "
              + '"_render"' + " + "
              + '"_conflict("')
    hits_r = selftest_kit.precheck_fragment(hist_r)["R"]
    sources_r = {f for f, _p in hits_r}
    assert "selftest_m33.py" in sources_r, \
        f"M35 收口前的字面量行应被 m33 的正则针脚命中（**含**而非等于），实际来源 {sorted(sources_r)}"
    mark = '= "def' + "\\" + " " + '"'
    assert any(mark in pat for _f, pat in hits_r), \
        f"命中模式串应含 {mark!r}，实际 {[p for _f, p in hits_r]}"

    hist_n = ("_CHAN" + "GES") + " = (('a', 'b', 'c'),)\n"
    hits_n = selftest_kit.precheck_fragment(hist_n)["N"]
    sources_n = {f for f, _v in hits_n}
    assert "selftest_m33.py" in sources_n, \
        f"M37 收口前的夹具常量名应被 m33 的名字针脚命中（**含**而非等于），实际来源 {sorted(sources_n)}"
    want_n = "_CHAN" + "GES"
    assert want_n in {v for _f, v in hits_n}, f"命中针脚值应含 {want_n!r}，实际 {[v for _f, v in hits_n]}"


# --- ③ 断言 ------------------------------------------------------------------------


def test_no_false_positive_and_dogfood() -> None:
    """③ 不得误报 + dogfooding：两条漏判的**改动后**形态两维恰空；本里程碑**新增**的顶层名字（3 公共名 +
    自身顶层名中**非**两个既定骨架名者）两键恰空；两个既定骨架名的命中**如实列出**、其连带影响**已**按登记表
    更新真值（**无**未处置的静默命中）。

    **口径校正（以实测为准；笔三回写设计稿 / 路线图）**：设计稿 §七 ③ 原写「本文件**全部**顶层名」零命中；
    实测**不可达**——M31 既定形态要求每个自测模块**自持** ⑦/⑧ 两个测试，其**固定名**由 `m30` / `m31` / `m34`
    的登记表**按名字**识别（**不可**改名），故这两个名字**必然**被既有名字针脚命中。依设计稿 §4.3「命中 ≠
    失败，须人裁定」，本文件取裁定 **(b) 登记为真值更新项**：断言命中**恰为**这两个既定名，且四处登记表
    均已含本文件。**此非放宽判据**（新增名仍须零命中），而是按实测把不可达断言校正为可达且更强的形式。
    """
    fixed_r = ("_RENDER" + "_ENTRY = "
               + '"def"' + ' + " " + '
               + '"_render"' + " + "
               + '"_conflict("')
    got_r = selftest_kit.precheck_fragment(fixed_r)
    assert got_r == {"R": [], "N": []}, \
        f"「分段拼接」这一修复应被识别为已避让（两维恰空），实际 {got_r}"

    fixed_n = ("_DIFF" + "_CHAN" + "GES") + " = (('a', 'b', 'c'),)\n"
    got_n = selftest_kit.precheck_fragment(fixed_n)
    assert got_n == {"R": [], "N": []}, \
        f"「改名」这一避让应被识别为已避让（两维恰空），实际 {got_n}"

    # 两个 M31 既定骨架名（**函数内**分段拼接；名字由登记表按名识别，不可改名）
    skeleton = (
        "test_existing" + "_selftests_regression",
        "test_full" + "_regression" + "_and_number" + "_independence",
    )
    own = _own_top_names()
    assert set(skeleton) <= set(own), f"本模块应自持两个既定骨架名，实际 {sorted(own)}"

    fresh = [n for n in own if n not in skeleton]
    got_fresh = selftest_kit.precheck_fragment(
        "".join(f"{name} = 0\n" for name in (*_public_names(), *fresh))
    )
    assert got_fresh == {"R": [], "N": []}, \
        f"本里程碑**新增**的顶层名字应两维俱零命中（dogfooding 自避让），实际 {got_fresh}"

    got_all = selftest_kit.precheck_fragment(
        "".join(f"{name} = 0\n" for name in (*_public_names(), *own))
    )
    assert got_all["R"] == [], f"本模块顶层名字不得被任何正则针脚命中，实际 {got_all['R']}"
    hit_n = sorted({v for _f, v in got_all["N"]})
    assert hit_n == sorted(skeleton), \
        f"自身名字的全部命中应**恰为**两个既定骨架名（不得有第三个未处置的静默命中），实际 {hit_n}"

    # 裁定 (b) 的证据：两个骨架名的连带影响**已**在四处登记表按本文件更新真值（否则即为「静默闯进别人登记集」）
    assert "selftest_m38.py" in selftest_m31._CONSUMERS_2, \
        "骨架名 ⑧ 的连带影响应按登记表更新真值（m31._CONSUMERS_2 应含本文件）"
    assert "selftest_m38.py" in selftest_m31._CONSUMERS_3, \
        "骨架名 ⑦ 的连带影响应按登记表更新真值（m31._CONSUMERS_3 应含本文件）"
    assert "selftest_m38.py" in selftest_m34._KEPT_BOTH, \
        "骨架名 ⑧ 的 AST 文件名集真值应按登记表更新（m34._KEPT_BOTH 应含本文件）"
    reg = dict(selftest_m30._REGISTERED)
    for name in skeleton:
        key = selftest_kit.DEF_PREFIX + name + "("
        assert "selftest_m38.py" in reg[key], \
            f"骨架名 {name!r} 的连带影响应按登记表更新真值（m30._REGISTERED[{key!r}] 应含本文件）"


# --- ④ 断言 ------------------------------------------------------------------------


def test_read_only_determinism_and_evidence_order() -> None:
    """④ 只读 + 确定性 + 取证顺序：基线**先于**被测动作；两次调用相同；不写盘；非法语法抛 `SyntaxError`。"""
    before = _dir_digest(PKG_DIR)          # 基线必须先于被测动作采集（M37 教训 4 的直接兑现）

    assert selftest_kit.scan_needles() == selftest_kit.scan_needles(), "scan_needles 两次调用应逐项相同"
    assert selftest_kit.unfoldable_patterns() == selftest_kit.unfoldable_patterns(), \
        "unfoldable_patterns 两次调用应逐项相同"
    probe = "_RENDER" + "_ENTRY = " + '"def "' + " + " + '"_render"' + " + " + '"_conflict("'
    assert selftest_kit.precheck_fragment(probe) == selftest_kit.precheck_fragment(probe), \
        "precheck_fragment 同输入两次应逐项相同"

    assert _dir_digest(PKG_DIR) == before, "全过程不得写盘（xprod 目录树复合摘要前后应相同）"

    raised = _capture(selftest_kit.precheck_fragment, "def (")
    assert type(raised) is SyntaxError, f"非法语法片段应抛 SyntaxError（**不**静默），实际 {raised!r}"


# --- ⑤ 断言 ------------------------------------------------------------------------


def test_unfoldable_not_silent() -> None:
    """⑤ 不可折叠不得静默：项数与其登记内容一致（实测 0 项；非空则逐项登记，不得丢弃）。"""
    rows = selftest_kit.unfoldable_patterns()
    for name, segment in rows:
        assert (PKG_DIR / name).is_file(), f"不可折叠项的来源应真实存在：{name}"
        assert segment.strip(), f"不可折叠项应含源码片段（不得为空）：{(name, segment)!r}"
    assert len(rows) == _UNFOLDABLE_TOTAL, \
        f"不可折叠实参应恰为登记的 {_UNFOLDABLE_TOTAL} 项（非空即须逐项登记），实际 {rows}"


# --- ⑥ 断言（夹具数据见上 `_DESIGN` / `_FLOW` / `_DIFF_CHANGES`）----------------------


def test_cli_and_exit_codes() -> None:
    """⑥ CLI 与退出码回归：stdout 与库输出逐字节一致、无 `\\r\\n`；错误 1；用法 2。"""
    with tempfile.TemporaryDirectory() as td:
        root, design, flow_doc, diffs = _fixture(
            Path(td), design_text=_DESIGN, flow_text=_FLOW, changes=_DIFF_CHANGES
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


# --- ⑦ / ⑧ 35 个无需命令行参数的自测（`m2` / `m3` 需代码根，见 ⑧）；条数为**实测** ------------


def test_existing_selftests_regression() -> None:
    """⑦ 既有自测零修订：35 个无需参数的自测各按实测条数全绿（经共享 `assert_regression`）。"""
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
        test_unique_implementation_and_mechanical_derivation,
        test_historical_miss_replay,
        test_no_false_positive_and_dogfood,
        test_read_only_determinism_and_evidence_order,
        test_unfoldable_not_silent,
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
