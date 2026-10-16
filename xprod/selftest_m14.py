"""M14 自测：把「流程层并发冲突检测」的验收点写成可执行断言。

核心思路：**夹具临时自建**——每次测试在临时目录里现造一个最小代码根 + 设计文档 + 流程文档 +
一份分工计划（5 份改动，每份各自一个 diff），使本自测**不依赖**任何归档基线副本、不依赖网络；
本文件与 `conflict.py` 同样不含冻结链目录名字面量（由 M0 自测第三条校验）。

主夹具（决定各测试的期望值）：
    代码根：src/app/{__init__,api,core,notify,report,other}.py、docs/{guide,spec}.md
    设计文档：OK-001 @ src/app/api.py、OK-002 @ src/app/core.py、
              OK-003 @ docs/（前缀锚）、OK-004 @ just-a-token（无斜杠 → unanchored）
    流程文档：
      FL-001「下单到发货」：S1@api.py → S2@core.py → S3@notify.py → S4（**无锚**）
      FL-002「日报汇总」：R1@report.py → R2@archive.py（**文件不存在 → 断链**）
    分工计划（id 升序）：
      A 改 api.py、B 改 core.py、C 改 notify.py、D 改 other.py、E **再改一次 core.py**
    各改动流程面：
      A: direct [S1]、affected [S1,S2,S3,S4]、flows [FL-001]
      B: direct [S2]、affected [S2,S3,S4]  、flows [FL-001]（E 同 B）
      C: direct [S3]、affected [S3,S4]     、flows [FL-001]
      D: direct []、affected []           、flows []
    期望冲突（6 对，按 (left,right) 字典序）：
      (A,B) flow；(A,C) flow；(A,E) flow；(B,C) flow；
      (B,E) **step,flow**（共享 S2）；(C,E) flow

覆盖：
    ① 无 `--flow` 回归：文档**不含**任何流程层键，文本与 M7 同形（不出现流程层行）；
    ② 流程面同源：`flow_of_changesets` 逐条与**逐改动** `flow.analyze` 的 `impact` 相等（取用而非重算）；
    ③ `step` 冲突：共享直接命中步骤被标出，`kinds` 含 `step`；
    ④ `flow` 冲突：仅波及同一流程（无共享步骤）时 `kinds` **只**含 `flow`；
    ⑤ 不误报：流程面无关的改动对**不**进冲突列表；
    ⑥ 断链不参与：把含断链的 FL-002 整条移除后，冲突列表与各改动流程面**完全不变**；
    ⑦ 无锚不参与：无证据锚的步骤**不**出现在任何 `direct_steps` / `shared_steps` 里；
    ⑧ 确定性：同输入两次 `to_json` / `render_text` 逐字节一致，且冲突对与共享集合均排序；
    ⑨ 只读：`analyze_plan` 前后夹具目录复合摘要不变；
    ⑩ CLI：`conflict ... --flow` 的 stdout 与库输出逐字节一致、无 `\\r\\n`、退出码 0；
        `--flow` 缺值 → 2；坏流程文档 → 1。
    另附：完整冲突列表断言（锁定判定结果本身）。

沿用 M0–M13 约定：不用 `subprocess` 管道，改临时文件重定向（本机沙箱禁建管道）。
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from . import conflict, flow
from .selftest_kit import cli as _cli, dir_digest as _tree_digest

PKG_DIR = Path(__file__).resolve().parent

_DESIGN = (
    "# 夹具设计文档（M14 自测专用）\n"
    "\n"
    "### OK-001 — 精确锚 api.py\n"
    "- type: 公共接口\n"
    "- invariant: 示例不变量\n"
    "- change_control: free\n"
    "- severity: normal\n"
    "- evidence:\n"
    "  - src/app/api.py\n"
    "- action_policy: 警告\n"
    "\n"
    "### OK-002 — 精确锚 core.py\n"
    "- type: 数据完整性\n"
    "- invariant: 示例不变量\n"
    "- change_control: free\n"
    "- severity: normal\n"
    "- evidence:\n"
    "  - src/app/core.py\n"
    "- action_policy: 警告\n"
    "\n"
    "### OK-003 — 前缀锚 docs/\n"
    "- type: 公共接口\n"
    "- invariant: 示例不变量\n"
    "- change_control: free\n"
    "- severity: normal\n"
    "- evidence:\n"
    "  - docs/\n"
    "- action_policy: 警告\n"
    "\n"
    "### OK-004 — 无斜杠锚（unanchored）\n"
    "- type: 公共接口\n"
    "- invariant: 示例不变量\n"
    "- change_control: free\n"
    "- severity: normal\n"
    "- evidence:\n"
    "  - just-a-token\n"
    "- action_policy: 警告\n"
)

_FLOW_WITH_DANGLING = (
    "# 流程夹具（M14 自测专用）\n"
    "\n"
    "## FL-001 — 下单到发货\n"
    "\n"
    "- step:\n"
    "  - S1: 校验库存 @ src/app/api.py\n"
    "  - S2: 扣减库存 @ src/app/core.py\n"
    "  - S3: 发货通知 @ src/app/notify.py\n"
    "  - S4: 人工复核\n"
    "- edge:\n"
    "  - S1 -> S2\n"
    "  - S2 -> S3\n"
    "  - S3 -> S4\n"
    "\n"
    "## FL-002 — 日报汇总\n"
    "\n"
    "- step:\n"
    "  - R1: 汇总 @ src/app/report.py\n"
    "  - R2: 归档 @ src/app/archive.py\n"
    "- edge:\n"
    "  - R1 -> R2\n"
)

# 与上面**只差**「整条 FL-002（含断链步骤 R2）被移除」——用于证明断链不参与任何判定
_FLOW_NO_DANGLING = (
    "# 流程夹具（M14 自测专用）\n"
    "\n"
    "## FL-001 — 下单到发货\n"
    "\n"
    "- step:\n"
    "  - S1: 校验库存 @ src/app/api.py\n"
    "  - S2: 扣减库存 @ src/app/core.py\n"
    "  - S3: 发货通知 @ src/app/notify.py\n"
    "  - S4: 人工复核\n"
    "- edge:\n"
    "  - S1 -> S2\n"
    "  - S2 -> S3\n"
    "  - S3 -> S4\n"
)


def _diff(path: str, old: str, new: str) -> str:
    """造一份只改一个文件的统一 diff（与 M3 解析口径一致）。"""
    return (
        f"diff --git a/{path} b/{path}\n"
        f"--- a/{path}\n"
        f"+++ b/{path}\n"
        "@@ -1 +1 @@\n"
        f"-{old}\n"
        f"+{new}\n"
    )


# id → (变更文件, 该文件新内容)
_CHANGES = (
    ("A", "src/app/api.py", "from app.core import X\nA = 1\n"),
    ("B", "src/app/core.py", "X = 2\n"),
    ("C", "src/app/notify.py", "N = 2\n"),
    ("D", "src/app/other.py", "Z = 4\n"),
    ("E", "src/app/core.py", "X = 3\n"),
)

# 期望的流程层冲突列表（锁定判定结果本身；按 (left, right) 字典序）
_EXPECTED_CONFLICTS = [
    {"left": "A", "right": "B", "kinds": ["flow"], "shared_steps": [], "shared_flows": ["FL-001"]},
    {"left": "A", "right": "C", "kinds": ["flow"], "shared_steps": [], "shared_flows": ["FL-001"]},
    {"left": "A", "right": "E", "kinds": ["flow"], "shared_steps": [], "shared_flows": ["FL-001"]},
    {"left": "B", "right": "C", "kinds": ["flow"], "shared_steps": [], "shared_flows": ["FL-001"]},
    {
        "left": "B",
        "right": "E",
        "kinds": ["step", "flow"],
        "shared_steps": [{"flow_id": "FL-001", "step_id": "S2"}],
        "shared_flows": ["FL-001"],
    },
    {"left": "C", "right": "E", "kinds": ["flow"], "shared_steps": [], "shared_flows": ["FL-001"]},
]


def _make_root(td: Path) -> Path:
    """建最小代码根（层层 `__init__.py`，使 M3 影响分析器有依赖图节点可用）。"""
    root = td / "root"
    (root / "src" / "app").mkdir(parents=True)
    (root / "docs").mkdir(parents=True)
    (root / "src" / "app" / "__init__.py").write_text("", encoding="utf-8")
    (root / "src" / "app" / "api.py").write_text("from app.core import X\nA = 0\n", encoding="utf-8")
    (root / "src" / "app" / "core.py").write_text("X = 1\n", encoding="utf-8")
    (root / "src" / "app" / "notify.py").write_text("N = 1\n", encoding="utf-8")
    (root / "src" / "app" / "report.py").write_text("R = 1\n", encoding="utf-8")
    (root / "src" / "app" / "other.py").write_text("Z = 3\n", encoding="utf-8")
    (root / "docs" / "guide.md").write_text("# 指南\n", encoding="utf-8")
    (root / "docs" / "spec.md").write_text("# 规格\n", encoding="utf-8")
    return root


def _fixture(td: Path) -> tuple[Path, Path, Path, Path]:
    """建全套夹具，返回（代码根, 设计文档, 流程文档, 分工计划）。"""
    root = _make_root(td)
    design = td / "design.md"
    design.write_text(_DESIGN, encoding="utf-8")
    flow_doc = td / "flow.md"
    flow_doc.write_text(_FLOW_WITH_DANGLING, encoding="utf-8")

    changesets = []
    for cid, path, new in _CHANGES:
        diff_path = td / f"{cid}.diff"
        diff_path.write_text(_diff(path, "old\n", new), encoding="utf-8")
        changesets.append({"id": cid, "diff": diff_path.name})  # 相对计划文件所在目录
    plan = td / "plan.json"
    plan.write_text(
        json.dumps({"plan_id": "M14 夹具", "changesets": changesets}, ensure_ascii=False),
        encoding="utf-8",
    )
    return root, design, flow_doc, plan


def test_no_flow_leaves_m7_shape_unchanged() -> None:
    """① 无 `--flow`：不出现任何流程层键，文本仍是 M7 同形。"""
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design, _flow_doc, plan = _fixture(td)
        doc = conflict.analyze_plan(plan, root, design)
        explicit_none = conflict.analyze_plan(plan, root, design, None)
        text = conflict.render_text(doc)
    assert "flow_conflict" not in doc and "flow_of_changesets" not in doc, "未给 --flow 却出现流程层键"
    assert doc == explicit_none, "缺省形参与显式 None 应产出同一文档"
    assert "flow verdict" not in text and "flow conflicts" not in text, "未给 --flow 却出现流程层文本"
    assert text.endswith(conflict._CLEAR_NOTE + "\n"), text[-80:]


def test_flow_layer_matches_flow_analyze() -> None:
    """② 流程面同源：逐条与**逐改动** `flow.analyze` 的 `impact` 相等（取用而非重算）。"""
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design, flow_doc, plan = _fixture(td)
        doc = conflict.analyze_plan(plan, root, design, flow_doc)
        loaded = conflict.load_plan(plan)
        per_change = {
            change["id"]: flow.analyze(flow_doc, root, change["diff"])["impact"]
            for change in loaded["changesets"]
        }
    rows = {r["id"]: r for r in doc["flow_of_changesets"]}
    assert list(rows) == [c["id"] for c in loaded["changesets"]], "流程面行应按 id 升序"
    for cid, impact in per_change.items():
        assert rows[cid]["direct_steps"] == impact["direct_steps"], f"{cid} 直接命中步骤与 flow 分叉"
        assert rows[cid]["affected_steps"] == impact["affected_steps"], f"{cid} 受影响步骤与 flow 分叉"


def test_step_conflict_reported() -> None:
    """③ `step` 冲突：两份改动**直接命中同一步骤**时须报出，且 `kinds` 含 `step`。"""
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design, flow_doc, plan = _fixture(td)
        doc = conflict.analyze_plan(plan, root, design, flow_doc)
    pair = next(c for c in doc["flow_conflict"]["conflicts"] if (c["left"], c["right"]) == ("B", "E"))
    assert "step" in pair["kinds"], pair
    assert pair["shared_steps"] == [{"flow_id": "FL-001", "step_id": "S2"}], pair


def test_flow_only_conflict_reported() -> None:
    """④ `flow` 冲突：仅**波及同一流程**而无共享步骤时，`kinds` 只含 `flow`。"""
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design, flow_doc, plan = _fixture(td)
        doc = conflict.analyze_plan(plan, root, design, flow_doc)
    pair = next(c for c in doc["flow_conflict"]["conflicts"] if (c["left"], c["right"]) == ("A", "B"))
    assert pair["kinds"] == ["flow"], pair
    assert pair["shared_steps"] == [], pair
    assert pair["shared_flows"] == ["FL-001"], pair


def test_conflict_list_is_exact() -> None:
    """完整冲突列表：锁定判定结果本身（顺序、类别、共享集合）。"""
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design, flow_doc, plan = _fixture(td)
        doc = conflict.analyze_plan(plan, root, design, flow_doc)
    assert doc["flow_conflict"]["conflicts"] == _EXPECTED_CONFLICTS, doc["flow_conflict"]["conflicts"]
    assert doc["flow_conflict"]["conflict_count"] == len(_EXPECTED_CONFLICTS)
    assert doc["flow_conflict"]["verdict"] == conflict.VERDICT_CONFLICT
    # 流程面无关的改动（D 只改 other.py）不与任何改动构成冲突对
    assert all("D" not in (c["left"], c["right"]) for c in doc["flow_conflict"]["conflicts"]), "误报"


def test_dangling_is_not_a_criterion() -> None:
    """⑥ 断链不参与：整条含断链步骤的流程移除后，冲突与各改动流程面**完全不变**。"""
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design, flow_doc, plan = _fixture(td)
        with_dangling = conflict.analyze_plan(plan, root, design, flow_doc)
        no_dangling_doc = td / "flow-nodead.md"
        no_dangling_doc.write_text(_FLOW_NO_DANGLING, encoding="utf-8")
        without = conflict.analyze_plan(plan, root, design, no_dangling_doc)
    assert without["flow_conflict"]["conflicts"] == with_dangling["flow_conflict"]["conflicts"], "断链影响了判定"
    assert without["flow_of_changesets"] == with_dangling["flow_of_changesets"], "断链影响了流程面"
    # 断链步骤 R2 不得出现在任何冲突记录里（它既没进 direct，也没进 affected）
    for c in with_dangling["flow_conflict"]["conflicts"]:
        assert all(s["step_id"] != "R2" for s in c["shared_steps"]), c


def test_unanchored_not_a_criterion() -> None:
    """⑦ 无锚不参与：无证据锚的步骤（S4）**不**出现在任何 `direct_steps` / `shared_steps` 里。"""
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design, flow_doc, plan = _fixture(td)
        doc = conflict.analyze_plan(plan, root, design, flow_doc)
    for row in doc["flow_of_changesets"]:
        assert all(d["step_id"] != "S4" for d in row["direct_steps"]), f"{row['id']} 的无锚步骤被算成直接命中"
    for c in doc["flow_conflict"]["conflicts"]:
        assert all(s["step_id"] != "S4" for s in c["shared_steps"]), c


def test_determinism() -> None:
    """⑧ 确定性：同输入两次输出逐字节一致。"""
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design, flow_doc, plan = _fixture(td)
        first = conflict.analyze_plan(plan, root, design, flow_doc)
        second = conflict.analyze_plan(plan, root, design, flow_doc)
        j1, j2 = conflict.to_json(first), conflict.to_json(second)
        t1, t2 = conflict.render_text(first), conflict.render_text(second)
    assert j1 == j2, "同输入两次 JSON 应完全一致"
    assert t1 == t2, "同输入两次文本应完全一致"
    assert "flow verdict: conflict\n" in t1, "文本流程层判定应为 conflict"


def test_analysis_is_readonly() -> None:
    """⑨ 只读：分析前后夹具目录复合摘要不变。"""
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design, flow_doc, plan = _fixture(td)
        before = _tree_digest(td)
        conflict.analyze_plan(plan, root, design, flow_doc)
        after = _tree_digest(td)
    assert after == before, "分析过程改动了夹具内容（应全程只读）"


def test_cli_bytes_and_bad_inputs() -> None:
    """⑩ CLI：`--flow` 的 stdout 逐字节一致；缺值 → 2；坏流程文档 → 1。"""
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design, flow_doc, plan = _fixture(td)
        expected = conflict.analyze_plan(plan, root, design, flow_doc)

        code, out, err = _cli("conflict", str(plan), str(root), str(design), "--flow", str(flow_doc))
        assert code == 0, f"退出码应为 0，实际 {code}；stderr={err!r}"
        assert out == conflict.to_json(expected).encode("utf-8"), "CLI JSON stdout 与库输出非逐字节一致"
        assert b"\r\n" not in out, "stdout 出现 \\r\\n 翻译，说明未走字节流输出"

        code, out, err = _cli(
            "conflict", str(plan), str(root), str(design), "--flow", str(flow_doc), "--text"
        )
        assert code == 0, f"文本模式应退出 0，实际 {code}；stderr={err!r}"
        assert out == conflict.render_text(expected).encode("utf-8"), "CLI --text stdout 与库输出不一致"
        assert b"flow conflicts (6):\n" in out, "主夹具文本应有 6 个流程层冲突"

        code, out, err = _cli("conflict", str(plan), str(root), str(design), "--flow")
        assert code == 2, f"--flow 缺值应退出 2（用法错误），实际 {code}"
        assert err.strip() and not out, "--flow 缺值应仅向 stderr 报错"

        bad_flow = td / "bad-flow.md"
        bad_flow.write_text("这不是合法流程文档\n", encoding="utf-8")
        code, out, err = _cli("conflict", str(plan), str(root), str(design), "--flow", str(bad_flow))
        assert code == 1, f"坏流程文档应退出 1，实际 {code}"
        assert err.strip() and not out, "坏流程文档应仅向 stderr 报错"


def main() -> int:
    tests = (
        test_no_flow_leaves_m7_shape_unchanged,
        test_flow_layer_matches_flow_analyze,
        test_step_conflict_reported,
        test_flow_only_conflict_reported,
        test_conflict_list_is_exact,
        test_dangling_is_not_a_criterion,
        test_unanchored_not_a_criterion,
        test_determinism,
        test_analysis_is_readonly,
        test_cli_bytes_and_bad_inputs,
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
