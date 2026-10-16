"""M9 逻辑控制面可视面：把条目、锚活性、设计盲区与模块依赖图汇成**单个自包含 HTML**。

为什么需要它（问题背景，大白话）：
    前几个里程碑把后台数据都算出来了——条目（M1）、依赖图（M2）、锚活性与设计盲区（M8）。
    但这些结果散在几个 JSON 里，人看不动。本模块把它们**汇成一张可离线打开、可展开下钻的页面**，
    即路线图 §二 所说的「**逻辑可视化控制面**」。

设计口径（对齐 `X产品化路线图-v1.md` §十三 M9 行与「判定口径（写死）」）：
    ① **纯离线自包含**：产物是单个 HTML 文档，**不含**任何外部引用（无 `http(s)://`、无外部脚本/样式）；
       下钻用原生 `<details>`，**零脚本**；
    ② **确定性**：不写时间戳/随机数/环境相关值，各段与组内一律排序，同输入两次渲染**逐字节一致**；
    ③ **不新增判定语义**：判定一律来自 `drift`（`ok` / `drift`），条目来自 `parser`，图来自
       `graph_builder`；本模块只做**呈现**；
    ④ **只读**：渲染过程不写入代码根 / 设计文档。

为什么这样定：
    * 用原生 `<details>` 而非内联脚本：脚本会引入执行顺序、异步等不确定因素，破坏「逐字节可断言」；
    * 把「呈现」与「判定」严格分开：可视面若自己造判定，就会与 `drift` 的口径悄悄分叉，
      正是本仓库反复强调的「同一事实两处口径」隐患。

M13 扩展：把 M12 的流程影响面接入可视面——可选 `flow_doc` / `diff_file`；给了流程文档就在
「同步增量」之后追加流程段（结构、三态、影响清单**一律取自** `flow.analyze`，本模块**不重算**）。
**`_CSS` 一行不改**：`_CSS` 在每个页面的同一个 `<style>` 里，任何新增 CSS 行都会**泄漏到所有页面**，
「未给流程文档时页面一字节未变」这条不变量就会失效；故流程段的判定配色复用既有类名
（`clear` → `ok`、`impacted` → `drift`）。

隔离约定：本模块**不写死**任何冻结链路径；代码根 / 设计文档一律由调用方传入
（由 M0 自测第三条校验本包源码不含冻结链目录名）。仅依赖 Python 标准库。
"""

from __future__ import annotations

import html

from . import drift, flow, graph_builder, parser, sync

# 证据在可视面上的三种状态：与 `drift` **同源**（直接取 `drift.STATUS_*`），此处只作标签用途，
# 不再各持一份字面量——可视面是「呈现层」，三态口径只能有一个源头。
STATUS_ACTIVE = drift.STATUS_ACTIVE
STATUS_DANGLING = drift.STATUS_DANGLING
STATUS_UNANCHORED = drift.STATUS_UNANCHORED

_STATUS_LABEL = {
    STATUS_ACTIVE: "活性",
    STATUS_DANGLING: "失联",
    STATUS_UNANCHORED: "无锚",
}

_CSS = """
:root { color-scheme: dark; }
body { margin: 0; padding: 24px; background: #0d1117; color: #c9d1d9;
       font: 14px/1.6 "Segoe UI", "Microsoft YaHei", sans-serif; }
h1 { font-size: 20px; letter-spacing: 1px; margin: 0 0 4px; color: #e6edf3; }
h2 { font-size: 15px; margin: 22px 0 8px; padding-bottom: 4px;
     border-bottom: 1px solid #21262d; color: #e6edf3; }
.verdict { font-family: Consolas, monospace; font-size: 13px; margin: 0; }
.verdict.ok { color: #3fb950; }
.verdict.drift { color: #f85149; }
.verdict.unchanged { color: #8b949e; }
.verdict.changed { color: #d29922; }
.verdict.regressed { color: #f85149; }
ul { margin: 6px 0; padding-left: 20px; }
code, .cid { font-family: Consolas, monospace; color: #79c0ff; }
details { margin: 4px 0; border: 1px solid #21262d; border-radius: 4px; padding: 6px 10px; }
details > summary { cursor: pointer; }
.badge { font-size: 12px; padding: 0 6px; border-radius: 3px; margin-left: 6px; }
.badge.active { background: #1f3a24; color: #3fb950; }
.badge.dangling { background: #3d1418; color: #f85149; }
.badge.unanchored { background: #3a2f14; color: #d29922; }
.muted { color: #8b949e; }
.kv { font-family: Consolas, monospace; font-size: 13px; }
footer { margin-top: 26px; padding-top: 10px; border-top: 1px solid #21262d;
         font-size: 12px; color: #8b949e; }
""".strip()


def _status_index(drift_doc: dict) -> dict[tuple[str, str], tuple[str, dict | None]]:
    """把 `drift` 的三类结果拉平成 {(条目id, 证据原文): (状态, 记录)}，供逐条渲染查表。"""
    index: dict[tuple[str, str], tuple[str, dict | None]] = {}
    for r in drift_doc["active_anchors"]:
        index[(r["constraint_id"], r["evidence"])] = (STATUS_ACTIVE, r)
    for r in drift_doc["dangling_anchors"]:
        index[(r["constraint_id"], r["evidence"])] = (STATUS_DANGLING, r)
    for r in drift_doc["unanchored_evidence"]:
        index[(r["constraint_id"], r["evidence"])] = (STATUS_UNANCHORED, None)
    return index


def analyze(
    code_root: str,
    design_doc: str,
    baseline: dict | None = None,
    flow_doc: str | None = None,
    diff_file: str | None = None,
) -> dict:
    """汇总条目 / 锚活性 / 盲区 / 依赖图（+ 可选同步增量、可选流程影响面），返回键序固定、可逐字节复现的文档。

    对同一批次数据只取一次：`drift` 负责锚活性与盲区，`graph_builder` 负责依赖图，
    本函数只做**汇合**，不改写任何一方的取值。给了 `baseline` 时，增量段经
    `sync.snapshot_from_drift` 由**同一份** `drift` 结果构造，不再重复采集。
    给了 `flow_doc` 时，流程段经 `flow.analyze`**只跑一次**得到，其返回文档**原样**放入
    `doc["flow"]`（不裁剪、不改写、不重算）——这样呈现段就没有第二份判定实现的可能。
    """
    drift_doc = drift.analyze(code_root, design_doc)
    design = parser.parse_file(design_doc)
    graph = graph_builder.build_graph(code_root)

    doc = {
        "verdict": drift_doc["verdict"],
        "entry_count": drift_doc["entry_count"],
        "active_count": drift_doc["active_count"],
        "dangling_count": drift_doc["dangling_count"],
        "unanchored_count": len(drift_doc["unanchored_evidence"]),
        "uncovered_file_count": drift_doc["uncovered_file_count"],
        "node_count": graph["node_count"],
        "edge_count": graph["edge_count"],
        "cycle_count": len(graph["cycles"]),
        "entries": design["entries"],
        "active_anchors": drift_doc["active_anchors"],
        "dangling_anchors": drift_doc["dangling_anchors"],
        "unanchored_evidence": drift_doc["unanchored_evidence"],
        "uncovered_files": drift_doc["uncovered_files"],
        "nodes": graph["nodes"],
        "edges": graph["edges"],
        "cycles": graph["cycles"],
    }
    doc["sync"] = (
        sync.compare_snapshots(baseline, sync.snapshot_from_drift(drift_doc))
        if baseline is not None
        else None
    )
    doc["flow"] = (
        flow.analyze(flow_doc, code_root, diff_file) if flow_doc is not None else None
    )
    return doc


def _ev(x: object) -> str:
    """HTML 转义：所有动态文本一律经此，防止设计文档内容破坏页面结构。"""
    return html.escape(str(x), quote=True)


def _badge(status: str) -> str:
    return f'<span class="badge {status}">{_STATUS_LABEL[status]}</span>'


def _render_entry(entry: dict, index: dict[tuple[str, str], tuple[str, dict | None]]) -> list[str]:
    """单个条目的卡片：摘要行给 id / 标题 / 最高优先级状态，展开后给字段与逐条证据锚。"""
    cid = entry["constraint_id"]
    statuses = [index[(cid, e)][0] for e in entry["required_evidence"] if (cid, e) in index]
    # 摘要徽标取「最需要注意」的那个：失联 > 无锚 > 活性
    summary_status = STATUS_ACTIVE
    if STATUS_UNANCHORED in statuses:
        summary_status = STATUS_UNANCHORED
    if STATUS_DANGLING in statuses:
        summary_status = STATUS_DANGLING

    out = [
        f'<details class="entry" id="entry-{_ev(cid)}">',
        f'<summary><span class="cid">{_ev(cid)}</span> {_ev(entry["title"])}{_badge(summary_status)}</summary>',
        "<ul>",
        f'<li class="kv">type: {_ev(entry["constraint_type"])}</li>',
        f'<li class="kv">invariant: {_ev(entry["expected_invariant"])}</li>',
        f'<li class="kv">change_control: {_ev(entry["change_control"])}</li>',
        f'<li class="kv">severity: {_ev(entry["severity"])}</li>',
        f'<li class="kv">action_policy: {_ev(entry["action_policy"])}</li>',
        "<li>证据锚：<ul>",
    ]
    for evidence in entry["required_evidence"]:
        status, record = index.get((cid, evidence), (STATUS_UNANCHORED, None))
        if status == STATUS_ACTIVE:
            extra = f'<span class="muted">[{_ev(record["match_kind"])}] → {_ev(", ".join(record["matched_files"]))}</span>'
        elif status == STATUS_DANGLING:
            extra = f'<span class="muted">[{_ev(record["match_kind"])}] {_ev(record["reason"])}</span>'
        else:
            extra = '<span class="muted">不参与判定</span>'
        out.append(f'<li><code>{_ev(evidence)}</code>{_badge(status)} {extra}</li>')
    out.extend(["</ul></li>", "</ul>", "</details>"])
    return out


def _render_node(node: dict) -> list[str]:
    """单个模块节点：摘要给路径与模块名，展开给文件内顶层符号。"""
    out = [
        f'<details class="node" id="node-{_ev(node["id"])}">',
        f'<summary><code>{_ev(node["id"])}</code> <span class="muted">{_ev(node["module"])}</span>'
        f' <span class="muted">({len(node["symbols"])} 个符号)</span></summary>',
        "<ul>",
    ]
    for s in node["symbols"]:
        out.append(f'<li class="kv">{_ev(s["kind"])} <code>{_ev(s["name"])}</code> : L{_ev(s["line"])}</li>')
    out.extend(["</ul>", "</details>"])
    return out


def _render_sync(syncdoc: dict) -> list[str]:
    """增量段：判定与六个变化清单**直接取自** `sync.compare_snapshots`，此处只做呈现。"""
    v = syncdoc["verdict"]
    lines = [
        '<section id="sync">',
        "<h2>同步增量（相对基线）</h2>",
        f'<p class="verdict {_ev(v)}">判定：{_ev(v)}</p>',
        "<ul>",
        f"<li>新增失联：{len(syncdoc['newly_dangling'])}</li>",
        f"<li>恢复：{len(syncdoc['recovered'])}</li>",
        f"<li>新增证据：{len(syncdoc['added_evidence'])}</li>",
        f"<li>移除证据：{len(syncdoc['removed_evidence'])}</li>",
        f"<li>盲区新增：{len(syncdoc['uncovered_added'])}</li>",
        f"<li>盲区移除：{len(syncdoc['uncovered_removed'])}</li>",
        "</ul>",
    ]
    groups = (
        ("新增失联", [(r["constraint_id"], r["evidence"]) for r in syncdoc["newly_dangling"]]),
        ("恢复", [(r["constraint_id"], r["evidence"]) for r in syncdoc["recovered"]]),
        ("新增证据", [(r["constraint_id"], r["evidence"]) for r in syncdoc["added_evidence"]]),
        ("移除证据", [(r["constraint_id"], r["evidence"]) for r in syncdoc["removed_evidence"]]),
        ("盲区新增", [(p, "") for p in syncdoc["uncovered_added"]]),
        ("盲区移除", [(p, "") for p in syncdoc["uncovered_removed"]]),
    )
    for title, items in groups:
        if not items:
            continue
        lines.append(f"<details><summary>{title}（{len(items)}）</summary>")
        lines.append("<ul>")
        for cid, ev in items:
            if ev:
                lines.append(f'<li><span class="cid">{_ev(cid)}</span> <code>{_ev(ev)}</code></li>')
            else:
                lines.append(f'<li><code>{_ev(cid)}</code></li>')
        lines.append("</ul>")
        lines.append("</details>")
    lines.append("</section>")
    return lines


def _render_flow(flowdoc: dict) -> list[str]:
    """流程影响段：结构与判定**一律取自** `flow.analyze` 的返回文档，此处只做呈现。

    本段**不**重算任何「锚是否存在」的判断（`status` 直接读 `flow` 已算好的值），
    避免在 M12 之外再添第三份活性判定实现；也**不**二次排序（沿用 `flow` 的确定性顺序）。
    """
    lines = [
        '<section id="flow">',
        f"<h2>业务流影响面（流程 {flowdoc['flow_count']} / 步骤 {flowdoc['step_count']} / 边 {flowdoc['edge_count']}）</h2>",
    ]
    impact = flowdoc["impact"]
    if impact is None:
        lines.append('<p class="kv muted">未提供 diff（仅呈现流程结构与锚活性）</p>')
    else:
        # 判定配色复用既有类名：clear → ok、impacted → drift（不新增 CSS，见模块 docstring）
        cls = "ok" if impact["verdict"] == "clear" else "drift"
        lines.append(f'<p class="verdict {cls}">判定：{_ev(impact["verdict"])}</p>')

    for flow_rec in flowdoc["flows"]:
        fid = flow_rec["flow_id"]
        dangling_n = sum(1 for s in flow_rec["steps"] if s["status"] == STATUS_DANGLING)
        meta = f"（{len(flow_rec['steps'])} 步 / {len(flow_rec['edges'])} 边"
        meta += f"，失联 {dangling_n}）" if dangling_n else "）"
        lines.append(f'<details class="flow" id="flow-{_ev(fid)}">')
        lines.append(
            f'<summary><span class="cid">{_ev(fid)}</span> {_ev(flow_rec["title"])} '
            f'<span class="muted">{meta}</span></summary>'
        )
        lines.append("<ul>")
        for s in flow_rec["steps"]:
            ev = s["evidence"] if s["evidence"] is not None else "（无证据）"
            lines.append(
                f'<li><code>{_ev(s["step_id"])}</code> {_ev(s["label"])}{_badge(s["status"])} '
                f'<span class="muted">{_ev(ev)}</span></li>'
            )
        for e in flow_rec["edges"]:
            lines.append(f'<li class="kv"><code>{_ev(e["from"])}</code> → <code>{_ev(e["to"])}</code></li>')
        lines.extend(["</ul>", "</details>"])

    if impact is not None:
        groups = (
            ("changed files", list(impact["changed_files"])),
            ("direct steps", [f'{d["flow_id"]}/{d["step_id"]}' for d in impact["direct_steps"]]),
            ("affected steps", [f'{a["flow_id"]}/{a["step_id"]}' for a in impact["affected_steps"]]),
            ("dangling steps", [f'{d["flow_id"]}/{d["step_id"]}' for d in impact["dangling_steps"]]),
        )
        lines.append("<h3>影响清单</h3>")
        lines.append("<ul>")
        for title, items in groups:
            lines.append(f"<li>{title}：{len(items)}</li>")
        lines.append("</ul>")
        for title, items in groups:
            lines.append(f"<details><summary>{title}（{len(items)}）</summary>")
            lines.append("<ul>")
            for item in items:
                lines.append(f'<li class="kv">{_ev(item)}</li>')
            lines.extend(["</ul>", "</details>"])

    lines.append("</section>")
    return lines


def render_html(doc: dict) -> str:
    """把合成文档渲染为单个自包含 HTML（末尾单换行；逐字节可断言）。"""
    index = _status_index(
        {
            "active_anchors": doc["active_anchors"],
            "dangling_anchors": doc["dangling_anchors"],
            "unanchored_evidence": doc["unanchored_evidence"],
        }
    )
    verdict = doc["verdict"]
    lines = [
        "<!DOCTYPE html>",
        '<html lang="zh-CN">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>X 逻辑控制面</title>",
        f"<style>{_CSS}</style>",
        "</head>",
        "<body>",
        "<header>",
        "<h1>X 逻辑控制面</h1>",
        f'<p class="verdict {_ev(verdict)}">判定：{_ev(verdict)}</p>',
        "</header>",
        '<section id="overview">',
        "<h2>概览</h2>",
        "<ul>",
        f"<li>设计条目：{doc['entry_count']}</li>",
        f"<li>活性锚：{doc['active_count']}</li>",
        f"<li>失联锚：{doc['dangling_count']}</li>",
        f"<li>无锚证据：{doc['unanchored_count']}</li>",
        f"<li>设计盲区（仅供参考）：{doc['uncovered_file_count']}</li>",
        f"<li>模块节点：{doc['node_count']}</li>",
        f"<li>依赖边：{doc['edge_count']}</li>",
        f"<li>依赖环：{doc['cycle_count']}</li>",
        "</ul>",
        "</section>",
    ]
    if doc.get("sync") is not None:
        lines.extend(_render_sync(doc["sync"]))
    if doc.get("flow") is not None:
        lines.extend(_render_flow(doc["flow"]))
    lines.append('<section id="entries">')
    lines.append("<h2>条目与锚</h2>")
    for entry in doc["entries"]:
        lines.extend(_render_entry(entry, index))
    lines.append("</section>")

    lines.append('<section id="dangling">')
    lines.append(f"<h2>失联锚（{doc['dangling_count']}）</h2>")
    lines.append("<ul>")
    for d in doc["dangling_anchors"]:
        lines.append(
            f'<li><span class="cid">{_ev(d["constraint_id"])}</span> '
            f'<code>{_ev(d["anchor"])}</code> — {_ev(d["reason"])}</li>'
        )
    lines.append("</ul>")
    lines.append("</section>")

    lines.append('<section id="unanchored">')
    lines.append(f"<h2>无锚证据（{doc['unanchored_count']}）</h2>")
    lines.append("<ul>")
    for u in doc["unanchored_evidence"]:
        lines.append(f'<li><span class="cid">{_ev(u["constraint_id"])}</span> {_ev(u["evidence"])}</li>')
    lines.append("</ul>")
    lines.append("</section>")

    lines.append('<section id="uncovered">')
    lines.append(f"<h2>设计盲区（{doc['uncovered_file_count']}，仅供参考）</h2>")
    lines.append("<ul>")
    for path in doc["uncovered_files"]:
        lines.append(f"<li><code>{_ev(path)}</code></li>")
    lines.append("</ul>")
    lines.append("</section>")

    lines.append('<section id="graph">')
    lines.append(f"<h2>模块依赖图（节点 {doc['node_count']} / 边 {doc['edge_count']}）</h2>")
    for node in doc["nodes"]:
        lines.extend(_render_node(node))
    lines.append("<h3>依赖边</h3>")
    lines.append("<ul>")
    for e in doc["edges"]:
        lines.append(
            f'<li class="kv"><code>{_ev(e["from"])}</code> → <code>{_ev(e["to"])}</code> '
            f'<span class="muted">[{_ev(e["kind"])}]</span></li>'
        )
    lines.append("</ul>")
    lines.append("<h3>依赖环</h3>")
    lines.append("<ul>")
    for cycle in doc["cycles"]:
        lines.append(f'<li class="kv">{" → ".join(_ev(p) for p in cycle)}</li>')
    lines.append("</ul>")
    lines.append("</section>")

    lines.append("<footer>")
    lines.append(f"<p>{_ev(drift._DRIFT_NOTE)}</p>")
    lines.append("<p>本页面为静态快照：不随代码变化自动刷新；判定口径与 drift 一致，增量段口径与 sync 一致，本页不新增判定。</p>")
    lines.append("</footer>")
    lines.extend(["</body>", "</html>"])
    return "\n".join(lines) + "\n"
