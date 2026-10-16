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
    ⑤ M16 采集 / 构造分离：`prepare`（与 diff 无关：建图 + 解析设计文档）、`read_diff`（全仓唯一的
       「读 diff 文件」实现）与 `analyze_prepared`（按 diff 构造）各有**唯一实现**；`analyze` /
       `analyze_files` 退化为**薄编排**；复用由调用方**显式持有**中间体，**不**引入隐式缓存
       （两者的签名与输出**逐字节不变**）。

为什么这样定：
    * 反向传播而非正向：改一个被依赖的底层模块，风险在于**它的消费者**，
      而不是它自己依赖的东西；正向闭包回答的是另一个问题。
    * 「直接变更才命中条目」把「我改了它」与「它会被别人的改动波及」两条
      不同强度的证据分开，避免把传播距离当成等价证据。
    * 图外变更文件（如 `docs/*.md`，不在 M2 依赖图中）单独列出、不参与传播：
      图里没有它，任何传播都只能靠猜；显式列出比静默丢弃可核验。

证据锚规则（写死；与 M1 `required_evidence` 的写法配套，实现已收口到 `parser.anchor_of`）：
    取每条证据串的**首个空白分隔 token**作锚；
    锚以 `/` 结尾 → **目录前缀**匹配（`tests/` 命中 `tests/x.py`）；
    否则 → **精确路径**匹配；
    首 token 不含 `/` → 记为 `unanchored` 并**显式列出**，禁止静默丢弃。

扫描根与设计文档路径一律由调用方传入，本模块不写死任何具体路径，
以维持与冻结链的物理隔离（由 M0 自测第三条校验本包源码不含冻结链目录名）。
仅依赖 Python 标准库（M3 边界：不引入未安装依赖、不写基线）。
"""

from __future__ import annotations

from pathlib import Path

from . import contract, graph_builder, parser, textio

# 统一 diff 的结构标记（git diff 风格）
_DIFF_HEADER = "diff --git "
_MINUS_HEAD = "--- "
_PLUS_HEAD = "+++ "
_HUNK_HEAD = "@@ "
_DEV_NULL = "/dev/null"

MATCH_EXACT = "exact"
MATCH_PREFIX = "prefix"

# M18：本模块采集体**必需键的唯一字面量源**，键序与 `prepare` 返回**逐字同序**（由 M18 自测 ③ 强制）。
# 为什么公开、为什么放在模块层：它是 `analyze_prepared` 入口校验的**真值源**——实现与测试都引用
# 同一处，才不会出现「常量说一套、实现做一套」的漂移（M18 设计稿 §四.1）。
# 注意：本模块与 `drift` 的清单**只共享 `design`** 一个键——正是这一处「部分同名」制造了
# 「可以互传」的错觉（`drift.analyze_prepared(impact_analyzer.prepare(...))` 在肉眼上完全合理），
# M18 的入口校验正是要把它变成「一眼能看懂为什么错」。
PREPARED_REQUIRED_KEYS = ("graph", "design")


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


def prepare(code_root: str | Path, design_doc: str | Path) -> dict:
    """采集一次：**与 diff 无关**的部分——依赖图构建 + 设计文档解析。

    为什么拆出这一层（M16）：M7 路径里同一对 `(代码根, 设计文档)` 要供 N 份改动复用，而此前
    `analyze` 每次都在这两件事上重做一遍——`build_graph` 要遍历整棵树并逐文件解析模块名与导入，
    `parse_file` 要重解析整份设计文档，两者都**不随 diff 变化**。此处抽成**显式传参**的中间体，
    由调用方**自己持有**以实现复用；**不**引入隐式缓存 / 全局状态——以什么为键都有漏洞
    （以路径为键则代码改了还命中旧图；以内容哈希为键则要遍历全树算哈希，成本回到原点），
    而且「哪些改动共享了同一张图」将不可见，正是隐性漂移的来源。

    **只放原始事实**：不预计算节点 id 集合 / 反向邻接 / 证据索引——派生属「构造」，塞进采集体
    等于把**消费方的方向假设**写进采集层（M11 教训：采集与构造耦合会让消费方重复实现同一口径）。
    返回键序固定为 `graph, design`。
    """
    # M19：产出不变量——采集端**自证**其产物键序满足契约常量 `PREPARED_REQUIRED_KEYS`（详见 `flow.prepare`
    # 同一注释）：把「契约常量与产物分叉」的失败点从某个消费者运行时，前移到**本定义点**，且诊断**指向生产者**。
    # 对合法输入恒真，不产生任何分支差异（对外产物逐字节不变）。
    body = {
        "graph": graph_builder.build_graph(code_root),
        "design": parser.parse_file(design_doc),
    }
    contract.assert_produced_keys(body, PREPARED_REQUIRED_KEYS, ImpactError, "impact_analyzer")
    return body


def read_diff(diff_path: str | Path) -> str:
    """全仓唯一的「读 diff 文件」实现，编码**沿用现状 `utf-8-sig`**。

    为什么收口：此前该读取内联在 `analyze_files` 里。一旦复用方各自去读，就会产生第二份编码口径，
    带 BOM 的 diff 在一处被剥离、在另一处没有，结果静默分叉。此处的编码口径与重构前**一字不改**
    （编码一改，「与重构前逐字节一致」就当场失效）。
    """
    return Path(diff_path).read_text(encoding="utf-8-sig")


def analyze_prepared(prepared: dict, diff_text: str) -> dict:
    """按 diff 构造：**与 diff 有关**的部分——解析 diff、条目命中、反向闭包传播。

    **只读**传入的 `prepared`：既不修改它，也不注册任何全局状态，故同一 `prepared` 可安全供给
    任意多份 diff 复用；复用次数与污染风险**写在调用点**，可读、可断言。
    返回键序与 `analyze` **逐字一致**。

    M18：取任何键**之前**先做**入口必需键校验**（见模块顶部 `PREPARED_REQUIRED_KEYS` 注释）。
    校验发生在**入口**：故「坏采集体 + 非法 diff 文本」同时成立时，**现在**先报采集体诊断
    （此前会先抛 `parse_unified_diff` 的 diff 错误）——仍是错误路径，错误类型仍是 `ImpactError`。
    """
    contract.require_prepared_keys(prepared, PREPARED_REQUIRED_KEYS, ImpactError, "impact_analyzer")

    changed = parse_unified_diff(diff_text)
    graph = prepared["graph"]
    design = prepared["design"]
    node_ids = {node["id"] for node in graph["nodes"]}

    changed_set = set(changed)
    in_graph = sorted(f for f in changed if f in node_ids)
    out_of_graph = sorted(f for f in changed if f not in node_ids)
    depth = _reverse_closure(graph["nodes"], graph["edges"], in_graph)

    affected_entries: list[dict] = []
    unanchored: list[dict] = []
    for entry in design["entries"]:
        matched: list[dict] = []
        for evidence in entry["required_evidence"]:
            anchor = parser.anchor_of(evidence)
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
    unanchored.sort(key=parser.evidence_key)

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


def analyze(diff_text: str, code_root: str | Path, design_doc: str | Path) -> dict:
    """分析一次 diff 的影响面，返回键序固定、可逐字节复现的结果文档。

    M16：本函数退化为**一层薄编排**——采集（`prepare`）与按 diff 构造（`analyze_prepared`）
    各有唯一实现，此处只顺次调用，采集逻辑**不**在编排层被再写一遍。
    """
    return analyze_prepared(prepare(code_root, design_doc), diff_text)


def analyze_files(
    diff_path: str | Path, code_root: str | Path, design_doc: str | Path
) -> dict:
    """读取 UTF-8 统一 diff 文件后分析；签名与输出与重构前**逐字节不变**（M16：薄编排）。

    读口径**唯一收口**在 `read_diff`（含 `utf-8-sig` 编码），本函数内部不再自行读取。
    """
    return analyze_prepared(prepare(code_root, design_doc), read_diff(diff_path))


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
    """稳定序列化：UTF-8、缩进 2、键序按插入顺序、末尾单换行（M21：口径由 `textio.to_json` 唯一提供，本函数只委派）。"""
    return textio.to_json(doc)
