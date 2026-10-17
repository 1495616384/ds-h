"""M7 自测：把「并发改动冲突检测」的验收点写成可执行断言。

核心思路：**夹具临时自建**——每次测试在临时目录里现造一个最小代码根 + 设计文档 + 若干 diff，
使本自测**不依赖**任何归档基线副本、不依赖网络；本文件与 `conflict.py` 同样不含冻结链
目录名字面量（由 M0 自测第三条校验）。

夹具的「撞车」设计（决定各测试的期望值）：
    W-1 改 `src/app/core.py` → 命中条目 {CV-001, CV-002}
    W-2 改 `src/app/api.py`  → 命中条目 {CV-002, DI-001}
    W-3 改 `src/app/core.py` → 命中条目 {CV-001, CV-002}（与 W-1 同文件）
    W-4 改 `src/app/other.py`→ 命中条目 {PI-001}
    W-E 空 diff              → 无文件、无条目
    CV-002 刻意带**两条锚**（core.py 与 api.py）：使 W-1/W-2 **文件不重叠却命中同一条目**，
    用以把「条目级冲突」与「文件级冲突」分开断言。

覆盖：
    ① 文件冲突：W-1/W-3 同文件 → `conflict`，kinds=[file, entry]、共享文件与共享条目均排序；
    ② 跨文件条目冲突：W-1/W-2 文件不重叠但共享 CV-002 → `conflict`，kinds=[entry]、shared_files 为空；
    ③ 无冲突：W-2/W-4 文件与条目皆不重叠 → `clear`、conflict_count 0；
    ④ 三份部分重叠：W-1/W-2/W-3 → 冲突对恰为 (W-1,W-2)/(W-1,W-3)/(W-2,W-3)，无遗漏无重复；
    ⑤ 单份改动：内部不可能冲突 → `clear`；
    ⑥ 空 diff 的改动：不产文件/条目不产生冲突；
    ⑦ 书写顺序无关：计划里乱序书写，输出仍按 id 升序规范化（与 ④ 逐字节一致）；
    ⑧ 确定性：同输入两次分析逐字节一致；
    ⑨ 全程只读：夹具文件复合摘要前后不变；
    ⑩ CLI `conflict` JSON stdout 与库输出逐字节一致（含无 `\\r\\n` 翻译）、退出码 0；
    ⑪ CLI `conflict --text` 同理；
    ⑫ 非法输入：JSON 坏 / id 重复 / changesets 空 / diff 不存在 → 退出码 1；参数不足 → 退出码 2。

沿用 M0–M6 约定：不用 `subprocess` 管道，改临时文件重定向（本机沙箱禁建管道）。
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from . import conflict
from .selftest_kit import PKG_DIR, cli as _cli, dir_digest as _tree_digest


_DESIGN = (
    "# 夹具设计文档（M7 自测专用）\n"
    "\n"
    "### CV-001 — 精确锚 core.py\n"
    "- type: 数据完整性\n"
    "- invariant: 示例不变量\n"
    "- change_control: free\n"
    "- severity: normal\n"
    "- evidence:\n"
    "  - src/app/core.py\n"
    "- action_policy: 警告\n"
    "\n"
    "### CV-002 — 双锚（跨文件同一条目）\n"
    "- type: 公共接口\n"
    "- invariant: 示例不变量\n"
    "- change_control: free\n"
    "- severity: normal\n"
    "- evidence:\n"
    "  - src/app/core.py\n"
    "  - src/app/api.py\n"
    "- action_policy: 警告\n"
    "\n"
    "### DI-001 — 精确锚 api.py\n"
    "- type: 数据完整性\n"
    "- invariant: 示例不变量\n"
    "- change_control: free\n"
    "- severity: normal\n"
    "- evidence:\n"
    "  - src/app/api.py\n"
    "- action_policy: 警告\n"
    "\n"
    "### PI-001 — 精确锚 other.py\n"
    "- type: 公共接口\n"
    "- invariant: 示例不变量\n"
    "- change_control: free\n"
    "- severity: normal\n"
    "- evidence:\n"
    "  - src/app/other.py\n"
    "- action_policy: 警告\n"
)


def _diff(path: str) -> str:
    """造一份最小统一 diff：只声明「改了这个文件」，正文不参与冲突判定。"""
    return (
        f"diff --git a/{path} b/{path}\n"
        f"--- a/{path}\n"
        f"+++ b/{path}\n"
        "@@ -1 +1 @@\n"
        "-old\n"
        "+new\n"
    )


def _make_fixture(td: Path) -> tuple[Path, Path]:
    """建最小夹具（代码根 + 设计文档 + 5 份 diff），返回 (root, design)。

    代码根只求「有 .py 可被静态解析」；设计文档只求「锚点落在可被 diff 命中的文件上」。
    """
    app = td / "root" / "src" / "app"
    app.mkdir(parents=True)
    (app / "__init__.py").write_text("", encoding="utf-8")
    (app / "core.py").write_text("X = 1\n", encoding="utf-8")
    (app / "api.py").write_text("from app.core import X\n\nY = 2\n", encoding="utf-8")
    (app / "other.py").write_text("Z = 3\n", encoding="utf-8")

    design = td / "design.md"
    design.write_text(_DESIGN, encoding="utf-8")

    (td / "w1.diff").write_text(_diff("src/app/core.py"), encoding="utf-8")
    (td / "w2.diff").write_text(_diff("src/app/api.py"), encoding="utf-8")
    (td / "w3.diff").write_text(_diff("src/app/core.py"), encoding="utf-8")
    (td / "w4.diff").write_text(_diff("src/app/other.py"), encoding="utf-8")
    (td / "wempty.diff").write_text("", encoding="utf-8")
    return td / "root", design


def _plan(td: Path, name: str, changesets: list[dict]) -> Path:
    """写一份分工计划；diff 用**相对路径**（相对计划文件所在目录）。"""
    p = td / name
    p.write_text(
        json.dumps({"plan_id": "P-001", "changesets": changesets}, ensure_ascii=False),
        encoding="utf-8",
    )
    return p


_THREE_WAY = [
    {"id": "W-1", "diff": "w1.diff"},
    {"id": "W-2", "diff": "w2.diff"},
    {"id": "W-3", "diff": "w3.diff"},
]


def test_file_conflict() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design = _make_fixture(td)
        plan = _plan(td, "p.json", [{"id": "W-1", "diff": "w1.diff"}, {"id": "W-3", "diff": "w3.diff"}])
        doc = conflict.analyze_plan(plan, root, design)
    assert doc["verdict"] == conflict.VERDICT_CONFLICT, doc["verdict"]
    assert doc["conflict_count"] == 1, f"应恰有 1 个冲突对，实际 {doc['conflict_count']}"
    c = doc["conflicts"][0]
    assert (c["left"], c["right"]) == ("W-1", "W-3"), "冲突对应按 id 升序"
    assert c["kinds"] == [conflict.FILE_KIND, conflict.ENTRY_KIND], f"kinds 应为 [file, entry]：{c['kinds']}"
    assert c["shared_files"] == ["src/app/core.py"], c["shared_files"]
    assert c["shared_entries"] == ["CV-001", "CV-002"], c["shared_entries"]


def test_entry_only_conflict_across_files() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design = _make_fixture(td)
        plan = _plan(td, "p.json", [{"id": "W-1", "diff": "w1.diff"}, {"id": "W-2", "diff": "w2.diff"}])
        doc = conflict.analyze_plan(plan, root, design)
    c = doc["conflicts"][0]
    assert doc["verdict"] == conflict.VERDICT_CONFLICT and doc["conflict_count"] == 1, doc["verdict"]
    assert c["kinds"] == [conflict.ENTRY_KIND], f"文件不重叠时 kinds 应仅 [entry]：{c['kinds']}"
    assert c["shared_files"] == [], "W-1/W-2 改的是不同文件，shared_files 必须为空"
    assert c["shared_entries"] == ["CV-002"], "应恰好共享 CV-002（其两条锚分别落在两个文件上）"


def test_clear_when_disjoint() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design = _make_fixture(td)
        plan = _plan(td, "p.json", [{"id": "W-2", "diff": "w2.diff"}, {"id": "W-4", "diff": "w4.diff"}])
        doc = conflict.analyze_plan(plan, root, design)
    assert doc["verdict"] == conflict.VERDICT_CLEAR, doc["verdict"]
    assert doc["conflict_count"] == 0 and doc["conflicts"] == [], "无交集的改动不得被判冲突"
    summaries = {s["id"]: s for s in doc["changesets"]}
    assert summaries["W-2"]["changed_files"] == ["src/app/api.py"], summaries["W-2"]
    assert summaries["W-2"]["entries"] == ["CV-002", "DI-001"], summaries["W-2"]
    assert summaries["W-4"]["entries"] == ["PI-001"], summaries["W-4"]


def test_three_way_partial_overlap() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design = _make_fixture(td)
        plan = _plan(td, "p.json", _THREE_WAY)
        doc = conflict.analyze_plan(plan, root, design)
    assert doc["conflict_count"] == 3, f"三份部分重叠应产出 3 个冲突对，实际 {doc['conflict_count']}"
    pairs = [(c["left"], c["right"]) for c in doc["conflicts"]]
    assert pairs == [("W-1", "W-2"), ("W-1", "W-3"), ("W-2", "W-3")], f"冲突对集合错误：{pairs}"
    kinds = {c["left"] + c["right"]: c["kinds"] for c in doc["conflicts"]}
    assert kinds == {
        "W-1W-2": [conflict.ENTRY_KIND],
        "W-1W-3": [conflict.FILE_KIND, conflict.ENTRY_KIND],
        "W-2W-3": [conflict.ENTRY_KIND],
    }, kinds


def test_single_changeset_is_clear() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design = _make_fixture(td)
        plan = _plan(td, "p.json", [{"id": "W-1", "diff": "w1.diff"}])
        doc = conflict.analyze_plan(plan, root, design)
    assert doc["changeset_count"] == 1 and doc["conflict_count"] == 0, doc
    assert doc["verdict"] == conflict.VERDICT_CLEAR, "单独一份改动不可能与谁冲突"


def test_empty_diff_makes_no_conflict() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design = _make_fixture(td)
        plan = _plan(td, "p.json", [{"id": "W-1", "diff": "w1.diff"}, {"id": "W-E", "diff": "wempty.diff"}])
        doc = conflict.analyze_plan(plan, root, design)
    assert doc["verdict"] == conflict.VERDICT_CLEAR and doc["conflict_count"] == 0, doc
    summaries = {s["id"]: s for s in doc["changesets"]}
    assert summaries["W-E"]["changed_file_count"] == 0 and summaries["W-E"]["changed_files"] == [], summaries["W-E"]
    assert summaries["W-E"]["entry_count"] == 0 and summaries["W-E"]["entries"] == [], summaries["W-E"]


def test_plan_order_independent() -> None:
    """计划里乱序书写，输出仍按 id 升序规范化——与 `test_three_way_partial_overlap` 同形。"""
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design = _make_fixture(td)
        shuffled = _plan(td, "shuffled.json", [_THREE_WAY[2], _THREE_WAY[0], _THREE_WAY[1]])
        doc = conflict.analyze_plan(shuffled, root, design)
    assert [s["id"] for s in doc["changesets"]] == ["W-1", "W-2", "W-3"], "改动应按 id 升序规范化"
    pairs = [(c["left"], c["right"]) for c in doc["conflicts"]]
    assert pairs == [("W-1", "W-2"), ("W-1", "W-3"), ("W-2", "W-3")], f"乱序输入改变了冲突对：{pairs}"


def test_determinism() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design = _make_fixture(td)
        plan = _plan(td, "p.json", _THREE_WAY)
        first = conflict.to_json(conflict.analyze_plan(plan, root, design))
        second = conflict.to_json(conflict.analyze_plan(plan, root, design))
    assert first == second, "同输入两次分析应完全一致"


def test_analysis_is_readonly() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design = _make_fixture(td)
        plan = _plan(td, "p.json", _THREE_WAY)
        before = _tree_digest(td)
        conflict.analyze_plan(plan, root, design)
        after = _tree_digest(td)
    assert after == before, "分析过程改动了夹具内容（应全程只读）"


def test_cli_json_bytes() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design = _make_fixture(td)
        plan = _plan(td, "p.json", _THREE_WAY)
        code, out, err = _cli("conflict", str(plan), str(root), str(design))
        expected = conflict.analyze_plan(plan, root, design)
    assert code == 0, f"退出码应为 0，实际 {code}；stderr={err!r}"
    assert out == conflict.to_json(expected).encode("utf-8"), "CLI JSON stdout 与库输出非逐字节一致"
    assert b"\r\n" not in out, "stdout 出现 \\r\\n 翻译，说明未走字节流输出"


def test_cli_text_bytes() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design = _make_fixture(td)
        plan = _plan(td, "p.json", _THREE_WAY)
        code, out, err = _cli("conflict", str(plan), str(root), str(design), "--text")
        expected = conflict.analyze_plan(plan, root, design)
    assert code == 0, f"文本模式应退出 0，实际 {code}；stderr={err!r}"
    assert out == conflict.render_text(expected).encode("utf-8"), "CLI --text stdout 与库输出不一致"
    assert b"\r\n" not in out, "stdout 出现 \\r\\n 翻译"
    assert b"verdict: conflict\n" in out, "三份部分重叠的文本判定应为 conflict"


def test_cli_rejects_bad_inputs() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design = _make_fixture(td)

        bad = td / "bad.json"
        bad.write_text("这不是 JSON\n", encoding="utf-8")
        code, out, err = _cli("conflict", str(bad), str(root), str(design))
        assert code == 1, f"计划 JSON 坏应退出 1，实际 {code}"
        assert err.strip() and not out, "应仅向 stderr 报错、不写 stdout"

        dup = _plan(td, "dup.json", [{"id": "W", "diff": "w1.diff"}, {"id": "W", "diff": "w2.diff"}])
        code, out, err = _cli("conflict", str(dup), str(root), str(design))
        assert code == 1, f"id 重复应退出 1，实际 {code}"
        assert err.strip() and not out, "id 重复应仅向 stderr 报错"

        empty = _plan(td, "empty.json", [])
        code, out, err = _cli("conflict", str(empty), str(root), str(design))
        assert code == 1, f"changesets 为空应退出 1，实际 {code}"
        assert err.strip() and not out, "空 changesets 应仅向 stderr 报错"

        missing = _plan(td, "missing.json", [{"id": "W", "diff": "no-such.diff"}])
        code, out, err = _cli("conflict", str(missing), str(root), str(design))
        assert code == 1, f"diff 不存在应退出 1，实际 {code}"
        assert err.strip() and not out, "diff 缺失应仅向 stderr 报错"

        code, out, err = _cli("conflict", str(dup), str(root))
        assert code == 2, f"参数不足应退出 2（用法错误），实际 {code}"
        assert err.strip() and not out, "用法错误应仅向 stderr 报错"


def main() -> int:
    tests = (
        test_file_conflict,
        test_entry_only_conflict_across_files,
        test_clear_when_disjoint,
        test_three_way_partial_overlap,
        test_single_changeset_is_clear,
        test_empty_diff_makes_no_conflict,
        test_plan_order_independent,
        test_determinism,
        test_analysis_is_readonly,
        test_cli_json_bytes,
        test_cli_text_bytes,
        test_cli_rejects_bad_inputs,
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
