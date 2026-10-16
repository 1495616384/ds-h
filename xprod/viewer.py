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

隔离约定：本模块**不写死**任何冻结链路径；代码根 / 设计文档一律由调用方传入
（由 M0 自测第三条校验本包源码不含冻结链目录名）。仅依赖 Python 标准库。
"""

from __future__ import annotations

import html

from . import drift, graph_builder, parser

# 证据在可视面上的三种状态（口径与 `drift` 一致，此处只是取给标签用）
STATUS_ACTIVE = "active"
STATUS_DANGLING = "dangling"
STATUS_UNANCHORED = "unanchored"

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


def analyze(code_root: str, design_doc: str) -> dict:
    """汇总条目 / 锚活性 / 盲区 / 依赖图，返回键序固定、可逐字节复现的合成文档。

    对同一批次数据只取一次：`drift` 负责锚活性与盲区，`graph_builder` 负责依赖图，
    本函数只做**汇合**，不改写任何一方的取值。
    """
    drift_doc = drift.analyze(code_root, design_doc)
    design = parser.parse_file(design_doc)
    graph = graph_builder.build_graph(code_root)

    return {
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
        '<section id="entries">',
        "<h2>条目与锚</h2>",
    ]
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
    lines.append("<p>本页面为静态快照：不随代码变化自动刷新；判定口径与 drift 一致，本页不新增判定。</p>")
    lines.append("</footer>")
    lines.extend(["</body>", "</html>"])
    return "\n".join(lines) + "\n"
