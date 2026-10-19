"""M39 纠偏指令生成器：把既有判定产物翻译为有界、可追溯、咨询式的纠偏指令。

为什么需要它（问题背景，大白话）：
    路线图闭环是「传感器 → 控制器 → 执行器 → 被控对象 → 反馈」。本仓此前只建成**传感器**：
    `drift`（失联锚）/ `impact`（影响面）/ `flow`（断链步骤）/ `conflict`（冲突对）/ `sync`（基线增量）
    都**能报出偏差**，却**没有任何件把偏差翻译成「下一步该做什么」**——链路停在观测这一环，
    永远走不到纠偏。本模块补上这一环的**策略半边**：只做**翻译**，不新增任何判定。

设计口径（对齐 `X产品化-M39设计稿-v1.md` §四，写死）：
    ① 逐源独立翻译（§4.1）：每条来源产物字段 → 一条指令；`target` 恰 1 个标量、`evidence` 逐键原样取；
    ② 有界：指令集规模由输入决定（每条发现至多 1 条指令）；
    ③ 可追溯：`evidence` **不**重算、**不**补算；④ 确定性：同一输入两次调用逐字节相同（排序写死）；
    ⑤ 只读：不写盘、不建临时目录、不起子进程；
    ⑥ 咨询式：只产出建议，**不**新增判定、**不**做门禁、**不**阻断合并、**不**自动执行（§六）；
    ⑦ 采集 / 构造分列（M36 口径的直接继承）：`remediate_prepared` 为纯构造入口（体内**零采集**），
       `remediate` 为薄编排——同一份设计文档只解析一次、依赖图只建一次、流程文档只采一次；
       基线增量复用**同一次** `drift` 采集（`sync.snapshot_from_drift`，M11 口径）。

**实现期口径校正（以实测为准；笔三回写设计稿 / 路线图）**：设计稿 §3.2 字面写「`impact_analyzer.prepare`
只在给了 `--plan` 时调用」，与本模块 §2.2 第 3 条「同一份设计文档各只采集一次」存在张力——`prepare`
会**再**解析一次设计文档。故按更强的 §2.2 落地：`--plan` 路径改用
`impact_analyzer.prepare_from_parts(graph_builder.build_graph(code_root), prepared["design"])`，
**复用** `drift.prepare` 已采到的 `design`（同一份设计文档只解析一次）。

隔离约定：本模块**不写死**任何冻结链路径；代码根 / 设计文档一律由调用方传入
（由 M0 自测第三条校验本包源码不含冻结链目录名）。仅依赖 Python 标准库与包内既有模块。
"""

from __future__ import annotations

from pathlib import Path

from . import conflict, drift, flow, graph_builder, impact_analyzer, sync, textio

# 来源顺序（§4.4 排序第一关键字；亦为 §4.3 汇总 by_kind 的分组依据）
SOURCE_ORDER = ("drift", "flow", "conflict", "baseline")

# 指令类别顺序（§4.4 排序第二关键字；§4.3 by_kind 六键**始终存在**）
KIND_ORDER = (
    "restore_dangling_anchor",
    "fix_unanchored_evidence",
    "restore_flow_step",
    "serialize_change_conflict",
    "serialize_flow_conflict",
    "fix_new_drift",
)

# 源 → 该类源的 kind 元组（分派与断言用；与 §4.1 表逐行对应）
KIND_BY_SOURCE = {
    "drift": ("restore_dangling_anchor", "fix_unanchored_evidence"),
    "flow": ("restore_flow_step",),
    "conflict": ("serialize_change_conflict", "serialize_flow_conflict"),
    "baseline": ("fix_new_drift",),
}

# kind → target_kind（§4.2；按来源分组：drift / baseline 同为 anchor）
KIND_TARGET_KIND = {
    "restore_dangling_anchor": "anchor",
    "fix_unanchored_evidence": "anchor",
    "restore_flow_step": "flow_step",
    "serialize_change_conflict": "changeset_pair",
    "serialize_flow_conflict": "changeset_pair",
    "fix_new_drift": "anchor",
}

# kind → 写死的固定短句（§4.2：note 不按内容生成，非自由生成）
KIND_NOTE = {
    "restore_dangling_anchor": "建议恢复该失联锚指向的代码证据（锚路径已失联）。",
    "fix_unanchored_evidence": "建议为该证据补一条可定位的代码锚（当前无锚，不参与活性判定）。",
    "restore_flow_step": "建议恢复该流程步骤锚指向的代码证据（步骤锚已断链）。",
    "serialize_change_conflict": "建议把这对改动改为串行（二者触碰同一文件或同一条目）。",
    "serialize_flow_conflict": "建议把这对改动改为串行（二者触碰同一流程步骤或波及同一流程）。",
    "fix_new_drift": "建议优先处置该失联锚（相对基线为本轮新增）。",
}

# §4.3 顶层 note：写死常量（含「不自动执行 / 不阻断合并 / 不表示设计完整或正确」）
_SUMMARY_NOTE = (
    "本指令集为咨询式建议：不自动执行、不阻断合并、不表示设计完整或正确；"
    "clear 仅表示本次口径下无待处置项。"
)

STATE_CLEAR = "clear"
STATE_ACTIONABLE = "actionable"


class RemediatorError(ValueError):
    """判定产物不合口径、或参数组合非法时抛出（调用方统一按退出码 1 处理）。"""


def _directive(source: str, kind: str, target: str, evidence: dict) -> dict:
    """按 §4.2 构造一条指令记录：`directive_id` 由内容派生（非序号 ⇒ 确定性）。"""
    return {
        "directive_id": f"{source}:{kind}:{target}",
        "source": source,
        "kind": kind,
        "target_kind": KIND_TARGET_KIND[kind],
        "target": target,
        "evidence": evidence,
        "note": KIND_NOTE[kind],
    }


def _from_drift(doc: dict) -> list[dict]:
    """drift → 失联锚（**全量**口径）+ 无锚证据 两类指令（§4.1）。"""
    out: list[dict] = []
    for r in doc["dangling_anchors"]:
        out.append(
            _directive(
                "drift",
                "restore_dangling_anchor",
                f"{r['constraint_id']}@{r['evidence']}",
                {"anchor": r["anchor"], "match_kind": r["match_kind"], "reason": r["reason"]},
            )
        )
    for r in doc["unanchored_evidence"]:
        out.append(
            _directive(
                "drift",
                "fix_unanchored_evidence",
                f"{r['constraint_id']}@{r['evidence']}",
                {"evidence": r["evidence"]},
            )
        )
    return out


def _from_flow(doc: dict) -> list[dict]:
    """flow → 断链步骤 一类指令（§4.1；取自 `impact.dangling_steps`；无 `impact` 即无该来源）。"""
    impact = doc.get("impact")
    if not impact:
        return []
    return [
        _directive(
            "flow",
            "restore_flow_step",
            f"{r['flow_id']}/{r['step_id']}",
            {"anchor": r["anchor"]},
        )
        for r in impact["dangling_steps"]
    ]


def _from_conflict(doc: dict) -> list[dict]:
    """conflict → 文件/条目层冲突对 + 流程层冲突对 两类指令（§4.1；无 `flow_conflict` 键即后者恒空）。"""
    out: list[dict] = [
        _directive(
            "conflict",
            "serialize_change_conflict",
            f"{r['left']}<>{r['right']}",
            {
                "kinds": r["kinds"],
                "shared_files": r["shared_files"],
                "shared_entries": r["shared_entries"],
            },
        )
        for r in doc["conflicts"]
    ]
    flow_conflict = doc.get("flow_conflict")
    if flow_conflict:
        out.extend(
            _directive(
                "conflict",
                "serialize_flow_conflict",
                f"flow:{r['left']}<>{r['right']}",
                {
                    "kinds": r["kinds"],
                    "shared_steps": r["shared_steps"],
                    "shared_flows": r["shared_flows"],
                },
            )
            for r in flow_conflict["conflicts"]
        )
    return out


def _from_baseline(doc: dict) -> list[dict]:
    """baseline（sync 比对文档）→ 本轮新增失联 一类指令（§4.1；取自 `newly_dangling`）。"""
    return [
        _directive(
            "baseline",
            "fix_new_drift",
            f"{r['constraint_id']}@{r['evidence']}",
            {"evidence": r["evidence"]},
        )
        for r in doc["newly_dangling"]
    ]


def remediate_prepared(
    *,
    drift_doc: dict,
    flow_doc: dict | None = None,
    conflict_doc: dict | None = None,
    baseline_doc: dict | None = None,
) -> dict:
    """**纯构造入口**：体内**零采集**（不建图 / 不解析文档 / 不调 prepare），只做逐源翻译 + 汇总排序。

    `flow_doc` / `conflict_doc` / `baseline_doc` 缺省时对应 kind 恒 0（§4.1 末段：缺失按「无该来源」处理，非报错）。
    """
    directives: list[dict] = []
    directives += _from_drift(drift_doc)
    if flow_doc is not None:
        directives += _from_flow(flow_doc)
    if conflict_doc is not None:
        directives += _from_conflict(conflict_doc)
    if baseline_doc is not None:
        directives += _from_baseline(baseline_doc)

    directives.sort(
        key=lambda d: (SOURCE_ORDER.index(d["source"]), KIND_ORDER.index(d["kind"]), d["target"])
    )

    by_kind = {kind: 0 for kind in KIND_ORDER}
    for d in directives:
        by_kind[d["kind"]] += 1

    return {
        "state": STATE_ACTIONABLE if directives else STATE_CLEAR,
        "directive_count": len(directives),
        "by_kind": by_kind,
        "directives": directives,
        "note": _SUMMARY_NOTE,
    }


def remediate(
    code_root: str | Path,
    design_doc: str | Path,
    flow_doc: str | Path | None = None,
    diff_file: str | Path | None = None,
    plan_path: str | Path | None = None,
    baseline_path: str | Path | None = None,
) -> dict:
    """**薄编排（采集入口）**：各来源各采集一次，再交给 `remediate_prepared` 构造。

    采集点写死：设计文档只解析一次（`drift.prepare`）；依赖图只在给了 `plan_path` 时构建一次
    （`graph_builder.build_graph`，经 `impact_analyzer.prepare_from_parts` 复用同一份 `design`）；
    流程文档采一次（`flow.prepare`）；基线增量复用**同一次** `drift` 采集（M11 口径）。

    `diff_file` / `plan_path` **依附** `flow_doc`（§3.3）：未给流程文档却给出二者即参数组合非法。
    """
    if (diff_file is not None or plan_path is not None) and flow_doc is None:
        raise RemediatorError("--diff / --plan 依附 --flow：未给流程文档时不得给出 diff 或分工计划")

    prepared = drift.prepare(code_root, design_doc)
    drift_doc = drift.analyze_prepared(prepared)

    flow_prepared = None
    flow_result = None
    if flow_doc is not None:
        flow_prepared = flow.prepare(flow_doc, code_root)
        flow_result = flow.analyze_prepared(flow_prepared, diff_file)

    conflict_doc = None
    if plan_path is not None:
        conflict_doc = conflict.analyze_plan_prepared(
            conflict.load_plan(plan_path),
            impact_analyzer.prepare_from_parts(graph_builder.build_graph(code_root), prepared["design"]),
            flow_prepared,
        )

    baseline_doc = None
    if baseline_path is not None:
        baseline_doc = sync.compare_snapshots(
            sync.load_snapshot(baseline_path), sync.snapshot_from_drift(drift_doc)
        )

    return remediate_prepared(
        drift_doc=drift_doc,
        flow_doc=flow_result,
        conflict_doc=conflict_doc,
        baseline_doc=baseline_doc,
    )


def render_text(doc: dict) -> str:
    """确定性人类可读摘要（逐字节可断言）。"""
    lines = [f"remediate: {doc['state']} ({doc['directive_count']} directives)"]
    for kind in KIND_ORDER:
        lines.append(f"  {kind}: {doc['by_kind'][kind]}")
    for d in doc["directives"]:
        lines.append(f"  [{d['source']}/{d['kind']}] {d['target']}")
    lines.append(doc["note"])
    return "\n".join(lines) + "\n"


def to_json(doc: dict) -> str:
    """稳定序列化（委派 `textio.to_json`，与全仓既有模块同口径）。"""
    return textio.to_json(doc)
