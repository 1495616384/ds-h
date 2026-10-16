"""M12 业务流 / 数据流影响图：把设计文档中**显式声明**的流程解析为有向图，报出受影响步骤与断链步骤。

为什么需要它（问题背景，大白话）：
    M2 只看模块 import、M3 只看「文件 → 条目」——都**不是流程层**。缺了流程层，
    「这次改动会不会波及某条业务 / 数据流的哪一段」就无人能答。
    本模块补上流程层：**步骤 = 节点、流向 = 边**，每个步骤挂一条代码证据锚。

设计口径（对齐 `X产品化路线图-v1.md` §十六 M12 行与 `X产品化-M12设计稿-v1.md` §四）：
    ① 流程事实**仅**取自流程文档中**显式声明**的步骤与边，**不**从代码逆向推断；
    ② `changed_files` 复用 M3 的 `parse_unified_diff`（不另造 diff 解析）；
    ③ `direct_steps` = 锚命中「直接变更文件」的步骤（`unanchored` 步骤**不参与**命中）；
    ④ `affected_steps` = `direct_steps` ∪ 沿边**正向（下游）闭包**（改动向**下游**扩散；
       与 M3 的反向「谁依赖我」是**两个不同问题**，故不套用 M3 传播方向）；
    ⑤ `dangling_steps` = 锚在代码根**失联**的步骤（**断链**），**单列**、**不**并入 `verdict`；
    ⑥ `verdict` ∈ `clear` / `impacted`（`affected_steps` 非空即 `impacted`）；
    ⑦ 无 `--diff` 时 `impact` 为 `null`，只输出流程结构与步骤锚活性；
    ⑧ 确定性（排序、无时间戳，同输入两次**逐字节一致**）、只读。

流程文档格式（写死；与条目设计文档**分文件**——M1 解析器在首个条目之后遇到 `##` 行会报错）：

    ## FL-001 — 下单到发货

    - step:
      - S1: 校验库存 @ src/app/api.py
      - S2: 扣减库存 @ src/app/core.py
      - S4: 人工复核
    - edge:
      - S1 -> S2

隔离约定：本模块**不写死**任何冻结链路径；流程文档 / 代码根 / diff 一律由调用方传入
（由 M0 自测第三条校验本包源码不含冻结链目录名）。仅依赖 Python 标准库。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from . import drift, impact_analyzer, parser

STATUS_ACTIVE = "active"
STATUS_DANGLING = "dangling"
STATUS_UNANCHORED = "unanchored"

VERDICT_CLEAR = "clear"
VERDICT_IMPACTED = "impacted"

_HEADING = re.compile(r"^##\s+(?P<id>FL-\d{3,})\s+—\s+(?P<title>.+?)\s*$")
_SECTION = re.compile(r"^-\s+(?P<key>step|edge)\s*:\s*$")
_ITEM = re.compile(r"^[ \t]+-\s+(?P<value>.+?)\s*$")
_EDGE = re.compile(r"^(?P<a>[A-Za-z0-9_]+)\s*->\s*(?P<b>[A-Za-z0-9_]+)$")
_SID = re.compile(r"^[A-Za-z0-9_]+$")


class FlowError(ValueError):
    """流程文档不合格式 / 代码根不可用 / diff 不合法时抛出；diff 问题由 M3 直接上抛。"""


def _parse_step(value: str, line: int) -> dict:
    """把 `SID: 标签 [@ 证据串]` 解析为步骤记录；格式错即抛 FlowError。"""
    if ":" not in value:
        raise FlowError(f"第 {line} 行：步骤需写成 `<SID>: <标签> [@ <证据串>]`，实际 {value!r}")
    sid, rest = value.split(":", 1)
    sid, rest = sid.strip(), rest.strip()
    if not _SID.fullmatch(sid):
        raise FlowError(f"第 {line} 行：步骤 ID 必须为非空字母 / 数字 / 下划线，实际 {sid!r}")
    label, evidence = rest, None
    if " @ " in rest:
        label, evidence = (x.strip() for x in rest.split(" @ ", 1))
        if not evidence:
            raise FlowError(f"第 {line} 行：`@` 之后的证据串不得为空")
    if not label:
        raise FlowError(f"第 {line} 行：步骤 {sid} 的标签不得为空")
    return {"step_id": sid, "label": label, "evidence": evidence}


def _parse_edge(value: str, line: int) -> dict:
    """把 `A -> B` 解析为边记录；格式错即抛 FlowError。"""
    m = _EDGE.match(value)
    if not m:
        raise FlowError(f"第 {line} 行：边需写成 `<SID> -> <SID>`，实际 {value!r}")
    return {"from": m.group("a"), "to": m.group("b")}


def parse_flow_doc(text: str) -> list[dict]:
    """把流程文档文本解析为流程列表；不合格式即抛 FlowError。"""
    flows: list[dict] = []
    cur: dict | None = None
    seen: set[str] = set()

    def flush() -> None:
        if cur is None:
            return
        fid = cur["flow_id"]
        if not cur["steps"]:
            raise FlowError(f"流程 {fid}（第 {cur['line']} 行起）缺少 step 声明")
        sids = [s["step_id"] for s in cur["steps"]]
        dup = sorted({s for s in sids if sids.count(s) > 1})
        if dup:
            raise FlowError(f"流程 {fid} 中步骤 ID 重复：{dup}")
        known = set(sids)
        for e in cur["edges"]:
            for end in (e["from"], e["to"]):
                if end not in known:
                    raise FlowError(f"流程 {fid} 的边引用了未声明的步骤：{end!r}")
        flows.append(
            {
                "flow_id": fid,
                "title": cur["title"],
                "steps": cur["steps"],
                "edges": cur["edges"],
            }
        )

    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.rstrip()  # 只去尾部空白，保留缩进用于识别列表项
        if not line.strip():
            continue

        m = _HEADING.match(line)
        if m:
            flush()
            fid = m.group("id")
            if fid in seen:
                raise FlowError(f"第 {lineno} 行：流程 ID 重复：{fid}")
            seen.add(fid)
            cur = {
                "flow_id": fid,
                "title": m.group("title"),
                "steps": [],
                "edges": [],
                "section": None,
                "line": lineno,
            }
            continue

        if cur is None:
            if line.lstrip().startswith(("#", ">")):
                continue  # 首个流程之前的文档头 / 引用行，忽略
            raise FlowError(f"第 {lineno} 行：首个流程之前出现无法解析的内容：{line!r}")

        m = _SECTION.match(line)
        if m:
            key = m.group("key")
            if cur["section"] == key:
                raise FlowError(f"第 {lineno} 行：流程 {cur['flow_id']} 的 `{key}` 段重复")
            cur["section"] = key
            continue

        m = _ITEM.match(line)
        if m:
            if cur["section"] is None:
                raise FlowError(f"第 {lineno} 行：列表项出现在 step / edge 段之外（流程 {cur['flow_id']}）")
            if cur["section"] == "step":
                cur["steps"].append(_parse_step(m.group("value"), lineno))
            else:
                cur["edges"].append(_parse_edge(m.group("value"), lineno))
            continue

        raise FlowError(f"第 {lineno} 行：无法解析的行：{line!r}")

    flush()
    if not flows:
        raise FlowError("未解析到任何流程")
    return flows


def _status(anchor: str | None, files: list[str], file_set: set[str]) -> str:
    """步骤锚活性（口径与 M8 一致：文件系统存在性）。"""
    if anchor is None:
        return STATUS_UNANCHORED
    if anchor.endswith("/"):
        return STATUS_ACTIVE if any(f.startswith(anchor) for f in files) else STATUS_DANGLING
    return STATUS_ACTIVE if anchor in file_set else STATUS_DANGLING


def _impact(flows: list[dict], changed: list[str]) -> dict:
    """按「直接命中 ∪ 正向下游闭包」计算受影响步骤；断链单独列出。"""
    changed_set = set(changed)
    direct: list[dict] = []
    seeds_by_flow: dict[str, list[str]] = {}
    for flow in flows:
        fid = flow["flow_id"]
        for step in flow["steps"]:
            a = step["anchor"]
            if a is None:
                continue
            hit = (
                any(f.startswith(a) for f in changed_set)
                if a.endswith("/")
                else a in changed_set
            )
            if hit:
                direct.append({"flow_id": fid, "step_id": step["step_id"], "evidence": step["evidence"]})
                seeds_by_flow.setdefault(fid, []).append(step["step_id"])

    affected: set[tuple[str, str]] = {(d["flow_id"], d["step_id"]) for d in direct}
    for flow in flows:
        fid = flow["flow_id"]
        seeds = seeds_by_flow.get(fid)
        if not seeds:
            continue
        adj: dict[str, list[str]] = {}
        for e in flow["edges"]:
            adj.setdefault(e["from"], []).append(e["to"])
        queue = list(seeds)
        visited = set(seeds)
        while queue:
            node = queue.pop(0)
            for nxt in adj.get(node, []):
                if nxt not in visited:
                    visited.add(nxt)
                    affected.add((fid, nxt))
                    queue.append(nxt)

    dangling: list[dict] = []
    for flow in flows:
        for step in flow["steps"]:
            if step["status"] == STATUS_DANGLING:
                dangling.append(
                    {"flow_id": flow["flow_id"], "step_id": step["step_id"], "anchor": step["anchor"]}
                )

    affected_list = [{"flow_id": f, "step_id": s} for (f, s) in sorted(affected)]
    return {
        "changed_files": list(changed),
        "direct_steps": sorted(direct, key=lambda d: (d["flow_id"], d["step_id"])),
        "affected_steps": affected_list,
        "dangling_steps": dangling,
        "verdict": VERDICT_IMPACTED if affected_list else VERDICT_CLEAR,
    }


def analyze(
    flow_doc: str | Path,
    code_root: str | Path,
    diff_file: str | Path | None = None,
) -> dict:
    """解析流程文档、判定步骤锚活性；给了 `diff_file` 再算一次流程级影响。

    返回键序固定、可逐字节复现的文档；无 `diff_file` 时 `impact` 为 `None`。
    """
    root = Path(code_root)
    if not root.is_dir():
        raise FlowError(f"代码根不是目录：{root}")
    parsed = parse_flow_doc(Path(flow_doc).read_text(encoding="utf-8"))
    files, _dirs, file_set = drift.scan_tree(root)

    flows: list[dict] = []
    for flow in parsed:
        steps = []
        for s in flow["steps"]:
            anchor = parser.anchor_of(s["evidence"]) if s["evidence"] is not None else None
            steps.append(
                {
                    "step_id": s["step_id"],
                    "label": s["label"],
                    "evidence": s["evidence"],
                    "anchor": anchor,
                    "status": _status(anchor, files, file_set),
                }
            )
        flows.append(
            {
                "flow_id": flow["flow_id"],
                "title": flow["title"],
                "steps": steps,
                "edges": [{"from": e["from"], "to": e["to"]} for e in flow["edges"]],
            }
        )

    impact = None
    if diff_file is not None:
        changed = impact_analyzer.parse_unified_diff(Path(diff_file).read_text(encoding="utf-8"))
        impact = _impact(flows, changed)

    return {
        "flow_count": len(flows),
        "step_count": sum(len(f["steps"]) for f in flows),
        "edge_count": sum(len(f["edges"]) for f in flows),
        "flows": flows,
        "impact": impact,
    }


def render_text(doc: dict) -> str:
    """把流程影响文档渲染为确定性 ASCII 清单（人类可读；逐字节可断言）。"""
    lines = [
        f"flow graph: {doc['flow_count']} flows / {doc['step_count']} steps / {doc['edge_count']} edges",
    ]
    for flow in doc["flows"]:
        lines.append(f"  {flow['flow_id']}  {flow['title']}")
        for s in flow["steps"]:
            ev = s["evidence"] if s["evidence"] is not None else "-"
            lines.append(f"    [{s['status']}] {s['step_id']}: {s['label']}  ({ev})")
        for e in flow["edges"]:
            lines.append(f"    {e['from']} -> {e['to']}")

    impact = doc["impact"]
    if impact is None:
        lines.append("impact: (no diff given)")
        return "\n".join(lines) + "\n"

    lines.append(f"impact verdict: {impact['verdict']}")
    lines.append(f"  changed files ({len(impact['changed_files'])}):")
    lines.extend(f"    {f}" for f in impact["changed_files"])
    lines.append(f"  direct steps ({len(impact['direct_steps'])}):")
    lines.extend(f"    {d['flow_id']}/{d['step_id']}  {d['evidence']}" for d in impact["direct_steps"])
    lines.append(f"  affected steps ({len(impact['affected_steps'])}):")
    lines.extend(f"    {a['flow_id']}/{a['step_id']}" for a in impact["affected_steps"])
    lines.append(f"  dangling steps ({len(impact['dangling_steps'])}):")
    lines.extend(f"    {d['flow_id']}/{d['step_id']}  {d['anchor']}" for d in impact["dangling_steps"])
    return "\n".join(lines) + "\n"


def to_json(doc: dict) -> str:
    """稳定序列化：UTF-8、缩进 2、键序按插入顺序、末尾单换行（与 M1–M11 同口径）。"""
    return json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
