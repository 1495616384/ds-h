"""M3 变更影响分析器：给定一次模拟 diff，输出受影响条目 / 文件清单。

设计口径（对齐 `X产品化路线图-v1.md` §四 M3 行「给定一次模拟 diff，输出受影响
条目/文件清单」，以及 §六 红线「用模拟 diff，不真改基线」）：
    ① 输入 = 一份**统一 diff 文本文件**（git diff 风格：`diff --git` 块 + `--- a/`
       + `+++ b/` 头 + hunk）。**纯文本静态解析**，不调用 git、不触碰工作树；
    ② 受影响文件 = 从「直接变更文件」沿依赖图**反向**（谁依赖我）取传递闭包，
       并记录**最小深度**（直接变更 = 深度 0）；
    ③ 条目命中 = **仅直接变更文件**参与证据锚匹配；传递受影响的文件只进文件清单，
       不升级为条目命中（否则影响面会被二次放大，失去可判定性）；
    ④ 输出 = 默认稳定 JSON，`--text` 给人类可读清单。

为什么这样定：
    * 反向传播而非正向：改一个被依赖的底层模块，风险在于**它的消费者**，
      而不是它自己依赖的东西；正向闭包回答的是另一个问题。
    * 「直接变更才命中条目」把「我改了它」与「它会被别人的改动波及」两条
      不同强度的证据分开，避免把传播距离当成等价证据。
    * 图外变更文件（如 `docs/*.md`，不在 M2 依赖图中）单独列出、不参与传播：
      图里没有它，任何传播都只能靠猜；显式列出比静默丢弃可核验。

证据锚规则（写死；与 M1 `required_evidence` 的写法配套）：
    取每条证据串的**首个空白分隔 token**作锚；
    锚以 `/` 结尾 → **目录前缀**匹配（`tests/` 命中 `tests/x.py`）；
    否则 → **精确路径**匹配；
    首 token 不含 `/` → 记为 `unanchored` 并**显式列出**，禁止静默丢弃。

扫描根与设计文档路径一律由调用方传入，本模块不写死任何具体路径，
以维持与冻结链的物理隔离（由 M0 自测第三条校验本包源码不含冻结链目录名）。
仅依赖 Python 标准库（M3 边界：不引入未安装依赖、不写基线）。
"""

from __future__ import annotations

import json
from pathlib import Path

from . import graph_builder, parser

# 统一 diff 的结构标记（git diff 风格）
_DIFF_HEADER = "diff --git "
_MINUS_HEAD = "--- "
_PLUS_HEAD = "+++ "
_HUNK_HEAD = "@@ "
_DEV_NULL = "/dev/null"

MATCH_EXACT = "exact"
MATCH_PREFIX = "prefix"


class ImpactError(ValueError):
    """diff 文本不合法、扫描根不可用或设计文档不合格式时抛出。"""


def _normalize(raw: str) -> str:
    """把 diff 头里的路径规范化为「相对代码根、POSIX 分隔」的比较用路径。"""
    path = raw.strip()
    for prefix in ("a/", "b/"):
        if path.startswith(prefix):
            path = path[len(prefix) :]
            break
    if path.startswith("./"):
        path = path[2:]
    return path


def _path_of_block(block: list[str], start_lineno: int) -> str:
    """从单个 `diff --git` 块中取出被变更文件的规范化路径。

    只在**首个 hunk 头之前**找 `--- `/`+++ `：hunk 正文里一条被删除的内容行
    若本身以 `-- ` 起头，渲染出来就是 `--- ...`，会被误判成文件头。
    """
    minus: str | None = None
    plus: str | None = None
    for line in block:
        if line.startswith(_HUNK_HEAD):
            break
        if minus is None and line.startswith(_MINUS_HEAD):
            minus = line[len(_MINUS_HEAD) :].strip()
        elif plus is None and line.startswith(_PLUS_HEAD):
            plus = line[len(_PLUS_HEAD) :].strip()
    if plus is None:
        raise ImpactError(f"第 {start_lineno} 行起的 diff 块缺少 `+++ ` 文件头")
    if minus is None:
        raise ImpactError(f"第 {start_lineno} 行起的 diff 块缺少 `--- ` 文件头")
    raw = plus if plus != _DEV_NULL else minus
    path = _normalize(raw)
    if not path or path == _DEV_NULL or path.startswith("/"):
        raise ImpactError(f"第 {start_lineno} 行起的 diff 块未能解析出有效文件路径：{raw!r}")
    return path


def parse_unified_diff(text: str) -> list[str]:
    """解析统一 diff 文本，返回去重且排序后的被变更文件列表。

    空白（或仅空白）输入视为**空 diff**：返回空列表，不报错——「这次没改东西」
    是合法输入，且必须有确定输出（全空清单），不能靠异常表达。
    非空且不含任何 `diff --git` 块 → 报错：那不是统一 diff，硬解析只会产出假结果。
    """
    if not text.strip():
        return []

    lines = text.splitlines()
    changed: list[str] = []
    i = 0
    total = len(lines)
    while i < total:
        if not lines[i].strip():
            i += 1
            continue
        if not lines[i].startswith(_DIFF_HEADER):
            raise ImpactError(f"第 {i + 1} 行：统一 diff 必须以 `diff --git ` 起头，实际 {lines[i]!r}")
        j = i + 1
        while j < total and not lines[j].startswith(_DIFF_HEADER):
            j += 1
        changed.append(_path_of_block(lines[i + 1 : j], i + 1))
        i = j
    return sorted(set(changed))


def _anchor_of(evidence: str) -> str | None:
    """取证据串的首个空白分隔 token 作锚；不含 `/` 时返回 None 表示 unanchored。"""
    parts = evidence.split()
    if not parts:
        return None
    return parts[0] if "/" in parts[0] else None


def _match_anchor(anchor: str, changed: set[str]) -> tuple[str, str] | None:
    """在**直接变更文件**集合里匹配锚，返回（命中文件, 匹配方式）或 None。"""
    if anchor.endswith("/"):
        for path in sorted(changed):
            if path.startswith(anchor):
                return path, MATCH_PREFIX
        return None
    return (anchor, MATCH_EXACT) if anchor in changed else None


def _reverse_closure(nodes: list[dict], edges: list[dict], seeds: list[str]) -> dict[str, int]:
    """沿依赖图反向做分层 BFS，返回 {受影响文件: 最小深度}。

    分层 BFS（逐层扩展、已登记节点不再入队）保证登记的就是最小深度；
    反向邻接按 `to → from` 建，语义是「谁依赖我」。
    """
    reverse: dict[str, list[str]] = {}
    for edge in edges:
        reverse.setdefault(edge["to"], []).append(edge["from"])

    depth: dict[str, int] = {seed: 0 for seed in seeds}
    frontier = sorted(depth)
    level = 0
    while frontier:
        level += 1
        found: set[str] = set()
        for node in frontier:
            for dependent in reverse.get(node, ()):
                if dependent not in depth:
                    found.add(dependent)
        for node in found:
            depth[node] = level
        frontier = sorted(found)
    return depth


def analyze(diff_text: str, code_root: str | Path, design_doc: str | Path) -> dict:
    """分析一次 diff 的影响面，返回键序固定、可逐字节复现的结果文档。"""
    changed = parse_unified_diff(diff_text)
    graph = graph_builder.build_graph(code_root)
    node_ids = {node["id"] for node in graph["nodes"]}
    design = parser.parse_file(design_doc)

    changed_set = set(changed)
    in_graph = sorted(f for f in changed if f in node_ids)
    out_of_graph = sorted(f for f in changed if f not in node_ids)
    depth = _reverse_closure(graph["nodes"], graph["edges"], in_graph)

    affected_entries: list[dict] = []
    unanchored: list[dict] = []
    for entry in design["entries"]:
        matched: list[dict] = []
        for evidence in entry["required_evidence"]:
            anchor = _anchor_of(evidence)
            if anchor is None:
                unanchored.append({"constraint_id": entry["constraint_id"], "evidence": evidence})
                continue
            hit = _match_anchor(anchor, changed_set)
            if hit is not None:
                matched.append(
                    {
                        "evidence": evidence,
                        "anchor": anchor,
                        "match_kind": hit[1],
                        "matched_file": hit[0],
                    }
                )
        if matched:
            affected_entries.append(
                {
                    "constraint_id": entry["constraint_id"],
                    "title": entry["title"],
                    "severity": entry["severity"],
                    "change_control": entry["change_control"],
                    "action_policy": entry["action_policy"],
                    "matched_evidence": matched,
                }
            )
    affected_entries.sort(key=lambda e: e["constraint_id"])
    unanchored.sort(key=lambda u: (u["constraint_id"], u["evidence"]))

    affected_files = [
        {"id": node, "depth": level}
        for node, level in sorted(depth.items(), key=lambda kv: (kv[1], kv[0]))
    ]
    return {
        "changed_file_count": len(changed),
        "changed_files": changed,
        "in_graph_changes": in_graph,
        "out_of_graph_changes": out_of_graph,
        "affected_entries": affected_entries,
        "unanchored_evidence": unanchored,
        "affected_file_count": len(affected_files),
        "max_depth": max(depth.values()) if depth else None,
        "affected_files": affected_files,
    }


def analyze_files(
    diff_path: str | Path, code_root: str | Path, design_doc: str | Path
) -> dict:
    """读取 UTF-8 统一 diff 文件后分析。"""
    return analyze(Path(diff_path).read_text(encoding="utf-8-sig"), code_root, design_doc)


def render_text(doc: dict) -> str:
    """把结果文档渲染为确定性 ASCII 清单（人类可读；逐字节可断言）。

    各段固定打印条目数（空段也打印），深度分组按深度升序、组内按节点 id 升序。
    """
    lines = [f"changed files ({doc['changed_file_count']}):"]
    lines.extend(f"    {path}" for path in doc["changed_files"])
    lines.append(f"out-of-graph changes ({len(doc['out_of_graph_changes'])}):")
    lines.extend(f"    {path}" for path in doc["out_of_graph_changes"])
    lines.append(f"affected entries ({len(doc['affected_entries'])}):")
    for entry in doc["affected_entries"]:
        lines.append(
            f"    {entry['constraint_id']} — {entry['title']} "
            f"[{entry['severity']}/{entry['change_control']}] "
            f"命中 {len(entry['matched_evidence'])} 条证据"
        )
        for item in entry["matched_evidence"]:
            lines.append(
                f"        {item['evidence']}  ->  {item['matched_file']} ({item['match_kind']})"
            )
    lines.append(f"unanchored evidence ({len(doc['unanchored_evidence'])}):")
    for item in doc["unanchored_evidence"]:
        lines.append(f"    {item['constraint_id']}: {item['evidence']}")

    max_depth = doc["max_depth"] if doc["max_depth"] is not None else "-"
    lines.append(f"affected files ({doc['affected_file_count']}), max depth {max_depth}:")
    for depth in sorted({item["depth"] for item in doc["affected_files"]}):
        group = [item["id"] for item in doc["affected_files"] if item["depth"] == depth]
        lines.append(f"    depth {depth} ({len(group)}): {', '.join(group)}")
    return "\n".join(lines) + "\n"


def to_json(doc: dict) -> str:
    """稳定序列化：UTF-8、缩进 2、键序按插入顺序、末尾单换行（与 M1/M2 同口径）。"""
    return json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
