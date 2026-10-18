"""M36 自测：把「可视面 `--plan` 汇合路径的采集一次 / 复用多次」的验收点写成可执行断言。

背景（`X产品化-M36设计稿-v1.md` §一）：M35 把 `conflict.analyze_plan` 接进了 `viewer.analyze`
（**同一进程**）。此前可视面与冲突路径各自独立、互不同进程；接进来之后，同一份
`(代码根, 设计文档, 流程文档)` 在同一进程里被**两侧各采一遍**——设计文档解析 2 次、依赖图构建 2 次、
流程文档解析 2 次。M36 把 M15 / M16 / M17 已三次确立的治理规则「采集一次 / 复用多次 + 显式中间体
（零隐式缓存）」应用到这条 M35 **新造出来的**汇合路径上。

核心思路：**夹具临时自建**——每次测试在临时目录里现造最小代码根 + 设计文档 + 流程文档 + 分工计划；
本自测**不依赖**任何归档基线副本、不依赖网络。**计数**才是「2 次变 1 次」的直接证据（耗时受机器抖动
影响、不可复现）：本文件用**计数探针**临时包装 `parser.parse_file` / `graph_builder.build_graph` /
`flow.parse_flow_doc`，`try/finally` 还原，并同时给出「M36 之前的汇合方式」的**对照基线**（各 2 次）。

覆盖（对应设计稿 §七 ①–⑩）：
  ① / ② / ③ 复用计数（核心证据）：`viewer.analyze(root, design, flow_doc, diff, plan)` →
     `parse_file` / `build_graph` / `parse_flow_doc` 各 **== 1**；**对照**「M36 之前的汇合方式」
     （`drift.prepare` + `graph_builder.build_graph` + `flow.analyze` + `conflict.analyze_plan`）→ 各 **== 2**；
  ④ 采集次数零退化：5 种选段组合下三类计数**逐条等于**该组合的**必需次数**（`--plan` 缺席时**不**多采）；
  ⑤ 薄编排等价：`analyze_plan` 与 `analyze_plan_prepared(load_plan, prepare, prepare)` 逐字节一致；
     `prepare_from_parts(build_graph, parse_file)` 与 `prepare` 深比较相等且键序同为 `("graph","design")`；
  ⑥ 输出逐字节不变：5 种选段组合下新汇合产物与「M36 之前的汇合方式」**深比较相等**、页面**逐字节一致**；
     CLI stdout 与库输出逐字节一致、无 `\\r\\n`；
  ⑦ 中间体只读 + 复用稳定：三件中间体在复用调用前后复合摘要不变；连续 5 次复用结果逐字节一致；
  ⑧ 零隐式缓存（结构断言）：全仓无隐式缓存装饰 / 引用（特征串分段拼接）、无缓存工具模块导入；
     `prepare_from_parts` / `analyze_plan_prepared` 体内**零**采集调用；`viewer.analyze` 的流程采集点**恰 1 处**；
  ⑨ 既有自测零修订：无需参数的自测各按**实测**条数全绿（经共享 `assert_regression`）；
  ⑩ 全域回归 + 编号无关性：逆序逐模块跑同一批自测仍全绿；需代码根者仍恰为 `m2` / `m3`。

**自指防护**（沿用 M23–M35）：本文件同样会被多份既有结构断言扫到，故凡以**源码文本**为输入的断言，
其待查特征串一律**分段拼接**（`"funct" + "ools"`、`"lru" + "_cache"`），使度量器自身（含 docstring /
注释）**不字面出现**该特征串；且新增拼接常量已逐条用全仓既有扫描正则自检。

沿用 M0–M35 约定：**不**用管道捕获输出，改临时文件重定向（本机沙箱禁建管道）——
本文件自身的脚手架调用一律经 `selftest_kit` 唯一实现，**不**内联子进程调用。
"""

from __future__ import annotations

import ast
import hashlib
import inspect
import json
import tempfile
from pathlib import Path

from . import conflict, drift, flow, graph_builder, impact_analyzer, parser, selftest_kit, sync, viewer
from .selftest_kit import (
    PKG_DIR,
    assert_regression,
    cli as _cli,
    dir_digest as _dir_digest,
    make_fixture as _fixture,
    number_independence_regression,
    ARG_EXEMPT as _ARG_EXEMPT,
    ARGV_MARK as _ARGV_MARK,
)

# 待查特征串**分段拼接**（见模块 docstring 的「自指防护」）：拼出的结果不在本文件源码中字面出现
_CACHE_REF = "lru" + "_cache"            # 隐式缓存装饰 / 引用的特征名（⑧）
_CACHE_MOD = "funct" + "ools"            # 缓存工具模块名（⑧）
_COLLECT_CALLS = ("build_graph", "parse_file", "parse_flow_doc")   # 三件「采集」原语之名（⑧）

# 确认过「采集次数」的三件与 diff 无关的原语：本文件用探针计数，不受计时抖动影响
_COUNTERS = ("parse_file", "build_graph", "parse_flow_doc")


# --- 夹具数据（本模块自己的三份；与其余自测同形，仅题头不同）----------------------------


_DESIGN = (
    "# 夹具设计文档（M36 自测专用）\n"
    "\n"
    "### OK-001 — 精确锚 api.py（活性）\n"
    "- type: 公共接口\n"
    "- invariant: 示例不变量\n"
    "- change_control: free\n"
    "- severity: normal\n"
    "- evidence:\n"
    "  - src/app/api.py\n"
    "- action_policy: 警告\n"
    "\n"
    "### OK-002 — 精确锚 core.py（活性）\n"
    "- type: 数据完整性\n"
    "- invariant: 示例不变量\n"
    "- change_control: free\n"
    "- severity: normal\n"
    "- evidence:\n"
    "  - src/app/core.py\n"
    "- action_policy: 警告\n"
)

_FLOW = (
    "# 流程夹具（M36 自测专用）\n"
    "\n"
    "## FL-001 — 下单到发货\n"
    "\n"
    "- step:\n"
    "  - S1: 校验库存 @ src/app/api.py\n"
    "  - S2: 扣减库存 @ src/app/core.py\n"
    "  - S3: 发货通知 @ src/app/notify.py\n"
    "- edge:\n"
    "  - S1 -> S2\n"
    "  - S2 -> S3\n"
)

# 4 元计划：A / B **同时**改 `src/app/core.py`（→ 文件层 + 条目层 + 流程层三重命中），
# C / D 各改一份非 `.py` 载体（→ 两层均不命中）。两类冲突因此**同时**出现在同一份文档里。
_PLAN_CHANGES = (
    ("A", "src/app/core.py", "X = 2\n"),
    ("B", "src/app/core.py", "X = 3\n"),
    ("C", "docs/guide.md", "c\n"),
    ("D", "docs/spec.md", "d\n"),
)

# ⑨ / ⑩ 的 33 个无需命令行参数的自测（`m2` / `m3` 需代码根，由 ⑩ 的边界先行校验覆盖）；条数为**实测**
_REGRESSION = {
    "selftest": "4/4",
    "selftest_m1": "7/7",
    "selftest_m5": "13/13",
    "selftest_m6": "13/13",
    "selftest_m7": "12/12",
    "selftest_m8": "12/12",
    "selftest_m9": "9/9",
    "selftest_m10": "11/11",
    "selftest_m11": "10/10",
    "selftest_m12": "12/12",
    "selftest_m13": "10/10",
    "selftest_m14": "10/10",
    "selftest_m15": "10/10",
    "selftest_m16": "10/10",
    "selftest_m17": "10/10",
    "selftest_m18": "10/10",
    "selftest_m19": "8/8",
    "selftest_m20": "8/8",
    "selftest_m21": "8/8",
    "selftest_m22": "8/8",
    "selftest_m23": "8/8",
    "selftest_m24": "8/8",
    "selftest_m25": "8/8",
    "selftest_m26": "8/8",
    "selftest_m27": "8/8",
    "selftest_m28": "8/8",
    "selftest_m29": "8/8",
    "selftest_m30": "8/8",
    "selftest_m31": "8/8",
    "selftest_m32": "8/8",
    "selftest_m33": "8/8",
    "selftest_m34": "8/8",
    "selftest_m35": "11/11",
}


# --- 夹具与计划 JSON 的构造（本模块自建，不依赖任何归档副本）------------------------------


def _write_plan(td: Path, name: str, plan_id: object, cids: tuple[str, ...]) -> Path:
    """把一份分工计划写成 JSON（`diff` 用**相对文件名**，相对计划文件所在目录解析）。

    字节流写盘：避免 Windows 文本模式把 `\\n` 译成 `\\r\\n` 而改变 `load_plan` 的读入字节。
    """
    doc = {"plan_id": plan_id, "changesets": [{"id": c, "diff": f"{c}.diff"} for c in cids]}
    p = td / name
    p.write_bytes(json.dumps(doc, ensure_ascii=False).encode("utf-8"))
    return p


# --- 对照基线：M36 **之前**的汇合方式（计数对照 + 产物对照，两用同一函数以保同源）--------------


def _legacy_viewer_doc(
    code_root: str,
    design_doc: str,
    baseline: dict | None = None,
    flow_doc: str | None = None,
    diff_file: str | None = None,
    plan_file: str | None = None,
) -> dict:
    """M36 **之前**的汇合方式（对照路径）：可视面各段各自采集一次，冲突段**再**采一遍。

    刻意在测试里保留这条旧路径：它既是 ①②③ 计数断言的**对照基线**（三类各采 **2** 次），也是 ⑥
    「对外产物是否逐字节不变」的**对照基线**——两份**结构不同**的文档不得拿来比对，故两者必须同源
    （键序、各段取值均由同一批既有实现产生；若将来有人把二次采集改回来，⑤ 的计数断言会立刻失败，
    这正是「用计数而不是用感觉」的用意，沿用 M17 ⑩ 的对照思路）。

    注意：本函数体**逐字复刻** M35 期 `viewer.analyze` 的取数顺序（`drift.prepare` → 可视面自己的
    `graph_builder.build_graph` → `flow.analyze` → `conflict.analyze_plan`），故冲突段在这一路径下
    **会**再经 `impact_analyzer.prepare` + `flow.prepare` 各采一遍。
    """
    prepared = drift.prepare(code_root, design_doc)
    drift_doc = drift.analyze_prepared(prepared)
    design = prepared["design"]
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
    doc["conflict"] = (
        conflict.analyze_plan(plan_file, code_root, design_doc, flow_doc)
        if plan_file is not None
        else None
    )
    return doc


class _Probe:
    """计数探针：临时包装三件采集原语，`try/finally` 还原。

    为什么不用「计时」：耗时受机器抖动影响、不可复现；**计数**才是「2 次变成 1 次」的直接证据。
    为什么只包这三件：它们正是「与 diff 无关」的三件事——枚举 `.py` 依赖图、解析设计文档、解析流程文档；
    构造入口（`*_prepared` / `analyze_plan_prepared`）一个都不调，故计数即等价于「采集发生了几次」。
    """

    def __init__(self) -> None:
        self.calls = {name: 0 for name in _COUNTERS}

    def __enter__(self) -> "_Probe":
        self._orig = {
            "parse_file": parser.parse_file,
            "build_graph": graph_builder.build_graph,
            "parse_flow_doc": flow.parse_flow_doc,
        }

        def wrap(key: str, fn):
            def wrapped(*args, **kwargs):
                self.calls[key] += 1
                return fn(*args, **kwargs)

            return wrapped

        parser.parse_file = wrap("parse_file", self._orig["parse_file"])
        graph_builder.build_graph = wrap("build_graph", self._orig["build_graph"])
        flow.parse_flow_doc = wrap("parse_flow_doc", self._orig["parse_flow_doc"])
        return self

    def __exit__(self, *exc: object) -> bool:
        parser.parse_file = self._orig["parse_file"]
        graph_builder.build_graph = self._orig["build_graph"]
        flow.parse_flow_doc = self._orig["parse_flow_doc"]
        return False


# --- ⑦ 用的复合摘要；⑧ 用的 AST 工具（均只读）-------------------------------------------


def _body_digest(obj: object) -> str:
    """采集体 / 产物的复合摘要（只读证据）：`repr` 口径固定、集合先排序，故同对象前后可比。"""

    def norm(o: object) -> object:
        if isinstance(o, dict):
            return {k: norm(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [norm(v) for v in o]
        if isinstance(o, (set, frozenset)):
            return sorted(repr(v) for v in o)
        return o

    return hashlib.sha256(repr(norm(obj)).encode("utf-8")).hexdigest()


def _module_calls(path: Path) -> set[str]:
    """某文件内**全部调用**的「被调名」（`ast.Name.id` 或 `ast.Attribute.attr`），忽略 docstring / 注释。"""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Name):
                names.add(f.id)
            elif isinstance(f, ast.Attribute):
                names.add(f.attr)
    return names


def _func_calls(func_obj: object) -> set[str]:
    """某函数体内**全部调用**的「被调名」（按源码 AST 解析，docstring / 注释不参与）。"""
    tree = ast.parse(inspect.getsource(func_obj))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Name):
                names.add(f.id)
            elif isinstance(f, ast.Attribute):
                names.add(f.attr)
    return names


def _count_calls(func_obj: object, module: str, name: str) -> int:
    """数某函数体内形如 `module.name(...)` 的调用次数（用于「采集点恰 1 处」的结构断言）。"""
    tree = ast.parse(inspect.getsource(func_obj))
    n = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            f = node.func
            if f.attr == name and isinstance(f.value, ast.Name) and f.value.id == module:
                n += 1
    return n


# --- ① 断言 ------------------------------------------------------------------------


def test_reuse_counter_design_doc() -> None:
    """① 复用计数（设计文档，核心证据）：`parser.parse_file` 在 `view … --plan` 下 == 1；对照 == 2。"""
    with tempfile.TemporaryDirectory() as td:
        td_p = Path(td)
        root, design, flow_doc, diffs = _fixture(
            td_p, design_text=_DESIGN, flow_text=_FLOW, changes=_PLAN_CHANGES
        )
        plan = _write_plan(td_p, "plan.json", "P-1", ("A", "B", "C", "D"))

        with _Probe() as probe:
            viewer.analyze(str(root), str(design), None, str(flow_doc), str(diffs["A"]), str(plan))
        assert probe.calls["parse_file"] == 1, \
            f"汇合路径下设计文档应只解析 1 次，实际 {probe.calls}"

        with _Probe() as control:
            _legacy_viewer_doc(str(root), str(design), None, str(flow_doc), str(diffs["A"]), str(plan))
        assert control.calls["parse_file"] == 2, \
            f"M36 之前的汇合方式应解析设计文档 2 次（对照基线），实际 {control.calls}"


# --- ② 断言 ------------------------------------------------------------------------


def test_reuse_counter_dependency_graph() -> None:
    """② 复用计数（依赖图，核心证据）：`graph_builder.build_graph` 在 `view … --plan` 下 == 1；对照 == 2。"""
    with tempfile.TemporaryDirectory() as td:
        td_p = Path(td)
        root, design, flow_doc, diffs = _fixture(
            td_p, design_text=_DESIGN, flow_text=_FLOW, changes=_PLAN_CHANGES
        )
        plan = _write_plan(td_p, "plan.json", "P-1", ("A", "B", "C", "D"))

        with _Probe() as probe:
            viewer.analyze(str(root), str(design), None, str(flow_doc), str(diffs["A"]), str(plan))
        assert probe.calls["build_graph"] == 1, \
            f"汇合路径下依赖图应只构建 1 次，实际 {probe.calls}"

        with _Probe() as control:
            _legacy_viewer_doc(str(root), str(design), None, str(flow_doc), str(diffs["A"]), str(plan))
        assert control.calls["build_graph"] == 2, \
            f"M36 之前的汇合方式应构建依赖图 2 次（对照基线），实际 {control.calls}"


# --- ③ 断言 ------------------------------------------------------------------------


def test_reuse_counter_flow_doc() -> None:
    """③ 复用计数（流程文档，核心证据）：`flow.parse_flow_doc` 在 `view … --plan` 下 == 1；对照 == 2。"""
    with tempfile.TemporaryDirectory() as td:
        td_p = Path(td)
        root, design, flow_doc, diffs = _fixture(
            td_p, design_text=_DESIGN, flow_text=_FLOW, changes=_PLAN_CHANGES
        )
        plan = _write_plan(td_p, "plan.json", "P-1", ("A", "B", "C", "D"))

        with _Probe() as probe:
            viewer.analyze(str(root), str(design), None, str(flow_doc), str(diffs["A"]), str(plan))
        assert probe.calls["parse_flow_doc"] == 1, \
            f"汇合路径下流程文档应只解析 1 次，实际 {probe.calls}"

        with _Probe() as control:
            _legacy_viewer_doc(str(root), str(design), None, str(flow_doc), str(diffs["A"]), str(plan))
        assert control.calls["parse_flow_doc"] == 2, \
            f"M36 之前的汇合方式应解析流程文档 2 次（对照基线），实际 {control.calls}"


# --- ④ 断言 ------------------------------------------------------------------------


def test_no_extra_collection_per_segment_combo() -> None:
    """④ 采集次数零退化：5 种选段组合的三类计数**逐条等于**该组合的必需次数（`--plan` 缺席不多采）。"""
    with tempfile.TemporaryDirectory() as td:
        td_p = Path(td)
        root, design, flow_doc, diffs = _fixture(
            td_p, design_text=_DESIGN, flow_text=_FLOW, changes=_PLAN_CHANGES
        )
        plan = _write_plan(td_p, "plan.json", "P-1", ("A", "B", "C", "D"))
        # 基线快照在探针之外先算好，使探针只计「可视面这一次汇合」的采集
        baseline = sync.snapshot_from_drift(drift.analyze(str(root), str(design)))

        combos = (
            ("无选段", dict(), {"parse_file": 1, "build_graph": 1, "parse_flow_doc": 0}),
            ("--baseline", dict(baseline=baseline), {"parse_file": 1, "build_graph": 1, "parse_flow_doc": 0}),
            ("--flow", dict(flow_doc=str(flow_doc)), {"parse_file": 1, "build_graph": 1, "parse_flow_doc": 1}),
            (
                "--flow --diff",
                dict(flow_doc=str(flow_doc), diff_file=str(diffs["A"])),
                {"parse_file": 1, "build_graph": 1, "parse_flow_doc": 1},
            ),
            (
                "--flow --plan",
                dict(flow_doc=str(flow_doc), plan_file=str(plan)),
                {"parse_file": 1, "build_graph": 1, "parse_flow_doc": 1},
            ),
        )
        for label, kwargs, want in combos:
            with _Probe() as probe:
                viewer.analyze(str(root), str(design), **kwargs)
            assert probe.calls == want, f"{label} 组合的采集次数应与必需次数逐条相等，实际 {probe.calls}"


# --- ⑤ 断言 ------------------------------------------------------------------------


def test_thin_shell_equivalence() -> None:
    """⑤ 薄编排等价：`analyze_plan` 与两段调用逐字节一致；`prepare_from_parts` 与 `prepare` 深比较相等。"""
    with tempfile.TemporaryDirectory() as td:
        td_p = Path(td)
        root, design, flow_doc, diffs = _fixture(
            td_p, design_text=_DESIGN, flow_text=_FLOW, changes=_PLAN_CHANGES
        )
        plan = _write_plan(td_p, "plan.json", "P-1", ("A", "B", "C", "D"))

        legacy = conflict.analyze_plan(str(plan), str(root), str(design), str(flow_doc))
        split = conflict.analyze_plan_prepared(
            conflict.load_plan(str(plan)),
            impact_analyzer.prepare(str(root), str(design)),
            flow.prepare(str(flow_doc), str(root)),
        )
        assert json.dumps(legacy, ensure_ascii=False) == json.dumps(split, ensure_ascii=False), \
            "薄编排应与构造入口逐字节一致（含键序）"
        assert conflict.render_text(legacy) == conflict.render_text(split), "文本口径同样不得有差异"

        # 未给流程文档时同样等价（流程层键**不出现**）
        legacy2 = conflict.analyze_plan(str(plan), str(root), str(design))
        split2 = conflict.analyze_plan_prepared(
            conflict.load_plan(str(plan)), impact_analyzer.prepare(str(root), str(design)), None
        )
        assert json.dumps(legacy2, ensure_ascii=False) == json.dumps(split2, ensure_ascii=False), \
            "未给流程文档时薄编排仍应与构造入口逐字节一致"

        parts = impact_analyzer.prepare_from_parts(
            graph_builder.build_graph(str(root)), parser.parse_file(str(design))
        )
        direct = impact_analyzer.prepare(str(root), str(design))
        assert parts == direct, "prepare_from_parts 应与 prepare 深比较相等"
        assert list(parts) == ["graph", "design"] == list(direct), \
            f"两者键序应同为 ('graph','design')，实际 {list(parts)} / {list(direct)}"


# --- ⑥ 断言 ------------------------------------------------------------------------


def test_output_byte_identical() -> None:
    """⑥ 输出逐字节不变：5 种组合下新产物与旧汇合深比较相等、页面逐字节一致；CLI stdout 与库输出一致。"""
    with tempfile.TemporaryDirectory() as td:
        td_p = Path(td)
        root, design, flow_doc, diffs = _fixture(
            td_p, design_text=_DESIGN, flow_text=_FLOW, changes=_PLAN_CHANGES
        )
        plan = _write_plan(td_p, "plan.json", "P-1", ("A", "B", "C", "D"))
        baseline = sync.snapshot_from_drift(drift.analyze(str(root), str(design)))
        base_file = td_p / "base.json"
        sync.save_snapshot(base_file, baseline)

        combos = (
            ("无选段", dict(), ()),
            ("--baseline", dict(baseline=baseline), ("--baseline", str(base_file))),
            ("--flow", dict(flow_doc=str(flow_doc)), ("--flow", str(flow_doc))),
            (
                "--flow --diff",
                dict(flow_doc=str(flow_doc), diff_file=str(diffs["A"])),
                ("--flow", str(flow_doc), "--diff", str(diffs["A"])),
            ),
            (
                "--flow --plan",
                dict(flow_doc=str(flow_doc), plan_file=str(plan)),
                ("--flow", str(flow_doc), "--plan", str(plan)),
            ),
        )
        for label, kwargs, cli_args in combos:
            new_doc = viewer.analyze(str(root), str(design), **kwargs)
            old_doc = _legacy_viewer_doc(str(root), str(design), **kwargs)
            assert list(new_doc) == list(old_doc), f"{label}：键序应与旧汇合逐条相同"
            assert json.dumps(new_doc, ensure_ascii=False) == json.dumps(old_doc, ensure_ascii=False), \
                f"{label}：产物应与旧汇合逐字节一致（对外产物不得变）"
            page = viewer.render_html(new_doc)
            assert page == viewer.render_html(old_doc), f"{label}：页面应与旧汇合逐字节一致"

            rc, out, err = _cli("view", str(root), str(design), *cli_args)
            assert rc == 0, f"{label}：CLI 应退出码 0，实际 {rc}；stderr={err[-200:]!r}"
            assert out == page.encode("utf-8"), f"{label}：CLI stdout 应与库输出逐字节一致"
            assert b"\r\n" not in out, f"{label}：stdout 不得含 CRLF（字节稳定写盘）"


# --- ⑦ 断言 ------------------------------------------------------------------------


def test_intermediates_read_only_and_stable() -> None:
    """⑦ 中间体只读 + 复用稳定：三件中间体在复用前后复合摘要不变；连续 5 次复用结果逐字节一致。"""
    with tempfile.TemporaryDirectory() as td:
        td_p = Path(td)
        root, design, flow_doc, diffs = _fixture(
            td_p, design_text=_DESIGN, flow_text=_FLOW, changes=_PLAN_CHANGES
        )
        plan_path = _write_plan(td_p, "plan.json", "P-1", ("A", "B", "C", "D"))
        plan = conflict.load_plan(str(plan_path))
        graph = graph_builder.build_graph(str(root))
        design_model = parser.parse_file(str(design))
        flow_prepared = flow.prepare(str(flow_doc), str(root))
        before = (_body_digest(graph), _body_digest(design_model), _body_digest(flow_prepared))

        got: list[str] = []
        for _ in range(5):
            doc = conflict.analyze_plan_prepared(
                plan, impact_analyzer.prepare_from_parts(graph, design_model), flow_prepared
            )
            flow.analyze_prepared(flow_prepared, str(diffs["A"]))
            got.append(json.dumps(doc, ensure_ascii=False))

        after = (_body_digest(graph), _body_digest(design_model), _body_digest(flow_prepared))
        assert before == after, "独立出的三件中间体在复用调用前后不得发生任何变化（只读）"
        assert len(set(got)) == 1, "同一批中间体连续 5 次复用的结果应逐字节一致"

        # 端到端复用同样不得写夹具目录（沿用 M35 只读口径）
        td_before = _dir_digest(td_p)
        viewer.analyze(str(root), str(design), None, str(flow_doc), str(diffs["A"]), str(plan_path))
        assert _dir_digest(td_p) == td_before, "可视面汇合全程不得写夹具中的任何一个字节"


# --- ⑧ 断言 ------------------------------------------------------------------------


def test_no_implicit_cache() -> None:
    """⑧ 零隐式缓存（结构断言）：无隐式缓存装饰/引用与缓存工具模块导入；构造入口零采集；采集点恰 1 处。"""
    for p in sorted(PKG_DIR.glob("*.py")):
        tree = ast.parse(p.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    assert a.name != _CACHE_MOD, f"{p.name} 不得导入缓存工具模块（隐式缓存）"
            elif isinstance(node, ast.ImportFrom):
                assert node.module != _CACHE_MOD, f"{p.name} 不得自缓存工具模块导入（隐式缓存）"
            elif isinstance(node, ast.Name):
                assert node.id != _CACHE_REF, f"{p.name} 不得引用隐式缓存装饰名"
            elif isinstance(node, ast.Attribute):
                assert node.attr != _CACHE_REF, f"{p.name} 不得引用隐式缓存装饰名"

    # 构造入口体内**零**采集：不建图、不解析设计文档、不解析流程文档、不调任何 `prepare`
    for func_obj in (impact_analyzer.prepare_from_parts, conflict.analyze_plan_prepared):
        calls = _func_calls(func_obj)
        hit = calls.intersection(set(_COLLECT_CALLS) | {"prepare"})
        assert not hit, f"{func_obj.__name__} 体内不得出现采集调用（应只组装 / 构造），实际命中 {sorted(hit)}"

    # 采集点恰 1 处：可视面对流程文档只在**同一处**采集一次（旧写法是两处：流程段 + 冲突段）
    assert _count_calls(viewer.analyze, "flow", "prepare") == 1, \
        "viewer.analyze 对流程文档的采集点应恰 1 处（同一份供流程段与冲突段复用）"
    assert _count_calls(viewer.analyze, "graph_builder", "build_graph") == 1, \
        "viewer.analyze 对依赖图的采集点应恰 1 处"
    _module_calls(PKG_DIR / "conflict.py")  # 只读解析，确保构造入口所在文件可被 AST 解析（无副作用）


# --- ⑨ / ⑩ 33 个无需命令行参数的自测（`m2` / `m3` 需代码根，见 ⑩）；条数为**实测** ------------


def test_existing_selftests_regression() -> None:
    """⑨ 既有自测零修订：33 个无需参数的自测各按实测条数全绿（经共享 `assert_regression`）。"""
    if selftest_kit.in_regression():
        return
    assert_regression(_REGRESSION)


def test_full_regression_and_number_independence() -> None:
    """⑩ 全域回归 + 编号无关性：逆序逐模块跑同一批自测仍全绿（与 ⑨ 逐条一致）；需代码根者恰 m2/m3。"""
    if selftest_kit.in_regression():
        return
    number_independence_regression(_REGRESSION, _ARGV_MARK, _ARG_EXEMPT)


def main() -> int:
    tests = (
        test_reuse_counter_design_doc,
        test_reuse_counter_dependency_graph,
        test_reuse_counter_flow_doc,
        test_no_extra_collection_per_segment_combo,
        test_thin_shell_equivalence,
        test_output_byte_identical,
        test_intermediates_read_only_and_stable,
        test_no_implicit_cache,
        test_existing_selftests_regression,
        test_full_regression_and_number_independence,
    )
    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as exc:
            failed += 1
            print(f"FAIL {t.__name__}: {exc}")
        else:
            print(f"PASS {t.__name__}")
    print(f"{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
