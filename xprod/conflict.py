"""M7 并发改动冲突检测（分工边界校验）：给定一份「分工计划」（多份并发改动），报出相互冲突的改动对。

为什么需要它（问题背景，大白话）：
    「同一文件禁止多个任务并行修改；多窗口并行前必须先划清分工边界」此前是一条**人工纪律**——
    谁跟谁撞车，全靠人自己核对。M7 把它变成**可运行、可断言**的静态检查：把每份改动各自
    「碰了哪些文件、命中哪些设计条目」算出来，两两求交集，交集非空即报冲突。

设计口径（对齐 `X产品化路线图-v1.md` §十一 M7 行与「判定口径（写死）」）：
    ① 输入 = 1 份**分工计划 JSON**（列出 N 份改动，每份 = id + 一份统一 diff 文件路径），
       外加**代码根**与**设计文档**；每份改动复用 M3 影响分析器解析 diff 与命中条目；
    ② 冲突只有两类，均按**集合交集非空**判定：
         `file`  = 两份改动的**直接变更文件**（M3 `changed_files`，不含反向闭包传播结果）有交集；
         `entry` = 两份改动的**命中条目**（M3 `affected_entries[*].constraint_id`）有交集；
       两类可**同时**发生；
    ③ **下游「受影响文件」重合不算冲突**：反向闭包结果是「会被别人的改动波及」的**弱证据**，
       与「我改了它」强度不同；升级为冲突会造成影响面二次放大（与 M3 既有理由一致），故显式排除；
    ④ 只比较**不同 id** 的改动两两组合，同一份改动内部不算冲突；
    ⑤ 判定：存在任一冲突对 → `conflict`，否则 `clear`。`clear` **只**表示「本次分工计划内部
       无冲突」，**不表示**「合并安全」；
    ⑥ 输出默认稳定 JSON，`--text` 给人类可读清单。

M14 扩展（流程层并发冲突检测；对齐路线图 §十八 M14 行与设计稿 `X产品化-M14设计稿-v1.md` §四）：
    ⑦ **可选**流程文档：给了才计算流程层，并在输出末尾**追加** `flow_of_changesets` / `flow_conflict`
       两个键；**未给时输出与 M7 逐字节一致**（流程层键**不出现**，而非出现并置 `null`）；
    ⑧ 流程面**一律**取自 M12 `flow` 的判定（M15 起：`flow.prepare` 对同一份流程文档**只做一次**，
       再对每份 diff 各做一次 `flow.analyze_prepared`，取其 `direct_steps` / `affected_steps`），
       **零新解析**——本模块只做「两层结果相交」，不持有第二份流程判定实现；
    ⑨ 流程层冲突只有两类：`step` = 两份改动 `direct_steps` 交集非空（强）；`flow` = 两份改动
       `affected_steps` 所属流程 id 交集非空（弱）。`unanchored` 步骤**不参与**（无锚即无「命中」
       可言，由 M12 ③ 排除）；**「断链」这一事实本身也不是判据**——`dangling_steps` 不进入任何比较
       （⚠ 一个失联步骤若其锚路径恰在变更文件集合里，仍会按 M12 ③ 计入 `direct_steps`，
       那是「谁改了它」的事实，不是「锚失联」的事实）；
    ⑩ 两层判定**并列、不合并**：顶层 `verdict` 语义**一字不改**，流程层判定**另置**于
       `flow_conflict.verdict`——把「波及同一流程」这种弱证据并进强判定会造成影响面二次放大
       （与 M3 排除反向闭包传播同理由）。

M16 扩展（条目层采集复用；对齐路线图 §二十 M16 行与设计稿 `X产品化-M16设计稿-v1.md` §四）：
    ⑪ 条目层同 M15 口径：`impact_analyzer.prepare`（建图 + 解析设计文档，两者**与 diff 无关**）
       **只做一次**，再对每份 diff 各做一次 `impact_analyzer.analyze_prepared`；**零新解析**。
       diff 读口径**唯一收口**在 `impact_analyzer.read_diff`；复用**写在调用点**，不引入隐式缓存。
       M7 / M14 输出**逐字节不变**。

为什么这样定：
    * 冲突对按 (left, right) 字典序输出、共享集合排序，保证同输入**逐字节可复现**；
    * 分工计划里的改动按 id 升序规范化，使输出的**键序与分组不依赖输入书写顺序**；
    * 把「我改了它」与「它会被波及」分开（同 M3），避免把传播距离当成等价证据。

路径规则（写死）：计划文件中的 `diff` 若为**相对路径**，**相对计划文件所在目录**解析
（便于夹具整包搬迁）；**绝对路径**原样使用。

隔离约定：本模块**不写死**任何冻结链路径；代码根 / 设计文档 / 计划路径一律由调用方传入
（由 M0 自测第三条校验本包源码不含冻结链目录名）。仅依赖 Python 标准库。
"""

from __future__ import annotations

import json
from pathlib import Path

from . import flow, impact_analyzer

FILE_KIND = "file"
ENTRY_KIND = "entry"
# 冲突类别在输出中的固定顺序：先文件、后条目，保证「两类同时命中」时 kinds 稳定
KIND_ORDER = (FILE_KIND, ENTRY_KIND)

# M14 流程层冲突类别：与文件 / 条目层**并列**，单独输出、不并入顶层 verdict
STEP_KIND = "step"
FLOW_KIND = "flow"
# 流程层类别顺序同样写死：先 step（强：同时直接改同一步骤）、后 flow（弱：同时波及同一流程）
FLOW_KIND_ORDER = (STEP_KIND, FLOW_KIND)

VERDICT_CONFLICT = "conflict"
VERDICT_CLEAR = "clear"


class ConflictError(ValueError):
    """分工计划不合法（不可读、JSON 坏、缺字段、id 重复/为空、改动数为零、diff 不存在）时抛出。"""


def load_plan(path: str | Path) -> dict:
    """读取分工计划 JSON，返回 `{plan_id, changesets}`；changesets 按 id 升序规范化。

    `diff` 值返回**已解析的绝对路径**：相对路径相对计划文件所在目录解析，绝对路径原样使用。
    任何不合格式的输入都抛 `ConflictError`，绝不静默放行（缺字段最容易被忽略，故列为首要校验）。
    """
    p = Path(path)
    try:
        raw = p.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise ConflictError(f"分工计划不可读：{p}（{exc}）") from exc
    try:
        doc = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ConflictError(f"分工计划不是合法 JSON：{p}（{exc}）") from exc
    if not isinstance(doc, dict):
        raise ConflictError(f"分工计划顶层应为对象：{p}")

    plan_id = doc.get("plan_id")
    if plan_id is not None and not isinstance(plan_id, str):
        raise ConflictError(f"plan_id 若给出必须为字符串：{p}")

    items = doc.get("changesets")
    if not isinstance(items, list) or not items:
        raise ConflictError(f"分工计划必须含非空数组 changesets：{p}")

    base = p.parent
    changesets: list[dict] = []
    seen: set[str] = set()
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            raise ConflictError(f"changesets[{i}] 应为对象")
        cid = item.get("id")
        diff = item.get("diff")
        if not isinstance(cid, str) or not cid.strip():
            raise ConflictError(f"changesets[{i}] 的 id 必须是非空字符串")
        if not isinstance(diff, str) or not diff.strip():
            raise ConflictError(f"changesets[{i}]（{cid}）的 diff 必须是非空字符串")
        if cid in seen:
            raise ConflictError(f"改动 id 重复：{cid}")
        seen.add(cid)
        dp = Path(diff)
        if not dp.is_absolute():
            dp = base / dp
        if not dp.is_file():
            raise ConflictError(f"改动 {cid} 的 diff 文件不存在：{dp}")
        changesets.append({"id": cid, "diff": dp})

    changesets.sort(key=lambda c: c["id"])
    return {"plan_id": plan_id, "changesets": changesets}


def _pairwise_conflicts(summaries: list[dict]) -> list[dict]:
    """对（已按 id 升序的）改动摘要做两两比较，返回冲突对列表。

    仅比较不同 id；`shared_files` / `shared_entries` 均为排序后的交集，空则不进冲突对。
    """
    files = {s["id"]: set(s["changed_files"]) for s in summaries}
    entries = {s["id"]: set(s["entries"]) for s in summaries}
    ids = [s["id"] for s in summaries]

    conflicts: list[dict] = []
    for a in range(len(ids)):
        for b in range(a + 1, len(ids)):
            left, right = ids[a], ids[b]  # ids 已升序，故 left < right
            shared_files = sorted(files[left] & files[right])
            shared_entries = sorted(entries[left] & entries[right])
            if not shared_files and not shared_entries:
                continue
            kinds = [
                kind
                for kind in KIND_ORDER
                if (kind == FILE_KIND and shared_files) or (kind == ENTRY_KIND and shared_entries)
            ]
            conflicts.append(
                {
                    "left": left,
                    "right": right,
                    "kinds": kinds,
                    "shared_files": shared_files,
                    "shared_entries": shared_entries,
                }
            )
    return conflicts


def _flow_layer(plan: dict, code_root: str | Path, flow_doc: str | Path) -> list[dict]:
    """逐改动取流程面：**一律**取自 `flow` 的判定，不重算、不另造。

    为什么用「采集一次 + 逐改动构造」（M15）：流程解析与「直接命中 ∪ 正向下游闭包」的判定口径
    只能有一个源头（M12），此处若自己复刻，就会重演「同一规则两处实现 → 隐性漂移」。
    而同一份流程文档在本工作流里要供 N 份改动复用——此前是逐改动各调一次 `flow.analyze`，
    于是「读 + 解析流程文档、扫树、判锚活性」这三件**与 diff 无关**的事被重复了 N 次。
    M15 起改为：`flow.prepare` **只做一次**，再对每份 diff 各做一次 `flow.analyze_prepared`。
    复用**写在调用点**（本函数显式持有 `prepared`），不引入任何隐式缓存；M14 的输出**逐字节不变**。
    `affected_steps` 与 `direct_steps` 在 `flow` 内已排序，此处原样透传以保确定性。
    """
    prepared = flow.prepare(flow_doc, code_root)
    rows: list[dict] = []
    for change in plan["changesets"]:
        impact = flow.analyze_prepared(prepared, change["diff"])["impact"]
        affected = list(impact["affected_steps"])
        rows.append(
            {
                "id": change["id"],
                "direct_steps": list(impact["direct_steps"]),
                "affected_steps": affected,
                "flow_ids": sorted({a["flow_id"] for a in affected}),
            }
        )
    return rows


def _flow_conflicts(rows: list[dict]) -> list[dict]:
    """对（已按 id 升序的）流程面做两两比较，返回流程层冲突对列表。

    `step` = `direct_steps` 交集非空（两个任务同时**直接改**同一流程步骤）；
    `flow` = `affected_steps` 所属流程 id 交集非空（两个任务同时**波及**同一流程）。
    本函数**只看** `direct_steps` / `affected_steps` 两项：`unanchored` 步骤由 M12 ③ 排除、
    天然不在其中；`dangling_steps` 是「锚失联」的事实，**不**进入本函数的任何输入，
    故「断链」不构成冲突判据（但失联步骤若其锚路径恰在变更文件里，仍会按 M12 ③ 计入 `direct_steps`）。
    """
    steps = {r["id"]: {(d["flow_id"], d["step_id"]) for d in r["direct_steps"]} for r in rows}
    flows = {r["id"]: set(r["flow_ids"]) for r in rows}
    ids = [r["id"] for r in rows]

    conflicts: list[dict] = []
    for a in range(len(ids)):
        for b in range(a + 1, len(ids)):
            left, right = ids[a], ids[b]  # ids 已升序，故 left < right
            shared_steps = sorted(steps[left] & steps[right])
            shared_flows = sorted(flows[left] & flows[right])
            if not shared_steps and not shared_flows:
                continue
            kinds = [
                kind
                for kind in FLOW_KIND_ORDER
                if (kind == STEP_KIND and shared_steps) or (kind == FLOW_KIND and shared_flows)
            ]
            conflicts.append(
                {
                    "left": left,
                    "right": right,
                    "kinds": kinds,
                    "shared_steps": [{"flow_id": f, "step_id": s} for (f, s) in shared_steps],
                    "shared_flows": shared_flows,
                }
            )
    return conflicts


_FLOW_CLEAR_NOTE = "note: clear 仅表示本次分工计划内部流程层无冲突，不表示合并安全"


def analyze_plan(
    plan_path: str | Path,
    code_root: str | Path,
    design_doc: str | Path,
    flow_doc: str | Path | None = None,
) -> dict:
    """分析一份分工计划，返回键序固定、可逐字节复现的结果文档。

    每份改动都经 M3 影响分析器解析：直接变更文件来自 diff，命中条目来自「证据锚 ∩ 直接变更文件」。

    M14：给了 `flow_doc` 才计算**流程层**并在输出末尾追加两个键（`flow_of_changesets` /
    `flow_conflict`）；**未给时输出与 M7 逐字节一致**（流程层键**不出现**，而不是出现并置 `null`）——
    这样既有断言与既有页面对照一律不受影响。流程层判定**不并入**顶层 `verdict`：把「波及同一流程」
    这种弱证据并进文件/条目层的强判定，会造成影响面二次放大（与 M3 排除反向闭包传播同理由）。

    M16：条目层改用「采集一次 + 逐改动构造」——同一对 `(代码根, 设计文档)` 供 N 份改动复用，
    `impact_analyzer.prepare` **只做一次**（建图 + 解析设计文档，两者**与 diff 无关**），
    再对每份改动各做一次 `impact_analyzer.analyze_prepared`（读该 diff 文件、命中条目、反向闭包）。
    复用**写在调用点**（本函数显式持有 `impact_prepared`），不引入任何隐式缓存；
    diff 读口径**唯一收口**在 `impact_analyzer.read_diff`。M7 / M14 输出**逐字节不变**。
    中间体变量名用 `impact_prepared`，与 `_flow_layer` 内的 `prepared`（流程面）区分，避免混淆。
    """
    plan = load_plan(plan_path)

    impact_prepared = impact_analyzer.prepare(code_root, design_doc)
    summaries: list[dict] = []
    for change in plan["changesets"]:
        doc = impact_analyzer.analyze_prepared(
            impact_prepared, impact_analyzer.read_diff(change["diff"])
        )
        summaries.append(
            {
                "id": change["id"],
                "changed_file_count": doc["changed_file_count"],
                "changed_files": doc["changed_files"],
                "entry_count": len(doc["affected_entries"]),
                "entries": [e["constraint_id"] for e in doc["affected_entries"]],
            }
        )

    conflicts = _pairwise_conflicts(summaries)
    result = {
        "plan_id": plan["plan_id"],
        "changeset_count": len(summaries),
        "changesets": summaries,
        "conflict_count": len(conflicts),
        "conflicts": conflicts,
        "verdict": VERDICT_CONFLICT if conflicts else VERDICT_CLEAR,
    }
    if flow_doc is not None:
        rows = _flow_layer(plan, code_root, flow_doc)
        flow_conflicts = _flow_conflicts(rows)
        result["flow_of_changesets"] = rows
        result["flow_conflict"] = {
            "conflict_count": len(flow_conflicts),
            "conflicts": flow_conflicts,
            "verdict": VERDICT_CONFLICT if flow_conflicts else VERDICT_CLEAR,
            "note": _FLOW_CLEAR_NOTE,
        }
    return result


_CLEAR_NOTE = "note: clear 仅表示本次分工计划内部无冲突，不表示合并安全"


def render_text(doc: dict) -> str:
    """把结果文档渲染为确定性 ASCII 清单（人类可读；逐字节可断言）。

    各段固定打印计数（空段也打印），每份改动的文件/条目、每个冲突对的共享集合均排序。
    M14：仅当文档含流程层键时，才在 M7 原有各行**之后**追加流程层两段——原有各行**逐行不变**，
    故「未给 `--flow`」时本函数输出与 M7 逐字节一致。
    """
    lines = [f"changesets ({doc['changeset_count']}):"]
    for s in doc["changesets"]:
        lines.append(
            f"    {s['id']}  files {s['changed_file_count']}, entries {s['entry_count']}"
        )
        lines.extend(f"        file  {path}" for path in s["changed_files"])
        lines.extend(f"        entry {cid}" for cid in s["entries"])
    lines.append(f"conflicts ({doc['conflict_count']}):")
    for c in doc["conflicts"]:
        lines.append(f"    {c['left']} <> {c['right']}  kinds {','.join(c['kinds'])}")
        lines.extend(f"        shared file  {path}" for path in c["shared_files"])
        lines.extend(f"        shared entry {cid}" for cid in c["shared_entries"])
    lines.append(f"verdict: {doc['verdict']}")
    lines.append(_CLEAR_NOTE)

    if "flow_conflict" in doc:
        lines.append(f"flow layer per changeset ({len(doc['flow_of_changesets'])}):")
        for r in doc["flow_of_changesets"]:
            lines.append(
                f"    {r['id']}  direct {len(r['direct_steps'])}, affected {len(r['affected_steps'])}"
            )
            lines.extend(f"        direct   {d['flow_id']}/{d['step_id']}" for d in r["direct_steps"])
            lines.extend(f"        affected {d['flow_id']}/{d['step_id']}" for d in r["affected_steps"])
        flow_conflict = doc["flow_conflict"]
        lines.append(f"flow conflicts ({flow_conflict['conflict_count']}):")
        for c in flow_conflict["conflicts"]:
            lines.append(f"    {c['left']} <> {c['right']}  kinds {','.join(c['kinds'])}")
            lines.extend(f"        shared step  {s['flow_id']}/{s['step_id']}" for s in c["shared_steps"])
            lines.extend(f"        shared flow  {fid}" for fid in c["shared_flows"])
        lines.append(f"flow verdict: {flow_conflict['verdict']}")
        lines.append(flow_conflict["note"])
    return "\n".join(lines) + "\n"


def to_json(doc: dict) -> str:
    """稳定序列化：UTF-8、缩进 2、键序按插入顺序、末尾单换行（与 M1–M6 同口径）。"""
    return json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
