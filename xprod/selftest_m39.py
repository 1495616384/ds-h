"""M39 自测：把「纠偏指令生成器」的验收点写成可执行断言。

背景（`X产品化-M39设计稿-v1.md` §一 / §二）：路线图闭环是「传感器 → 控制器 → 执行器 → 被控对象 → 反馈」，
本仓此前**只建成了传感器**——`drift` / `flow` / `conflict` / `sync` 都能**报出偏差**，却**没有任何件把偏差
翻译成「下一步该做什么」**。M39 补上闭环「控制器」的**策略半边**：`remediator.py` 把既有判定产物
**翻译**为**有界、可追溯、咨询式**的纠偏指令集（**不**新增任何判定、**不**做门禁、**不**阻断合并）。

**实现期口径校正（以实测为准；笔三回写设计稿 / 路线图）**：设计稿 §七 ② 写死 `directive_count=8`，但其
**同一句**列举的输入构成为「2 条失联锚 + 1 条无锚证据 + 1 条断链步骤 + 1 对文件层冲突 + 1 对流程层冲突 +
1 条基线新增失联」——**按列举构造实测恰为 7**（「对」= 1 条冲突记录 = 1 条指令）。本文件 ② 按**实测 7** 断言，
设计稿的 8 作口径校正登记（**不**放宽判据，也**不**回改设计稿正文）。

**自指防护**：本文件同样会被多份既有结构断言扫到，故凡**将作为候选片段 /** 会被全仓扫描看见的特征串
一律**分段拼接**构造（**不**落模块级常量），使度量器自身**不**字面出现这些特征串（与 M23–M38 同法）。

覆盖（对应设计稿 §七 ①–⑧）：
  ① **唯一实现 + 采集/构造分列**：`remediate` / `remediate_prepared` 的**全签名定义**在全仓各恰 1 处且均在
     `remediator.py`；且 `remediate_prepared` 体内**零采集调用**（AST 结构断言，M36 ⑧ 同口径）；
  ② **逐源翻译正确（核心证据）**：喂入**合成判定产物**⇒ `directive_count=7`，逐条
     `(source, kind, target_kind, target)` 与**预期序列**（按 §4.4 排序）恰等；`evidence` 逐键与来源
     **同一对象**（`is` 级同值）；**有意重叠**（同一失联锚既出 `restore_dangling_anchor` 又出 `fix_new_drift`）
     两条指令 `directive_id` 不同 ⇒ 不合并、不去重；
  ③ **有界 + 可追溯 + 确定性 + dogfooding（核心反向证据）**：每条指令 `target` 为标量字符串、`directive_id`
     互不重复；`evidence` 值逐键 `is` 级取自来源；`remediate_prepared` 两次调用逐字节相同、**全程不写盘**
     （对 `xprod` 目录树复合摘要**前后相同**，**基线先于**被测动作采集——M37 教训 4 直接兑现）；
     `remediator.py` 全文经 M38 `precheck_fragment` **两维零命中**（§五 dogfooding）；
  ④ **空输入不得误报**：全绿产物 ⇒ `directive_count=0` / `state="clear"` / `by_kind` 六键恰 0 / `directives`
     恰空；**缺省来源**时对应 kind 恰 0（§4.1 末段）；
  ⑤ **咨询式声明与无门禁**：顶层 `note` 为**写死常量**（同一对象）且含三句声明；`state` 仅取两值；
     `remediator.py` **无** `verdict` 字段、字典字面量**无**判定字段名（AST / 文本双查）；
  ⑥ **CLI 与退出码回归**：`parse` / `graph` / `drift` / `sync` / `impact` / `flow` / `view` / `remediate`
     正常路径 stdout 与库输出**逐字节一致**、退出码 **0**、**无 `\\r\\n`**；错误 **1**；用法 **2**
     （含缺参数、`--diff` 缺 `--flow`、`--plan` 缺 `--flow` 三类）；
  ⑦ **既有自测零修订**：36 个无需参数的自测各按**实测**条数全绿（经 M30 唯一实现 `assert_regression`）；
  ⑧ **全域回归 + 编号无关性**：**逆序**跑同一批自测仍全绿（与 ⑦ 逐条一致）；需代码根者仍恰为 `m2` / `m3`。

沿用 M0–M38 约定：**不**用管道捕获输出，改临时文件重定向（本机沙箱禁建管道）——本文件自身的脚手架
调用一律经 `selftest_kit` 唯一实现，**不**内联子进程调用。
"""

from __future__ import annotations

import ast
import tempfile
from pathlib import Path

from . import conflict, drift, flow, graph_builder, impact_analyzer, parser, remediator, scanscope, selftest_kit, sync, viewer
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
    DEF_PREFIX as _D,
)

# ① 两个公共入口的**全签名锚点**（分段拼接，见模块 docstring 的「自指防护」；**不**落 `= "def "`）
_SIG_REMEDIATE = _D + "remed" + "iate("
_SIG_PREPARED = _D + "remed" + "iate_prepared("

# ① `remediate_prepared` 体内**不得**出现的采集调用名（M36 ⑧ 口径：构造入口体内零采集）
_FORBIDDEN_CALLS = (
    "build_graph",
    "parse_file",
    "parse_flow_doc",
    "read_text",
    "read_bytes",
    "read_diff",
    "scan_tree",
)

# 本模块名（供只读源码用；**不**经任何登记表）
_HERE = "selftest_m39.py"

# ③ / ⑤ 的 dogfooding 对象：纠偏指令生成器（**实现模块**，M39 新增）
_TARGET_MODULE = "remed" + "iator.py"

# ⑤ 的判定字段名黑名单（字典**键**口径；`note` 值里的「不阻断合并」是**负向声明**，不在本口径内）
_GATE_TOKENS = (
    "verdict",
    "pass",
    "fail",
    "passed",
    "failed",
    "decision",
    "gate",
    "block",
    "reject",
    "allow",
    "deny",
)

# ② 预期指令序列（按 §4.4 排序：来源 → 类别 → target 升序）
_EXPECTED = (
    ("drift", "restore_dangling_anchor", "anchor", "D-1@src/app/gone.py"),
    ("drift", "restore_dangling_anchor", "anchor", "D-2@src/app/missing.py"),
    ("drift", "fix_unanchored_evidence", "anchor", "U-1@无锚证据"),
    ("flow", "restore_flow_step", "flow_step", "FL-001/S9"),
    ("conflict", "serialize_change_conflict", "changeset_pair", "A<>B"),
    ("conflict", "serialize_flow_conflict", "changeset_pair", "flow:A<>B"),
    ("baseline", "fix_new_drift", "anchor", "D-1@src/app/gone.py"),
)

# ② / ③ 预期 evidence：`directive_id` → （来源记录键, 该 kind 的写死键集）
_EVIDENCE_KEYS = (
    ("drift:restore_dangling_anchor:D-1@src/app/gone.py", "d1", ("anchor", "match_kind", "reason")),
    ("drift:restore_dangling_anchor:D-2@src/app/missing.py", "d2", ("anchor", "match_kind", "reason")),
    ("drift:fix_unanchored_evidence:U-1@无锚证据", "u1", ("evidence",)),
    ("flow:restore_flow_step:FL-001/S9", "s1", ("anchor",)),
    ("conflict:serialize_change_conflict:A<>B", "c1", ("kinds", "shared_files", "shared_entries")),
    ("conflict:serialize_flow_conflict:flow:A<>B", "f1", ("kinds", "shared_steps", "shared_flows")),
    ("baseline:fix_new_drift:D-1@src/app/gone.py", "n1", ("evidence",)),
)

# ⑤ 写死的三句咨询式声明（`note` 必须逐句含之）
_SUMMARY_PHRASES = ("不自动执行", "不阻断合并", "不表示设计完整或正确")

# ⑦ / ⑧ 的 36 个无需命令行参数的自测（`m2` / `m3` 需代码根，由 ⑧ 的边界先行校验覆盖）；条数为**实测**
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
    "selftest_m38": "8/8",
}

# ⑥ 用的夹具数据（本模块自己的三份；与其余自测同形，仅题头不同）。夹具改动清单**不**取名 `_CHANGES`
# ——该名是 `m33` 明文登记的「两真数据组」专属集合，新里程碑自建夹具须另起名（M35–M38 同法）。
_DESIGN = (
    "# 夹具设计文档（M39 自测专用）\n"
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
    "# 流程夹具（M39 自测专用）\n"
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


# --- ② / ③ 用的**合成判定产物**（进程内构造，不落盘、不经任何模块）----------------------------


def _bundle() -> tuple[dict, dict, dict, dict, dict]:
    """合成四份判定产物 + 来源记录本体：返回 (drift, flow, conflict, baseline, records)。

    `records` 保存**来源记录本体**，供 ③ 断言 `evidence` 值 `is` 级同源（**不**重算、**不**补算的另一半）。
    `baseline.newly_dangling` 刻意取与 `drift` 失联锚 `D-1` **同一锚**——如实回放 §4.1 的「有意重叠」。
    """
    d1 = {
        "constraint_id": "D-1",
        "evidence": "src/app/gone.py",
        "anchor": "src/app/gone.py",
        "match_kind": "exact",
        "reason": "锚路径失联",
    }
    d2 = {
        "constraint_id": "D-2",
        "evidence": "src/app/missing.py",
        "anchor": "src/app/missing.py",
        "match_kind": "exact",
        "reason": "锚路径失联",
    }
    u1 = {"constraint_id": "U-1", "evidence": "无锚证据"}
    s1 = {"flow_id": "FL-001", "step_id": "S9", "anchor": "src/app/gone.py"}
    c1 = {
        "left": "A",
        "right": "B",
        "kinds": ["file"],
        "shared_files": ["src/app/api.py"],
        "shared_entries": [],
    }
    f1 = {
        "left": "A",
        "right": "B",
        "kinds": ["step"],
        "shared_steps": [{"flow_id": "FL-001", "step_id": "S1"}],
        "shared_flows": [],
    }
    n1 = {"constraint_id": "D-1", "evidence": "src/app/gone.py"}
    drift_doc = {"dangling_anchors": [d1, d2], "unanchored_evidence": [u1]}
    flow_doc = {"impact": {"dangling_steps": [s1]}}
    conflict_doc = {"conflicts": [c1], "flow_conflict": {"conflicts": [f1]}}
    baseline_doc = {"newly_dangling": [n1]}
    records = {"d1": d1, "d2": d2, "u1": u1, "s1": s1, "c1": c1, "f1": f1, "n1": n1}
    return drift_doc, flow_doc, conflict_doc, baseline_doc, records


def _empty_drift() -> dict:
    """全绿 drift 产物（无失联锚、无无锚证据）——④ 的空输入一半。"""
    return {"dangling_anchors": [], "unanchored_evidence": []}


# --- ① / ③ / ⑤ 用的只读工具（自持最小实现，不引第二份判据）--------------------------------


def _module_source(name: str) -> str:
    """只读某模块源码（**字节流**读，避免文本模式把换行归一化后与磁盘不符）。"""
    return (PKG_DIR / name).read_bytes().decode("utf-8")


def _def_sites(func: str) -> dict[str, int]:
    """按 AST 统计「顶层函数定义名 = `func`」的文件 → 处数（**不**受源码内字符串字面量干扰）。"""
    hits: dict[str, int] = {}
    for path in scanscope.all_modules():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        n = sum(1 for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == func)
        if n:
            hits[path.name] = n
    return hits


def _dict_keys(text: str) -> set[str]:
    """某模块源码里**字典字面量的字符串键**（⑤ 判定字段名黑名单的 AST 口径）。"""
    keys: set[str] = set()
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, ast.Dict):
            for k in node.keys:
                if isinstance(k, ast.Constant) and isinstance(k.value, str):
                    keys.add(k.value)
    return keys


# --- ① 断言 ------------------------------------------------------------------------


def test_unique_implementation_and_separation() -> None:
    """① 唯一实现 + 采集/构造分列：两入口全签名各恰 1 处且在 `remediator.py`；构造入口体内零采集。"""
    assert _def_sites("remed" + "iate") == {_TARGET_MODULE: 1}, \
        f"采集入口应在 {_TARGET_MODULE} 恰 1 处（按 AST 顶层定义计），实际 {_def_sites('remed' + 'iate')}"
    assert _def_sites("remed" + "iate_prepared") == {_TARGET_MODULE: 1}, \
        f"构造入口应在 {_TARGET_MODULE} 恰 1 处（按 AST 顶层定义计），实际 {_def_sites('remed' + 'iate_prepared')}"

    src = _module_source(_TARGET_MODULE)
    for sig in (_SIG_REMEDIATE, _SIG_PREPARED):
        assert src.count(sig) == 1, f"全签名锚点应在目标模块恰 1 处：{sig!r} → {src.count(sig)}"

    # 构造入口体内**零采集**：以 AST 取其函数体，扫描上述采集调用名（属性名 / 名字两种形态）
    tree = ast.parse(src)
    node = next(
        n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == ("remed" + "iate_prepared")
    )
    calls = {
        getattr(c.func, "attr", getattr(c.func, "id", ""))
        for c in ast.walk(node)
        if isinstance(c, ast.Call)
    }
    got = sorted(calls & set(_FORBIDDEN_CALLS))
    assert got == [], f"构造入口体内不得出现采集调用（应零采集），实际 {got}"


# --- ② 断言 ------------------------------------------------------------------------


def test_translation_accuracy() -> None:
    """② 逐源翻译正确：合成产物 ⇒ 7 条指令，逐条四元组恰等预期；`evidence` 逐键 `is` 级同源。

    **口径校正**：设计稿 §七 ② 写死 `directive_count=8`，按同句列举构造**实测为 7**（见模块 docstring）。
    """
    drift_doc, flow_doc, conflict_doc, baseline_doc, records = _bundle()
    doc = remediator.remediate_prepared(
        drift_doc=drift_doc, flow_doc=flow_doc, conflict_doc=conflict_doc, baseline_doc=baseline_doc
    )

    assert doc["directive_count"] == 7, f"合成产物应恰 7 条指令（实测），实际 {doc['directive_count']}"
    assert doc["state"] == "actionable", f"非空指令集应 state=actionable，实际 {doc['state']!r}"
    got = [(d["source"], d["kind"], d["target_kind"], d["target"]) for d in doc["directives"]]
    assert got == list(_EXPECTED), f"指令四元组应逐条恰等预期序列，实际 {got}"

    # evidence 逐键与来源产物**同一对象**（`is` 级同值）：不重算、不补算
    by_id = {d["directive_id"]: d for d in doc["directives"]}
    for did, rec_key, keys in _EVIDENCE_KEYS:
        d = by_id[did]
        assert set(d["evidence"]) == set(keys), f"{did} 的 evidence 键集应为 {keys}，实际 {sorted(d['evidence'])}"
        for k in keys:
            assert d["evidence"][k] is records[rec_key][k], \
                f"{did} 的 evidence[{k!r}] 应与来源记录同一对象（不重算），实际 {d['evidence'][k]!r}"

    # 有意重叠：同一失联锚 `D-1` 既出 drift（全量）又出 baseline（增量），二者 id / 语义不同 ⇒ 不合并
    overlap = [d["directive_id"] for d in doc["directives"] if d["target"] == "D-1@src/app/gone.py"]
    assert len(overlap) == 2 and len(set(overlap)) == 2, \
        f"同一失联锚的全量 / 增量两条指令应并存且 id 互异，实际 {overlap}"


# --- ③ 断言 ------------------------------------------------------------------------


def test_bounded_traceable_deterministic_and_dogfood() -> None:
    """③ 有界 + 可追溯 + 确定性 + dogfooding：target 标量、id 唯一；两次逐字节相同；不写盘；两维零命中。"""
    before = _dir_digest(PKG_DIR)          # 基线必须先于被测动作采集（M37 教训 4 的直接兑现）

    b1 = _bundle()
    d1 = remediator.remediate_prepared(drift_doc=b1[0], flow_doc=b1[1], conflict_doc=b1[2], baseline_doc=b1[3])
    b2 = _bundle()
    d2 = remediator.remediate_prepared(drift_doc=b2[0], flow_doc=b2[1], conflict_doc=b2[2], baseline_doc=b2[3])
    assert remediator.to_json(d1) == remediator.to_json(d2), "同一输入两次构造应逐字节相同（确定性）"

    for d in d1["directives"]:
        assert isinstance(d["target"], str) and d["target"], f"每条指令的 target 应为**单个非空标量**，实际 {d}"
    ids = [d["directive_id"] for d in d1["directives"]]
    assert len(ids) == len(set(ids)), f"directive_id 应互不重复（内容派生），实际 {ids}"

    assert _dir_digest(PKG_DIR) == before, "构造全过程不得写盘（xprod 目录树复合摘要前后应相同）"

    hits = selftest_kit.precheck_fragment(_module_source(_TARGET_MODULE))
    assert hits == {"R": [], "N": []}, \
        f"{_TARGET_MODULE} 全部顶层名应经 M38 机具两维零命中（dogfooding），实际 {hits}"


# --- ④ 断言 ------------------------------------------------------------------------


def test_empty_input_not_misreported() -> None:
    """④ 空输入不得误报：全绿 ⇒ clear / 0 / 六键全 0 / 空列表；缺省来源时对应 kind 恰 0。"""
    empty = remediator.remediate_prepared(drift_doc=_empty_drift())
    assert empty["state"] == "clear", f"全绿产物应 state=clear，实际 {empty['state']!r}"
    assert empty["directive_count"] == 0, f"全绿产物应 0 条指令，实际 {empty['directive_count']}"
    assert empty["directives"] == [], f"全绿产物应恰为空列表，实际 {empty['directives']!r}"
    assert set(empty["by_kind"]) == set(remediator.KIND_ORDER), \
        f"by_kind 六键应始终存在，实际 {sorted(empty['by_kind'])}"
    assert all(v == 0 for v in empty["by_kind"].values()), f"全绿产物 by_kind 六键应恰为 0，实际 {empty['by_kind']}"

    # 缺省来源（§4.1 末段：缺失即按「无该来源」处理，非报错）
    only_drift = _bundle()[0]
    got = remediator.remediate_prepared(drift_doc=only_drift)
    for kind in ("restore_flow_step", "serialize_change_conflict", "serialize_flow_conflict", "fix_new_drift"):
        assert got["by_kind"][kind] == 0, f"缺省来源时 {kind} 应恰为 0，实际 {got['by_kind'][kind]}"


# --- ⑤ 断言 ------------------------------------------------------------------------


def test_advisory_declaration_and_no_gate() -> None:
    """⑤ 咨询式声明与无门禁：note 为写死常量（同源）且含三句声明；state 仅两值；无判定字段（AST/文本双查）。"""
    empty = remediator.remediate_prepared(drift_doc=_empty_drift())
    doc = remediator.remediate_prepared(drift_doc=_bundle()[0], flow_doc=_bundle()[1])
    assert empty["note"] is remediator._SUMMARY_NOTE, "顶层 note 应为写死常量（同一对象，非按内容生成）"
    assert doc["note"] is remediator._SUMMARY_NOTE, "顶层 note 应与全绿路径同一对象"
    for phrase in _SUMMARY_PHRASES:
        assert phrase in empty["note"], f"顶层 note 应含咨询式声明 {phrase!r}，实际 {empty['note']!r}"
    assert set(empty["state"]) and empty["state"] in ("clear", "actionable"), \
        f"state 仅可取 clear / actionable 两值，实际 {empty['state']!r}"
    assert doc["state"] in ("clear", "actionable"), f"state 仅可取 clear / actionable 两值，实际 {doc['state']!r}"

    src = _module_source(_TARGET_MODULE)
    assert "verdict" not in src, "纠偏指令生成器**不得**产出判定字段 `verdict`（咨询式、无门禁）"
    keys = _dict_keys(src)
    gate = sorted(keys & set(_GATE_TOKENS))
    assert gate == [], f"字典字面量不得含判定字段名（AST 口径），实际 {gate}"


# --- ⑥ 断言（夹具数据见上 `_DESIGN` / `_FLOW` / `_DIFF_CHANGES`）----------------------


def test_cli_and_exit_codes() -> None:
    """⑥ CLI 与退出码回归：既有 7 命令 + `remediate` 的 stdout 与库输出逐字节一致、无 `\\r\\n`；错误 1；用法 2。"""
    with tempfile.TemporaryDirectory() as td:
        root, design, flow_doc, diffs = _fixture(
            Path(td), design_text=_DESIGN, flow_text=_FLOW, changes=_DIFF_CHANGES
        )

        cases = (
            (("parse", str(design)), parser.to_json(parser.parse_file(design))),
            (("graph", str(root)), graph_builder.to_json(graph_builder.build_graph(root))),
            (("drift", str(root), str(design)), drift.to_json(drift.analyze(root, design))),
            (("sync", str(root), str(design)), sync.to_json(sync.snapshot(root, design))),
            (
                ("impact", str(diffs["A"]), str(root), str(design)),
                impact_analyzer.to_json(impact_analyzer.analyze_files(diffs["A"], root, design)),
            ),
            (("flow", str(flow_doc), str(root)), flow.to_json(flow.analyze(flow_doc, root))),
            (("view", str(root), str(design)), viewer.render_html(viewer.analyze(root, design))),
            (("remediate", str(root), str(design)), remediator.to_json(remediator.remediate(root, design))),
        )
        for args, expected in cases:
            rc, out, err = _cli(*args)
            assert rc == 0, f"{args} 退出码应为 0，实际 {rc}；stderr={err[-200:]!r}"
            assert out == expected.encode("utf-8"), f"{args} stdout 应与库输出逐字节一致"
            assert b"\r\n" not in out, f"{args} stdout 不得含 CRLF（字节稳定写盘）"

        rc, _out, _err = _cli("remediate", str(root), str(Path(td) / "nope.md"))
        assert rc == 1, f"输入错误应退出码 1，实际 {rc}"
        for bad in (
            ("remediate", str(root)),
            ("remediate", str(root), str(design), "--diff", str(diffs["A"])),
            ("remediate", str(root), str(design), "--plan", str(diffs["A"])),
        ):
            rc, _out, _err = _cli(*bad)
            assert rc == 2, f"用法错误 {bad} 应退出码 2（`--diff` / `--plan` 依附 `--flow`），实际 {rc}"


# --- ⑦ / ⑧ 36 个无需命令行参数的自测（`m2` / `m3` 需代码根，见 ⑧）；条数为**实测** ------------


def test_existing_selftests_regression() -> None:
    """⑦ 既有自测零修订：36 个无需参数的自测各按实测条数全绿（经共享 `assert_regression`）。"""
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
        test_unique_implementation_and_separation,
        test_translation_accuracy,
        test_bounded_traceable_deterministic_and_dogfood,
        test_empty_input_not_misreported,
        test_advisory_declaration_and_no_gate,
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
