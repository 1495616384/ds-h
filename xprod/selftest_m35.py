"""M35 自测：把「分工计划冲突接入可视面」的验收点写成可执行断言。

背景（`X产品化-M35设计稿-v1.md` §一）：《X产品化-M14设计稿-v1.md》§七 第 6 条登记过一条遗留——
流程层冲突**只**做进了 CLI 层、**未**接入可视面。`xprod/viewer.py` 因此只有同步段与流程影响段，
看不到 M7/M14 的分工计划冲突。M35 兑现该遗留：`view` 新增**可选** `--plan <plan.json>`（**依赖**
`--flow`），给了就在流程段之后追加一段「分工计划冲突」，其内容**原样**取自 `conflict.analyze_plan`
的返回文档（**零新判定、零裁剪、不二次排序**）。

**不变量**（设计稿 §二 2.2 / §四）：未给 `--plan` 时页面**逐字节不变**（冲突段**不出现**，而非
出现并置空）；`_CSS` **一行不加**（冲突段只用既有类名）。故本文件 ① 同时断言「`conflict` 键为
`None` 时对页面零影响」与「冲突段用到的所有类名都已在 `_CSS` 中定义」——后者是「零新 CSS」
的**结构证据**，无需写死任何行数常量。

**自指防护**（沿用 M32/M33/M34）：本文件同样会被多份既有结构断言扫到，故凡以**源码文本**为输入的
待查特征串一律**分段拼接**构造（`"flow" + "_conflict"`、`"<section id=" + '"conflict">'` …），
使度量器自身（含 docstring / 注释）**不字面出现**该特征串。

覆盖（对应设计稿 §八 ①–⑧）：
  ① **无 `--plan` 的回归**：5 参与 6 参（`plan_file=None`）分析文档**深比较相等**；`doc["conflict"]
     为 `None`；页面**无**冲突段；「移除 `conflict` 键后再渲染」与实渲染**逐字节一致**；冲突渲染入口
     在 `viewer.py` **恰 1 处**；冲突段只用既有类名（全部已在 `_CSS` 中）；
  ② **来源一致（取自而非重算）**：`doc["conflict"]` 与 `conflict.analyze_plan(…)` 直算结果**深比较相等**；
  ③ **段落落位与计数一致**：冲突段位于流程段**之后**、条目段**之前**；三个计数与文档对应值**逐一相等**；
  ④ **两层冲突均呈现**：`shared file` / `shared entry` 与 `shared step` / `shared flow` 同现，
     且 `kinds` 与文档一致；
  ⑤ **不误报**：无冲突计划 → 判定 `clear`、配色 `ok`、冲突对 `0`、流程层判定同为 `clear`；
  ⑥ **确定性 + 顺序保真**：同输入两次渲染**逐字节一致**；改动清单 / 冲突对 / 共享集合的顺序与文档
     **逐条一致**（可视面**不**二次排序）；
  ⑦ **只读**：分析 / 渲染 / CLI 全程夹具目录复合摘要**不变**；
  ⑧ **CLI 与退出码**：正常路径退出码 **0**、stdout 与库输出**逐字节一致**、**无 `\\r\\n`**；
     `--plan` **缺值** → **2**；`--plan` **缺 `--flow`** → **2**；坏计划 → **1**；
     **无 `--plan`** 时 stdout 与库输出**逐字节一致**。

沿用 M0–M34 约定：**不**用管道捕获输出，改临时文件重定向（本机沙箱禁建管道）——
本文件自身的脚手架调用一律经 `selftest_kit` 唯一实现，**不**内联子进程调用。
"""

from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path

from . import conflict, selftest_kit, viewer
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
_MARK_SECTION = "<section id=" + '"conflict">'      # 冲突段开标签（① / ③ / ⑤ / ⑥）
_MARK_ENTRIES = "<section id=" + '"entries">'       # 条目段开标签（③ 的落位上界）
_MARK_FLOW = "<section id=" + '"flow">'             # 流程段开标签（③ 的落位下界）
_MARK_OVERVIEW = "<section id=" + '"overview">'
_CONFLICT_KEY = "flow" + "_conflict"                # 流程层键名（③/④/⑤/⑥ 取值用）
_RENDER_ENTRY = "def" + " " + "_render" + "_conflict("   # 冲突渲染入口定义锚点（①；前缀同样分段拼接，见「自指防护」）

# 冲突段「只增段、不加 CSS」：解析段内 class 值，逐个核对已在 `_CSS` 中定义
_CLASS_RE = re.compile(r'class="([^"]+)"')
_LI_FILE = '<li class="kv">file  '
_LI_SHARED = '<li class="kv">shared '
_SUM_CID_RE = re.compile(r'<details><summary><span class="cid">([^<]*)</span>')
_SUM_KINDS_RE = re.compile(
    r'<details><summary>([^<]+) &lt;&gt; ([^<]+) <span class="muted">kinds ([^<]*)</span>'
)


# --- 夹具数据（本模块自己的三份；与其余自测同形，仅题头不同）----------------------------


_DESIGN = (
    "# 夹具设计文档（M35 自测专用）\n"
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
    "# 流程夹具（M35 自测专用）\n"
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
# 只含 C / D 的「无冲突计划」（⑤ 用）：两层判定均应 `clear`
_CLEAR_CHANGES = (
    ("C", "docs/guide.md", "c\n"),
    ("D", "docs/spec.md", "d\n"),
)

# ⑦ / ⑧ 32 个无需命令行参数的自测（`m2` / `m3` 需代码根，由 ⑧ 的边界先行校验覆盖）；条数为**实测**
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


def _conflict_segment(page: str) -> str:
    """截出冲突段正文（介于冲突段开标签与条目段开标签之间，供段内计数与顺序核对）。"""
    assert _MARK_SECTION in page, "页面里没有冲突段"
    return page.split(_MARK_SECTION, 1)[1].split(_MARK_ENTRIES, 1)[0]


# --- ① 断言 ------------------------------------------------------------------------


def test_without_plan_page_unchanged() -> None:
    """① 无 `--plan` 的回归：5 参 / 6 参（`None`）深比较相等；无冲突段；冲突段只用既有类名。"""
    with tempfile.TemporaryDirectory() as td:
        root, design, _flow_doc, _diffs = _fixture(
            Path(td), design_text=_DESIGN, flow_text=_FLOW, changes=_PLAN_CHANGES
        )

        five = viewer.analyze(str(root), str(design))
        six = viewer.analyze(str(root), str(design), None, None, None, None)
        assert five == six, "5 参与 6 参（plan_file=None）的分析文档应深比较相等"
        assert six["conflict"] is None, "未给 plan_file 时 doc 的冲突键应为 None"

        page = viewer.render_html(six)
        assert _MARK_SECTION not in page, "未给 --plan 时页面不得出现冲突段"
        # 「既有基线」等价物：把冲突键整体移除后再渲染，须与实渲染逐字节一致（该键对页面零影响）
        stripped = dict(six)
        stripped.pop("conflict")
        assert viewer.render_html(stripped) == page, "冲突键为 None 时对页面应零影响"
        assert page.index(_MARK_OVERVIEW) < page.index(_MARK_ENTRIES), "既有段序应保持"

        src = (PKG_DIR / "viewer.py").read_text(encoding="utf-8")
        assert src.count(_RENDER_ENTRY) == 1, "冲突渲染入口应在 viewer.py 恰 1 处（不得有第二份实现）"


def test_conflict_section_reuses_existing_css() -> None:
    """①（续）零新 CSS 的结构证据：冲突段用到的每个 class 都已在 `_CSS` 中定义。"""
    with tempfile.TemporaryDirectory() as td:
        td_p = Path(td)
        root, design, flow_doc, _diffs = _fixture(
            td_p, design_text=_DESIGN, flow_text=_FLOW, changes=_PLAN_CHANGES
        )
        plan = _write_plan(td_p, "plan.json", "P-1", ("A", "B", "C", "D"))
        doc = viewer.analyze(str(root), str(design), None, str(flow_doc), None, str(plan))
        segment = _conflict_segment(viewer.render_html(doc))

        used: set[str] = set()
        for m in _CLASS_RE.finditer(segment):
            used.update(m.group(1).split())
        assert used, "冲突段应至少用一个既有类名（否则该断言为空真）"
        for cls in sorted(used):
            assert re.search(r"\." + re.escape(cls) + r"\b", viewer._CSS), \
                f"冲突段用了未定义的类名 .{cls}——「_CSS 一行不加」被破坏"

        # 同理：判定配色若不走既有 ok / drift，就会需要新规则；这两条必须**仍然缺席**
        assert "verdict.conflict" not in viewer._CSS, "_CSS 新增了 verdict.conflict"
        assert "verdict.clear" not in viewer._CSS, "_CSS 新增了 verdict.clear"


# --- ② 断言 ------------------------------------------------------------------------


def test_conflict_source_identical() -> None:
    """② 来源一致（取自而非重算）：冲突键与 `conflict.analyze_plan` 直算结果深比较相等。"""
    with tempfile.TemporaryDirectory() as td:
        td_p = Path(td)
        root, design, flow_doc, _diffs = _fixture(
            td_p, design_text=_DESIGN, flow_text=_FLOW, changes=_PLAN_CHANGES
        )
        plan = _write_plan(td_p, "plan.json", "P-1", ("A", "B", "C", "D"))
        doc = viewer.analyze(str(root), str(design), None, str(flow_doc), None, str(plan))
        direct = conflict.analyze_plan(str(plan), str(root), str(design), str(flow_doc))
        assert doc["conflict"] == direct, "冲突段应原样取自 conflict.analyze_plan（不裁剪、不重算）"
        assert doc["conflict"] is not None and doc["flow"] is not None, \
            "同一份分析应同时含流程段与冲突段（两层并列，互不取代）"


# --- ③ 断言 ------------------------------------------------------------------------


def test_section_placement_and_counts() -> None:
    """③ 段落落位与计数一致：冲突段在流程段之后、条目段之前；三计数与文档逐一相等。"""
    with tempfile.TemporaryDirectory() as td:
        td_p = Path(td)
        root, design, flow_doc, _diffs = _fixture(
            td_p, design_text=_DESIGN, flow_text=_FLOW, changes=_PLAN_CHANGES
        )
        plan = _write_plan(td_p, "plan.json", "P-1", ("A", "B", "C", "D"))
        doc = viewer.analyze(str(root), str(design), None, str(flow_doc), None, str(plan))
        cd = doc["conflict"]
        page = viewer.render_html(doc)

        assert _MARK_SECTION in page, "给了 --plan 时页面应含冲突段"
        assert page.index(_MARK_FLOW) < page.index(_MARK_SECTION) < page.index(_MARK_ENTRIES), \
            "冲突段应位于流程段之后、条目段之前"

        segment = _conflict_segment(page)
        assert f"<li>改动数：{cd['changeset_count']}</li>" in segment, "改动数应与文档一致"
        assert f"<li>冲突对：{cd['conflict_count']}</li>" in segment, "冲突对计数应与文档一致"
        assert f"<li>流程层冲突对：{cd[_CONFLICT_KEY]['conflict_count']}</li>" in segment, \
            "流程层冲突对计数应与文档一致"
        assert f"<h2>分工计划冲突（计划 {cd['plan_id']}）</h2>" in segment, "标题应含计划名"


# --- ④ 断言 ------------------------------------------------------------------------


def test_two_layer_conflicts_rendered() -> None:
    """④ 两层冲突均呈现：shared file / entry 与 shared step / flow 同现，kinds 与文档一致。"""
    with tempfile.TemporaryDirectory() as td:
        td_p = Path(td)
        root, design, flow_doc, _diffs = _fixture(
            td_p, design_text=_DESIGN, flow_text=_FLOW, changes=_PLAN_CHANGES
        )
        plan = _write_plan(td_p, "plan.json", "P-1", ("A", "B", "C", "D"))
        doc = viewer.analyze(str(root), str(design), None, str(flow_doc), None, str(plan))
        cd = doc["conflict"]
        assert cd["conflict_count"] == 1, f"本夹具应恰有 1 个文件 / 条目层冲突对，实际 {cd['conflict_count']}"
        assert cd[_CONFLICT_KEY]["conflict_count"] == 1, \
            f"本夹具应恰有 1 个流程层冲突对，实际 {cd[_CONFLICT_KEY]['conflict_count']}"

        pair = cd["conflicts"][0]
        flow_pair = cd[_CONFLICT_KEY]["conflicts"][0]
        assert pair["kinds"] == ["file", "entry"], f"文件层 kinds 应为两类同现，实际 {pair['kinds']}"
        assert flow_pair["kinds"] == ["step", "flow"], f"流程层 kinds 应为两类同现，实际 {flow_pair['kinds']}"

        segment = _conflict_segment(viewer.render_html(doc))
        for path in pair["shared_files"]:
            assert f"shared file  {path}" in segment, f"页面缺共享文件行：{path}"
        for cid in pair["shared_entries"]:
            assert f"shared entry {cid}" in segment, f"页面缺共享条目行：{cid}"
        for step in flow_pair["shared_steps"]:
            assert f"shared step  {step['flow_id']}/{step['step_id']}" in segment, "页面缺共享步骤行"
        for fid in flow_pair["shared_flows"]:
            assert f"shared flow  {fid}" in segment, f"页面缺共享流程行：{fid}"
        assert f'kinds {",".join(pair["kinds"])}' in segment, "文件层 kinds 应与文档一致"
        assert f'kinds {",".join(flow_pair["kinds"])}' in segment, "流程层 kinds 应与文档一致"


# --- ⑤ 断言 ------------------------------------------------------------------------


def test_clear_plan_no_false_positive() -> None:
    """⑤ 不误报：无冲突计划 → 判定 clear、配色 ok、冲突对 0、流程层判定同为 clear。"""
    with tempfile.TemporaryDirectory() as td:
        td_p = Path(td)
        root, design, flow_doc, _diffs = _fixture(
            td_p, design_text=_DESIGN, flow_text=_FLOW, changes=_CLEAR_CHANGES
        )
        plan = _write_plan(td_p, "plan.json", None, ("C", "D"))
        doc = viewer.analyze(str(root), str(design), None, str(flow_doc), None, str(plan))
        cd = doc["conflict"]
        assert cd["verdict"] == "clear" and cd["conflict_count"] == 0, \
            f"无冲突计划的两层判定应为 clear / 0，实际 {cd['verdict']} / {cd['conflict_count']}"
        assert cd[_CONFLICT_KEY]["verdict"] == "clear", "流程层判定同样应为 clear"

        segment = _conflict_segment(viewer.render_html(doc))
        assert '判定：clear' in segment, "冲突段判定应为 clear"
        assert '<p class="verdict ok">' in segment, "clear 应复用既有 ok 配色类"
        assert '<li>冲突对：0</li>' in segment, "无冲突对应打印计数 0"
        assert '流程层判定：clear' in segment, "流程层判定应为 clear"
        assert 'class="verdict drift"' not in segment, "clear 计划不得出现 drift 配色"
        assert "（未命名）" in segment, "无名计划的标题应渲染为「（未命名）」"


# --- ⑥ 断言 ------------------------------------------------------------------------


def test_determinism_and_order_preserved() -> None:
    """⑥ 确定性 + 顺序保真：两次渲染逐字节一致；各清单顺序与文档逐条一致（不二次排序）。"""
    with tempfile.TemporaryDirectory() as td:
        td_p = Path(td)
        root, design, flow_doc, _diffs = _fixture(
            td_p, design_text=_DESIGN, flow_text=_FLOW, changes=_PLAN_CHANGES
        )
        plan = _write_plan(td_p, "plan.json", "P-1", ("A", "B", "C", "D"))
        doc = viewer.analyze(str(root), str(design), None, str(flow_doc), None, str(plan))
        cd = doc["conflict"]

        first = viewer.render_html(doc)
        second = viewer.render_html(doc)
        assert first == second, "同输入两次渲染应逐字节一致"
        assert viewer.render_html(viewer.analyze(
            str(root), str(design), None, str(flow_doc), None, str(plan)
        )) == first, "同一输入重新分析 + 渲染也应逐字节一致（确定性）"

        lines = _conflict_segment(first).splitlines()

        got_ids = _SUM_CID_RE.findall("\n".join(lines))
        want_ids = [s["id"] for s in cd["changesets"]] + [r["id"] for r in cd["flow_of_changesets"]]
        assert got_ids == want_ids, f"改动清单 / 流程层行的 id 顺序应与文档一致：{got_ids} vs {want_ids}"

        got_files = [ln[len(_LI_FILE):-len("</li>")] for ln in lines if ln.startswith(_LI_FILE)]
        want_files = [p for s in cd["changesets"] for p in s["changed_files"]]
        assert got_files == want_files, f"文件清单顺序应与文档一致：{got_files} vs {want_files}"

        got_kinds = _SUM_KINDS_RE.findall("\n".join(lines))
        want_kinds = (
            [(c["left"], c["right"], ",".join(c["kinds"])) for c in cd["conflicts"]]
            + [(c["left"], c["right"], ",".join(c["kinds"])) for c in cd[_CONFLICT_KEY]["conflicts"]]
        )
        assert got_kinds == want_kinds, f"冲突对与 kinds 顺序应与文档一致：{got_kinds} vs {want_kinds}"

        got_shared = [ln[len('<li class="kv">'):-len("</li>")] for ln in lines if ln.startswith(_LI_SHARED)]
        want_shared: list[str] = []
        for c in cd["conflicts"]:
            want_shared += [f"shared file  {p}" for p in c["shared_files"]]
            want_shared += [f"shared entry {i}" for i in c["shared_entries"]]
        for c in cd[_CONFLICT_KEY]["conflicts"]:
            want_shared += [f"shared step  {s['flow_id']}/{s['step_id']}" for s in c["shared_steps"]]
            want_shared += [f"shared flow  {f}" for f in c["shared_flows"]]
        assert got_shared == want_shared, f"共享集合顺序应与文档一致：{got_shared} vs {want_shared}"


# --- ⑦ 断言 ------------------------------------------------------------------------


def test_read_only() -> None:
    """⑦ 只读：分析 / 渲染 / CLI 全程夹具目录复合摘要不变（四处输入均未被写）。"""
    with tempfile.TemporaryDirectory() as td:
        td_p = Path(td)
        root, design, flow_doc, _diffs = _fixture(
            td_p, design_text=_DESIGN, flow_text=_FLOW, changes=_PLAN_CHANGES
        )
        plan = _write_plan(td_p, "plan.json", "P-1", ("A", "B", "C", "D"))
        before = _dir_digest(td_p)

        doc = viewer.analyze(str(root), str(design), None, str(flow_doc), None, str(plan))
        viewer.render_html(doc)
        rc, _out, err = _cli(
            "view", str(root), str(design), "--flow", str(flow_doc), "--plan", str(plan)
        )
        assert rc == 0, f"CLI 正常路径应退出码 0，实际 {rc}；stderr={err[-200:]!r}"
        assert _dir_digest(td_p) == before, "分析 / 渲染 / CLI 全程不得写夹具中的任何一个字节"


# --- ⑧ 断言 ------------------------------------------------------------------------


def test_cli_and_exit_codes() -> None:
    """⑧ CLI：正常路径退出码 0、stdout 与库输出逐字节一致、无 `\\r\\n`；两类用法错误 2；坏计划 1。"""
    with tempfile.TemporaryDirectory() as td:
        td_p = Path(td)
        root, design, flow_doc, _diffs = _fixture(
            td_p, design_text=_DESIGN, flow_text=_FLOW, changes=_PLAN_CHANGES
        )
        plan = _write_plan(td_p, "plan.json", "P-1", ("A", "B", "C", "D"))

        expected = viewer.render_html(
            viewer.analyze(str(root), str(design), None, str(flow_doc), None, str(plan))
        )
        rc, out, err = _cli(
            "view", str(root), str(design), "--flow", str(flow_doc), "--plan", str(plan)
        )
        assert rc == 0, f"normal 路径应退出码 0，实际 {rc}；stderr={err[-200:]!r}"
        assert out == expected.encode("utf-8"), "给了 --plan 时 stdout 应与库输出逐字节一致"
        assert b"\r\n" not in out, "stdout 不得含 CRLF（字节稳定写盘）"

        expected_no_plan = viewer.render_html(
            viewer.analyze(str(root), str(design), None, str(flow_doc), None, None)
        )
        rc, out, err = _cli("view", str(root), str(design), "--flow", str(flow_doc))
        assert rc == 0, f"未给 --plan 时应退出码 0，实际 {rc}；stderr={err[-200:]!r}"
        assert out == expected_no_plan.encode("utf-8"), \
            "未给 --plan 时 stdout 应与库输出逐字节一致（页面逐字节不变）"
        assert b"\r\n" not in out, "stdout 不得含 CRLF（字节稳定写盘）"

        rc, _out, _err = _cli("view", str(root), str(design), "--flow", str(flow_doc), "--plan")
        assert rc == 2, f"--plan 缺值应属用法错误（退出码 2），实际 {rc}"

        rc, _out, _err = _cli("view", str(root), str(design), "--plan", str(plan))
        assert rc == 2, f"--plan 缺 --flow 应属用法错误（退出码 2），实际 {rc}"

        bad = td_p / "bad.json"
        bad.write_bytes(b"{not json")
        rc, _out, _err = _cli(
            "view", str(root), str(design), "--flow", str(flow_doc), "--plan", str(bad)
        )
        assert rc == 1, f"坏计划应退出码 1（沿 ConflictError），实际 {rc}"


# --- ⑦ / ⑧ 32 个无需命令行参数的自测（`m2` / `m3` 需代码根，见 ⑧）；条数为**实测** ------------


def test_existing_selftests_regression() -> None:
    """⑦ 既有自测零修订：32 个无需参数的自测各按实测条数全绿（经共享 `assert_regression`）。"""
    if selftest_kit.in_regression():
        return
    assert_regression(_REGRESSION)


def test_full_regression_and_number_independence() -> None:
    """⑧ 全域回归 + 编号无关性：逆序逐模块跑同一批自测仍全绿（与 ⑦ 逐条一致）；需代码根者恰 m2/m3。"""
    if selftest_kit.in_regression():
        return
    number_independence_regression(_REGRESSION, _ARGV_MARK, _ARG_EXEMPT)


def main() -> int:
    tests = (
        test_without_plan_page_unchanged,
        test_conflict_section_reuses_existing_css,
        test_conflict_source_identical,
        test_section_placement_and_counts,
        test_two_layer_conflicts_rendered,
        test_clear_plan_no_false_positive,
        test_determinism_and_order_preserved,
        test_read_only,
        test_cli_and_exit_codes,
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
