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

from . import impact_analyzer

FILE_KIND = "file"
ENTRY_KIND = "entry"
# 冲突类别在输出中的固定顺序：先文件、后条目，保证「两类同时命中」时 kinds 稳定
KIND_ORDER = (FILE_KIND, ENTRY_KIND)

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


def analyze_plan(plan_path: str | Path, code_root: str | Path, design_doc: str | Path) -> dict:
    """分析一份分工计划，返回键序固定、可逐字节复现的结果文档。

    每份改动都经 M3 影响分析器解析：直接变更文件来自 diff，命中条目来自「证据锚 ∩ 直接变更文件」。
    """
    plan = load_plan(plan_path)

    summaries: list[dict] = []
    for change in plan["changesets"]:
        doc = impact_analyzer.analyze_files(change["diff"], code_root, design_doc)
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
    return {
        "plan_id": plan["plan_id"],
        "changeset_count": len(summaries),
        "changesets": summaries,
        "conflict_count": len(conflicts),
        "conflicts": conflicts,
        "verdict": VERDICT_CONFLICT if conflicts else VERDICT_CLEAR,
    }


_CLEAR_NOTE = "note: clear 仅表示本次分工计划内部无冲突，不表示合并安全"


def render_text(doc: dict) -> str:
    """把结果文档渲染为确定性 ASCII 清单（人类可读；逐字节可断言）。

    各段固定打印计数（空段也打印），每份改动的文件/条目、每个冲突对的共享集合均排序。
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
    return "\n".join(lines) + "\n"


def to_json(doc: dict) -> str:
    """稳定序列化：UTF-8、缩进 2、键序按插入顺序、末尾单换行（与 M1–M6 同口径）。"""
    return json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
