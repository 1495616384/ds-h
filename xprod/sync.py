"""M10 同步基线比对：给锚活性加上**时间维**——把「现在活不活」升级为「**相对上次同步**变没变」。

为什么需要它（问题背景，大白话）：
    M8 只回答「锚现在还活着吗」。但「持续同步」真正想问的是「**从上次到现在，有没有锚悄悄死掉**」。
    没有时间维，人每次都得自己回忆上次是什么状态。本模块把锚活性存成**基线快照**，
    下次采集后与基线做**集合差**，直接报出：新增失联 / 恢复 / 证据增删 / 盲区变化。

设计口径（对齐 `X产品化路线图-v1.md` §十四 M10 行与「判定口径（写死）」）：
    ① 快照 = `drift` 结果的**稳定子集**：每条证据锚记 `(constraint_id, evidence, status)`
       （status ∈ active / dangling / unanchored）+ 盲区文件集合 + 若干计数；
       **不**记 `matched_files`（会因无关文件增删而抖动，属噪声）；
    ② 比对 = 以 `(constraint_id, evidence)` 为键的集合差；
    ③ 三态判定：任一**新增失联** → `regressed`；否则其余任一变化非空 → `changed`；否则 `unchanged`；
    ④ 确定性：一律排序、不写时间戳，同输入两次逐字节一致；⑤ 只读。

为什么这样定：
    * 记 `status` 而非 `matched_files`：把「事实的稳定性」放在第一位——无关文件增删不应制造同步噪声；
    * 用**集合差**而非「对比两份文本」：集合差天然可判定、可断言，且与 M7/M8 的集合口径一致。

隔离约定：本模块**不写死**任何冻结链路径；代码根 / 设计文档一律由调用方传入
（由 M0 自测第三条校验本包源码不含冻结链目录名）。仅依赖 Python 标准库。
"""

from __future__ import annotations

import json
from pathlib import Path

from . import drift, parser, textio

# 证据锚三态：与 M8 **同源**——三态字面量只允许有一个源头（`drift`），此处一律别名引用。
# 为什么不自己重写：同一状态名在多处各写一份，将来「改名 / 加态」必然只改到其中几处，
# 剩下的那份就悄悄分叉（本仓库已因同类问题吃过亏）；且 `_EVIDENCE_STATUSES` 若自持字面量，
# 校验集合会与真实取值来源脱钩——别名组合则不可能脱钩。
STATUS_ACTIVE = drift.STATUS_ACTIVE
STATUS_DANGLING = drift.STATUS_DANGLING
STATUS_UNANCHORED = drift.STATUS_UNANCHORED
_EVIDENCE_STATUSES = (STATUS_ACTIVE, STATUS_DANGLING, STATUS_UNANCHORED)

VERDICT_UNCHANGED = "unchanged"
VERDICT_CHANGED = "changed"
VERDICT_REGRESSED = "regressed"

_SYNC_NOTE = "note: unchanged 仅表示本次口径下相对基线无变化，不表示设计正确"

_SCALAR_KEYS = (
    "entry_count",
    "active_count",
    "dangling_count",
    "unanchored_count",
    "uncovered_file_count",
)


class SyncError(ValueError):
    """快照文件不合格式时抛出；代码根 / 设计文档的问题由 `drift` 与 M1 直接上抛。"""


def _anchor_key(record: dict) -> tuple[str, str]:
    """证据锚的比对键；同一键在两侧各只保留一条。

    M22：身份键口径由 `parser.evidence_key` **唯一提供**，本函数只委派（保留名与签名，
    调用点一字不改）。**必须**写模块限定名，结构断言与受控注入才能指向「共享实现」。
    """
    return parser.evidence_key(record)


def snapshot_from_drift(d: dict) -> dict:
    """由**已有的** `drift` 结果构造锚活性快照。

    单独成函数，供已持有 `drift` 结果的调用方（如可视面）复用：既避免对同一次采集
    重复跑 `drift` 的二次计算，也避免两条路径各自拼快照导致口径分叉。
    """
    records: list[dict] = []
    for r in d["active_anchors"]:
        records.append({"constraint_id": r["constraint_id"], "evidence": r["evidence"], "status": STATUS_ACTIVE})
    for r in d["dangling_anchors"]:
        records.append({"constraint_id": r["constraint_id"], "evidence": r["evidence"], "status": STATUS_DANGLING})
    for r in d["unanchored_evidence"]:
        records.append({"constraint_id": r["constraint_id"], "evidence": r["evidence"], "status": STATUS_UNANCHORED})
    records.sort(key=_anchor_key)

    return {
        "entry_count": d["entry_count"],
        "active_count": d["active_count"],
        "dangling_count": d["dangling_count"],
        "unanchored_count": len(d["unanchored_evidence"]),
        "uncovered_file_count": d["uncovered_file_count"],
        "anchors": records,
        "uncovered_files": list(d["uncovered_files"]),
    }


def snapshot(code_root: str | Path, design_doc: str | Path) -> dict:
    """采集锚活性基线快照（仅记 `(条目id, 证据原文, 状态)` 这一稳定子集）。

    薄封装：把 `drift` 采集与快照构造串起来；需要复用已算好的 `drift` 结果时，
    直接调用 `snapshot_from_drift`。
    """
    return snapshot_from_drift(drift.analyze(code_root, design_doc))


def save_snapshot(path: str | Path, snap: dict) -> None:
    """把快照写成 UTF-8 稳定 JSON（缩进 2、末尾单换行）。

    走 `textio.save_text`（字节写）：Windows 文本模式会把换行符翻译成回车加换行，
    使落盘字节与 `to_json` 输出不一致，破坏快照的逐字节可复现性。
    """
    textio.save_text(path, to_json(snap))


def load_snapshot(path: str | Path) -> dict:
    """读取并校验快照文件；结构不符即抛 SyncError。"""
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SyncError(f"快照文件不是合法 JSON：{exc}") from exc
    if not isinstance(raw, dict):
        raise SyncError("快照顶层必须是 JSON 对象")
    if not isinstance(raw.get("anchors"), list):
        raise SyncError("快照缺少 anchors 数组")
    for i, a in enumerate(raw["anchors"]):
        if not isinstance(a, dict):
            raise SyncError(f"anchors[{i}] 不是对象")
        for k in ("constraint_id", "evidence", "status"):
            if not isinstance(a.get(k), str) or not a[k]:
                raise SyncError(f"anchors[{i}] 的 {k} 必须是非空字符串")
        if a["status"] not in _EVIDENCE_STATUSES:
            raise SyncError(f"anchors[{i}] 的 status 取值 {a['status']!r} 不在 {_EVIDENCE_STATUSES}")
    if not isinstance(raw.get("uncovered_files"), list):
        raise SyncError("快照缺少 uncovered_files 数组")
    missing = [k for k in _SCALAR_KEYS if not isinstance(raw.get(k), int)]
    if missing:
        raise SyncError(f"快照缺少整数计数：{missing}")
    return raw


def _as_map(snap: dict) -> dict[tuple[str, str], str]:
    """把快照的 anchors 拉平成 {键: 状态}；同键重复时后者覆盖前者（写入前已排序，行为确定）。"""
    return {_anchor_key(a): a["status"] for a in snap["anchors"]}


def compare_snapshots(base: dict, cur: dict) -> dict:
    """以 `(条目id, 证据原文)` 为键做集合差，返回键序固定、可逐字节复现的增量文档。"""
    base_map = _as_map(base)
    cur_map = _as_map(cur)
    keys = sorted(set(base_map) | set(cur_map))

    newly_dangling: list[dict] = []
    recovered: list[dict] = []
    added: list[dict] = []
    removed: list[dict] = []
    for key in keys:
        rec = {"constraint_id": key[0], "evidence": key[1]}
        if key not in base_map:
            added.append(rec)
        elif key not in cur_map:
            removed.append(rec)
        if cur_map.get(key) == STATUS_DANGLING and base_map.get(key) != STATUS_DANGLING:
            newly_dangling.append(rec)
        if base_map.get(key) == STATUS_DANGLING and key in cur_map and cur_map[key] != STATUS_DANGLING:
            recovered.append(rec)

    base_uncovered = set(base["uncovered_files"])
    cur_uncovered = set(cur["uncovered_files"])
    uncovered_added = sorted(cur_uncovered - base_uncovered)
    uncovered_removed = sorted(base_uncovered - cur_uncovered)

    if newly_dangling:
        verdict = VERDICT_REGRESSED
    elif recovered or added or removed or uncovered_added or uncovered_removed:
        verdict = VERDICT_CHANGED
    else:
        verdict = VERDICT_UNCHANGED

    change_count = (
        len(newly_dangling)
        + len(recovered)
        + len(added)
        + len(removed)
        + len(uncovered_added)
        + len(uncovered_removed)
    )
    return {
        "verdict": verdict,
        "change_count": change_count,
        "baseline": {k: base[k] for k in _SCALAR_KEYS},
        "current": {k: cur[k] for k in _SCALAR_KEYS},
        "newly_dangling": newly_dangling,
        "recovered": recovered,
        "added_evidence": added,
        "removed_evidence": removed,
        "uncovered_added": uncovered_added,
        "uncovered_removed": uncovered_removed,
    }


def render_text(doc: dict) -> str:
    """把比对文档渲染为确定性 ASCII 清单（人类可读；逐字节可断言）。"""
    lines = [
        f"sync compare: {doc['baseline']['entry_count']} → {doc['current']['entry_count']} entries",
        f"  baseline: active {doc['baseline']['active_count']} / dangling {doc['baseline']['dangling_count']}"
        f" / unanchored {doc['baseline']['unanchored_count']}"
        f" / uncovered {doc['baseline']['uncovered_file_count']}",
        f"  current : active {doc['current']['active_count']} / dangling {doc['current']['dangling_count']}"
        f" / unanchored {doc['current']['unanchored_count']}"
        f" / uncovered {doc['current']['uncovered_file_count']}",
        f"newly dangling ({len(doc['newly_dangling'])}):",
    ]
    lines.extend(f"    {r['constraint_id']}  {r['evidence']}" for r in doc["newly_dangling"])
    lines.append(f"recovered ({len(doc['recovered'])}):")
    lines.extend(f"    {r['constraint_id']}  {r['evidence']}" for r in doc["recovered"])
    lines.append(f"added evidence ({len(doc['added_evidence'])}):")
    lines.extend(f"    {r['constraint_id']}  {r['evidence']}" for r in doc["added_evidence"])
    lines.append(f"removed evidence ({len(doc['removed_evidence'])}):")
    lines.extend(f"    {r['constraint_id']}  {r['evidence']}" for r in doc["removed_evidence"])
    lines.append(f"uncovered added ({len(doc['uncovered_added'])}):")
    lines.extend(f"    {path}" for path in doc["uncovered_added"])
    lines.append(f"uncovered removed ({len(doc['uncovered_removed'])}):")
    lines.extend(f"    {path}" for path in doc["uncovered_removed"])
    lines.append(f"verdict: {doc['verdict']}")
    lines.append(_SYNC_NOTE)
    return "\n".join(lines) + "\n"


def to_json(doc: dict) -> str:
    """稳定序列化：UTF-8、缩进 2、键序按插入顺序、末尾单换行（M21：口径由 `textio.to_json` 唯一提供，本函数只委派）。"""
    return textio.to_json(doc)
