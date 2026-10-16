"""M2 逻辑地图构建器：从只读代码副本静态构建「模块依赖图 + 文件内符号索引」。

设计口径（对齐 `X产品化路线图-v1.md` §四 M2 行「生成模块依赖图并可下钻到文件/符号」）：
    节点 = 1 个 Python 文件（模块级粒度），节点 id 为扫描根下的相对 POSIX 路径；
    边   = 模块间 import 依赖，区分两类：
             import    —— 普通导入，含函数体内与 `try`/`if TYPE_CHECKING` 等嵌套位置的延迟导入
                          （`ast.walk` 全树收集，因为它们同样是真实依赖）；
             reexport  —— 包 `__init__.py` 内 `from <模块> import <名字>` 形式
                          （把外部名字绑定进包命名空间，即审计关注的「包级绑定」）；
    下钻 = 展开单文件内的顶层 def/class 清单（含行号），层级为 模块 → 文件 → 符号。

为什么这样定：
    ① 只做静态 AST 解析、从不导入被解析模块，故副本内 `eval/types.py` 与
       `eval/validator.py` 互为循环依赖也不会导致构建卡死——环被显式检出后照常输出；
    ② 导入根的判定规则来自副本自身的 `pytest.ini`（`pythonpath = src`），
       因此 `cdm`/`eval` 以 `src` 为根、`tests` 以副本根为根；
       中间目录必须层层具备 `__init__.py` 才算正规包，否则不产出候选模块名
       （否则会把无 `__init__.py` 的 `src/` 目录误判成包，凭空造出 `src.cdm.*` 假节点）。

扫描根由调用方传入（CLI 参数），本模块不写死任何具体路径，以维持与冻结链的物理隔离。
仅依赖 Python 标准库（M2 边界：不引入未安装依赖、不写基线）。
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from . import textio

IMPORT_KIND = "import"
REEXPORT_KIND = "reexport"

# 导入根，顺序即优先级。`src` 来自副本内 pytest.ini 的 pythonpath；
# `.` 是副本根（`tests` 包挂在根下）。判定成立条件见 `_module_names`。
ROOTS = ("src", ".")


class GraphError(ValueError):
    """扫描根不可用或文件无法静态解析时抛出。"""


@dataclass(frozen=True)
class Symbol:
    """文件内的顶层符号（仅模块体直接子节点，不递归进类体/函数体）。"""

    name: str
    kind: str  # class / function / async-function
    line: int

    def to_dict(self) -> dict:
        return {"name": self.name, "kind": self.kind, "line": self.line}


@dataclass(frozen=True)
class Node:
    id: str  # 扫描根下相对 POSIX 路径，作为稳定节点标识
    module: str  # 命中的点分模块名（多根命中时取 ROOTS 序首个）
    symbols: tuple[Symbol, ...]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "module": self.module,
            "symbols": [s.to_dict() for s in self.symbols],
        }


@dataclass(frozen=True)
class Edge:
    src: str
    dst: str
    kind: str

    def to_dict(self) -> dict:
        # 键名用 from/to 表达图语义；本类字段避开 `from` 关键字
        return {"from": self.src, "to": self.dst, "kind": self.kind}


def _dotted(parts: tuple[str, ...]) -> str:
    """路径分量 → 点分模块名：`__init__.py` 归入包名，普通文件去掉 `.py` 后缀。"""
    if parts[-1] == "__init__.py":
        return ".".join(parts[:-1])
    return ".".join(parts[:-1] + (parts[-1][:-3],))


def _package_of(module: str, is_init: bool) -> str:
    """返回模块的 `__package__` 语义值。

    包 `__init__.py` 的所属包就是它自身的包名（`from .x import y` 的基准仍是本包）；
    普通模块则去掉最后一段。二者不同是相对导入解析是否偏移的关键。
    """
    if is_init:
        return module
    return module.rsplit(".", 1)[0] if "." in module else ""


def _module_names(root: Path, rel: str) -> list[str]:
    """该文件在各导入根下可用的点分模块名（按 ROOTS 顺序）；根不成立则不产出候选。"""
    names: list[str] = []
    for prefix in ROOTS:
        if prefix == ".":
            sub, base_dir = rel, root
        elif rel.startswith(prefix + "/"):
            sub, base_dir = rel[len(prefix) + 1 :], root / prefix
        else:
            continue
        parts = tuple(sub.split("/"))
        probe = base_dir
        chain_ok = True
        for d in parts[:-1]:
            probe = probe / d
            if not (probe / "__init__.py").is_file():
                chain_ok = False
                break
        if chain_ok:
            names.append(_dotted(parts))
    return names


def _top_level_symbols(tree: ast.Module) -> tuple[Symbol, ...]:
    """取模块体的直接子节点中的 def/class，按 (行号, 名字) 排序保证输出稳定。

    只看直接子节点：顶层 `if`/`try` 块内缩进的定义不算「文件对外的顶层符号」，
    与独立核查口径（列 0 起头的 def/class）保持一致。
    """
    out: list[Symbol] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            out.append(Symbol(name=node.name, kind="class", line=node.lineno))
        elif isinstance(node, ast.AsyncFunctionDef):
            out.append(Symbol(name=node.name, kind="async-function", line=node.lineno))
        elif isinstance(node, ast.FunctionDef):
            out.append(Symbol(name=node.name, kind="function", line=node.lineno))
    out.sort(key=lambda s: (s.line, s.name))
    return tuple(out)


def _resolve(node: ast.Import | ast.ImportFrom, package_parts: tuple[str, ...]) -> list[str]:
    """把一条导入语句解析为候选点分模块名。

    绝对导入（level=0）不得冠以当前包名，否则会把 `from cdm.id import x` 误解析成
    `eval.cdm.id`；相对导入的基准是当前模块的 `__package__`，level 每加 1 就上退一层。
    """
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if node.level == 0:
        return [node.module] if node.module else []
    parts = list(package_parts)
    drop = node.level - 1
    if drop > len(parts):
        return []  # 越过根，无法解析
    if drop:
        parts = parts[: len(parts) - drop]
    if node.module:
        parts.extend(node.module.split("."))
    return [".".join(parts)] if parts else []


def _edge_kind(node: ast.Import | ast.ImportFrom, is_init: bool) -> str:
    """包 `__init__.py` 内的 `from <模块> import <名字>` 记为重导出。

    判定只看形状（导入方是包 `__init__` 且是具名 ImportFrom），不做被导入名
    「是符号还是子模块」的语义推断——那需要真正导入模块，超出静态解析边界。
    """
    named = isinstance(node, ast.ImportFrom) and bool(node.names) and node.names[0].name != "*"
    return REEXPORT_KIND if (is_init and named) else IMPORT_KIND


def _cycles(adj: dict[str, list[str]]) -> list[list[str]]:
    """Tarjan 求强连通分量，仅返回含环的分量（大小 >= 2，或自指单点）。

    用显式栈而非递归：副本规模小，但避免未来大仓库触发递归深度上限。
    """
    index_of: dict[str, int] = {}
    low: dict[str, int] = {}
    on_stack: set[str] = set()
    stack: list[str] = []
    found: list[list[str]] = []
    counter = 0
    for root in sorted(adj):
        if root in index_of:
            continue
        index_of[root] = low[root] = counter
        counter += 1
        stack.append(root)
        on_stack.add(root)
        work: list[tuple[str, list[str], int]] = [(root, sorted(adj[root]), 0)]
        while work:
            v, targets, i = work.pop()
            if i < len(targets):
                work.append((v, targets, i + 1))
                w = targets[i]
                if w not in index_of:
                    index_of[w] = low[w] = counter
                    counter += 1
                    stack.append(w)
                    on_stack.add(w)
                    work.append((w, sorted(adj.get(w, ())), 0))
                elif w in on_stack:
                    low[v] = min(low[v], index_of[w])
                continue
            if low[v] == index_of[v]:
                comp: list[str] = []
                while True:
                    w = stack.pop()
                    on_stack.discard(w)
                    comp.append(w)
                    if w == v:
                        break
                comp.sort()
                if len(comp) > 1 or v in adj.get(v, ()):
                    found.append(comp)
            if work:
                parent = work[-1][0]
                low[parent] = min(low[parent], low[v])
    found.sort()
    return found


def build_graph(root: str | Path) -> dict:
    """扫描 `root` 下的全部 .py 文件，返回图文档（键序固定，可逐字节复现）。

    返回结构：node_count / edge_count / nodes / edges / cycles。
    边按 (from, to, kind) 去重：同一对模块间的多条同型导入语句是同一条图边，
    保留逐语句行号对 M2 的「节点数/边数/下钻路径」判定无增量，故不登记。
    """
    root = Path(root)
    if not root.is_dir():
        raise GraphError(f"扫描根不是目录：{root}")

    rel_paths = sorted(p.relative_to(root).as_posix() for p in root.rglob("*.py"))
    if not rel_paths:
        raise GraphError(f"扫描根下没有 .py 文件：{root}")

    names_of: dict[str, list[str]] = {}
    by_name: dict[str, str] = {}
    for rel in rel_paths:
        names = _module_names(root, rel)
        names_of[rel] = names
        for name in names:
            by_name.setdefault(name, rel)  # 同名多命中时取路径序首个，保证确定性

    nodes: list[Node] = []
    edge_keys: set[tuple[str, str, str]] = set()
    for rel in rel_paths:
        text = (root / rel).read_text(encoding="utf-8-sig")
        try:
            tree = ast.parse(text, filename=rel)
        except SyntaxError as exc:
            raise GraphError(f"无法静态解析 {rel}：{exc}") from None
        is_init = rel.endswith("__init__.py")
        module = names_of[rel][0] if names_of[rel] else ""
        package_parts = tuple(_package_of(module, is_init).split(".")) if module else ()
        for stmt in ast.walk(tree):
            if not isinstance(stmt, (ast.Import, ast.ImportFrom)):
                continue
            kind = _edge_kind(stmt, is_init)
            for cand in _resolve(stmt, package_parts):
                dst = by_name.get(cand)
                # 未命中即目标在副本之外（标准库/第三方），M2 只登记副本内节点
                if dst is None:
                    continue
                edge_keys.add((rel, dst, kind))
        nodes.append(Node(id=rel, module=module, symbols=_top_level_symbols(tree)))

    edges = [Edge(*key) for key in sorted(edge_keys)]
    adj: dict[str, list[str]] = {n.id: [] for n in nodes}
    for e in edges:
        adj[e.src].append(e.dst)

    node_list = [n.to_dict() for n in sorted(nodes, key=lambda n: n.id)]
    edge_list = [e.to_dict() for e in edges]
    return {
        "node_count": len(node_list),
        "edge_count": len(edge_list),
        "nodes": node_list,
        "edges": edge_list,
        "cycles": _cycles(adj),
    }


def render_node_tree(doc: dict, node_id: str) -> str:
    """把单个节点的下钻内容渲染为确定性 ASCII 文本（模块 → 文件 → 符号）。

    层级固定为：节点行 → module → symbols → imports → imported-by，
    各段内按 id/行号升序，空段照样打印 `(0):`，便于逐字节断言。
    """
    nodes = {n["id"]: n for n in doc["nodes"]}
    if node_id not in nodes:
        raise GraphError(f"图中不存在节点：{node_id}")
    node = nodes[node_id]
    imports = sorted((e["to"], e["kind"]) for e in doc["edges"] if e["from"] == node_id)
    imported_by = sorted((e["from"], e["kind"]) for e in doc["edges"] if e["to"] == node_id)

    lines = [f"node: {node['id']}", f"  module: {node['module']}"]
    lines.append(f"  symbols ({len(node['symbols'])}):")
    lines.extend(f"    L{s['line']} {s['kind']} {s['name']}" for s in node["symbols"])
    lines.append(f"  imports ({len(imports)}):")
    lines.extend(f"    {dst} [{kind}]" for dst, kind in imports)
    lines.append(f"  imported-by ({len(imported_by)}):")
    lines.extend(f"    {src} [{kind}]" for src, kind in imported_by)
    return "\n".join(lines) + "\n"


def to_json(doc: dict) -> str:
    """稳定序列化：UTF-8、缩进 2、键序按插入顺序、末尾单换行（M21：口径由 `textio.to_json` 唯一提供，本函数只委派）。"""
    return textio.to_json(doc)
