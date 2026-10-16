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
    ⑤ `dangling_steps` = 锚在代码根**失联**的步骤（**断链**），**单列**、**不**并入 `verdict`
       （步骤锚三态一律取自 `drift.anchor_state`——全仓唯一实现，与 M8 逐字同口径）；
    ⑥ `verdict` ∈ `clear` / `impacted`（`affected_steps` 非空即 `impacted`）；
    ⑦ 无 `--diff` 时 `impact` 为 `null`，只输出流程结构与步骤锚活性；
    ⑧ 确定性（排序、无时间戳，同输入两次**逐字节一致**）、只读；
    ⑨ M15 采集 / 构造分离：`prepare`（与 diff 无关：读 + 解析流程文档、扫树、判锚活性）与
       `analyze_prepared`（按 diff 构造影响）各有**唯一实现**，`analyze` 退化为**薄编排**；
       复用由调用方**显式持有**中间体，**不**引入隐式缓存（签名与输出**逐字节不变**）。

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

from . import contract, drift, impact_analyzer, parser

# 步骤锚三态：与 M8 **同源**——明细判定收口在 `drift.anchor_state`（全仓唯一），
# 此处只保留公开名，供调用方 / 自测引用，不再各持一份字面量或一份判定实现。
STATUS_ACTIVE = drift.STATUS_ACTIVE
STATUS_DANGLING = drift.STATUS_DANGLING
STATUS_UNANCHORED = drift.STATUS_UNANCHORED

VERDICT_CLEAR = "clear"
VERDICT_IMPACTED = "impacted"

# M18：本模块采集体**必需键的唯一字面量源**，键序与 `prepare` 返回**逐字同序**（由 M18 自测 ③ 强制）。
# 为什么公开、为什么放在模块层：它是 `analyze_prepared` 入口校验的**真值源**——实现与测试都引用
# 同一处，才不会出现「常量说一套、实现做一套」的漂移；也正因为它是**跨模块同名可互传**治理的判据，
# 三个模块的这份清单必须各持一份、彼此不同（由 M18 自测 ⑦ 固化，M18 设计稿 §四.1）。
PREPARED_REQUIRED_KEYS = ("flow_count", "step_count", "edge_count", "flows")

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


def prepare(flow_doc: str | Path, code_root: str | Path) -> dict:
    """采集一次：**与 diff 无关**的部分——读 + 解析流程文档、扫一遍代码根树、逐步骤判锚活性。

    为什么拆出这一层（M15）：同一份流程文档在一个工作流里要供 N 份 diff 复用（M14 的流程层即是）。
    把「与 diff 无关的采集」与「按 diff 构造」分成两个**显式传参**的入口，调用方只需**自己持有**
    中间体即可只采集一次。**不**引入隐式缓存 / 全局状态：一旦用 `lru_cache` 或模块级字典复用，
    「哪些调用共享了同一份采集」就变得不可见，键不覆盖真实语义时还会串味（A 的采集被 B 误用）——
    本仓库的核心教训之一就是「隐式共享比显式传参更难防」。

    返回键序固定为 `flow_count, step_count, edge_count, flows`（即 `analyze` 输出**去掉 `impact` 键**）。
    """
    root = Path(code_root)
    if not root.is_dir():
        raise FlowError(f"代码根不是目录：{root}")
    parsed = parse_flow_doc(Path(flow_doc).read_text(encoding="utf-8"))
    files, dirs, file_set = drift.scan_tree(root)

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
                    "status": drift.anchor_state(anchor, files, dirs, file_set)["status"],
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

    # M19：产出不变量——采集端**自证**其产物键序满足契约常量 `PREPARED_REQUIRED_KEYS`。
    # 为什么加在**生产者侧**（而不是只靠消费端 M18 的入口校验）：契约以常量声明，若无人被要求遵守，
    # 一旦两份字面量分叉，合法的调用会先撞上消费端校验、报出「你传错了」——**归因指错了方向**，
    # 且只在某个消费者跑起来时才暴露。放在返回前，则缺陷在**定义点**、以**指向生产者**的诊断失败。
    # 对合法输入恒真，不产生任何分支差异（对外产物逐字节不变）。
    body = {
        "flow_count": len(flows),
        "step_count": sum(len(f["steps"]) for f in flows),
        "edge_count": sum(len(f["edges"]) for f in flows),
        "flows": flows,
    }
    contract.assert_produced_keys(body, PREPARED_REQUIRED_KEYS, FlowError, "flow")
    return body


def analyze_prepared(prepared: dict, diff_file: str | Path | None = None) -> dict:
    """按 diff 构造：**与 diff 有关**的部分——读 + 解析该 diff、做流程级影响判定（不可复用）。

    **只读**传入的 `prepared`：既不修改它，也不注册任何全局状态，故同一 `prepared` 可安全供给
    任意多份 diff 复用——复用次数与污染风险**写在调用点**，可读、可断言、可推理。
    返回键序与 `analyze` **逐字一致**（`flow_count, step_count, edge_count, flows, impact`）；
    无 `diff_file` 时 `impact` 为 `None`。

    M18：取任何键**之前**先做**入口必需键校验**。为什么放在**消费端入口**而不是采集端：
    `flow` / `impact_analyzer` / `drift` 三个模块的 `prepare` **同名而形状不兼容**（本模块 4 键、
    另两个 2 / 4 键），中间体在模块间流动时**不携带身份信息**，误传时此前只会抛一句无诊断性的
    `KeyError`。此处用**本模块既有错误类型**报出「缺了哪些键 + 应由谁产出」，把误传变成一眼可懂。
    校验只读、只判必需键**子集**（多出的键不报错）；对合法采集体**恒真**，不产生任何分支差异。
    """
    contract.require_prepared_keys(prepared, PREPARED_REQUIRED_KEYS, FlowError, "flow")

    impact = None
    if diff_file is not None:
        changed = impact_analyzer.parse_unified_diff(Path(diff_file).read_text(encoding="utf-8"))
        impact = _impact(prepared["flows"], changed)

    return {
        "flow_count": prepared["flow_count"],
        "step_count": prepared["step_count"],
        "edge_count": prepared["edge_count"],
        "flows": prepared["flows"],
        "impact": impact,
    }


def analyze(
    flow_doc: str | Path,
    code_root: str | Path,
    diff_file: str | Path | None = None,
) -> dict:
    """解析流程文档、判定步骤锚活性；给了 `diff_file` 再算一次流程级影响。

    返回键序固定、可逐字节复现的文档；无 `diff_file` 时 `impact` 为 `None`。

    M15：本函数退化为**一层薄编排**——上面两个入口各有**唯一实现**，此处只顺次调用它们，
    采集逻辑**不**在编排层被再写一遍（否则又回到「同一事实多处实现」的老路）。
    """
    return analyze_prepared(prepare(flow_doc, code_root), diff_file)


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
