"""M13 自测：把「流程影响面接入可视面」的验收点写成可执行断言。

核心思路：**夹具临时自建**——每次测试在临时目录里现造一个最小代码根 + 条目设计文档 +
流程文档 +（可选）统一 diff，使本自测**不依赖**任何归档基线副本、不依赖网络；
本文件与 `viewer.py` 同样不含冻结链目录名字面量（由 M0 自测第三条校验）。

主夹具（决定各测试的期望值）：
    代码根（8 文件）：src/app/__init__.py、core.py、api.py、notify.py、report.py、other.py、
                     docs/guide.md、docs/spec.md
    条目设计文档：OK-001 精确锚 src/app/core.py（使 drift 判定为 ok）
    流程文档：
      FL-001「下单到发货」：S1 校验库存@src/app/api.py、S2 扣减库存@src/app/core.py、
            S3 发货通知@src/app/notify.py、S4 人工复核（无证据 → unanchored）；
            边 S1->S2、S2->S3、S3->S4
      FL-002「日报汇总」：R1 汇总@src/app/report.py、R2 归档@src/app/archive.py（文件不存在 → dangling）；
            边 R1->R2
    统计：flow_count=2、step_count=6、edge_count=4
    主 diff：改 src/app/core.py
      → direct=[FL-001/S2]；affected=[S2,S3,S4]；dangling=[FL-002/R2]；verdict=impacted

覆盖：
    ① 无 `--flow`：`doc["flow"] is None`、页面**不含** `<section id="flow">`、
       既有六个段及其顺序完全不变、`_CSS` 未新增 `verdict.clear` / `verdict.impacted` 两条规则；
    ② 给了 `--flow`：出现 `<section id="flow">`，段内流程数 / 步骤数 / 边数与 `flow.analyze` 一致；
    ③ 三态徽标逐条取自 `flow` 的 `status`（active / dangling / unanchored 各至少一例，逐行钉住）；
    ④ 无 `--diff`：给出「未提供 diff」提示，且**不出现**影响清单；
    ⑤ 有 `--diff`：`verdict` 与四组清单逐字取自 `flow` 的影响文档；
    ⑥ 同一次采集：段内计数与 `flow.analyze(...)` 单次结果完全一致（不是两次跑出来的）；
    ⑦ 确定性：同输入两次 `render_html` 逐字节一致；
    ⑧ 只读：渲染前后夹具复合摘要不变；
    ⑨ CLI：`view --flow`（含 `--diff`）与无 `--flow` 两路 stdout 均与库输出逐字节一致、
       无 `\\r\\n` 翻译、退出码 0；
    ⑩ 非法输入：坏流程文档 / 坏 diff → 1；参数不足 / `--diff` 缺值 / `--diff` 无 `--flow` → 2。

沿用 M0–M12 约定：不用 `subprocess` 管道，改临时文件重定向（本机沙箱禁建管道）。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from . import flow, viewer
from .selftest_kit import PKG_DIR, cli as _cli, dir_digest as _tree_digest


FLOW_SECTION = '<section id="flow">'

_DESIGN = (
    "# 夹具设计文档（M13 自测专用）\n"
    "\n"
    "### OK-001 — 精确锚 core.py\n"
    "- type: 数据完整性\n"
    "- invariant: 示例不变量\n"
    "- change_control: free\n"
    "- severity: normal\n"
    "- evidence:\n"
    "  - src/app/core.py\n"
    "- action_policy: 警告\n"
)

_FLOW_DOC = (
    "# 流程夹具（M13 自测专用）\n"
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

_DIFF_CORE = (
    "diff --git a/src/app/core.py b/src/app/core.py\n"
    "index 1111111..2222222 100644\n"
    "--- a/src/app/core.py\n"
    "+++ b/src/app/core.py\n"
    "@@ -1 +1 @@\n"
    "-X = 1\n"
    "+X = 2\n"
)

_EXISTING_SECTIONS = [
    '<section id="overview">',
    '<section id="entries">',
    '<section id="dangling">',
    '<section id="unanchored">',
    '<section id="uncovered">',
    '<section id="graph">',
]


def _make_root(td: Path) -> Path:
    """建最小代码根：正规包（层层 `__init__.py`，使依赖图有节点）+ 两个非 `.py` 载体。"""
    root = td / "root"
    (root / "src" / "app").mkdir(parents=True)
    (root / "docs").mkdir(parents=True)
    (root / "src" / "app" / "__init__.py").write_text("", encoding="utf-8")
    (root / "src" / "app" / "core.py").write_text("X = 1\n", encoding="utf-8")
    (root / "src" / "app" / "api.py").write_text("from app.core import X\n\nY = 2\n", encoding="utf-8")
    (root / "src" / "app" / "notify.py").write_text("N = 1\n", encoding="utf-8")
    (root / "src" / "app" / "report.py").write_text("R = 1\n", encoding="utf-8")
    (root / "src" / "app" / "other.py").write_text("Z = 3\n", encoding="utf-8")
    (root / "docs" / "guide.md").write_text("# 指南\n", encoding="utf-8")
    (root / "docs" / "spec.md").write_text("# 规格\n", encoding="utf-8")
    return root


def _write(td: Path, name: str, text: str) -> Path:
    p = td / name
    p.write_text(text, encoding="utf-8")
    return p


def _flow_body(page: str) -> str:
    """截出流程段正文（供只在段内计数，避免与条目段的同名徽标混淆）。"""
    assert FLOW_SECTION in page, "页面里没有流程段"
    tail = page.split(FLOW_SECTION, 1)[1]
    return tail.split("</section>", 1)[0]


def test_no_flow_page_unchanged() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        design = _write(td, "design.md", _DESIGN)
        doc = viewer.analyze(root, design)
        page = viewer.render_html(doc)
        default = viewer.analyze(root, design, None, None, None)
    assert doc["flow"] is None, "未给流程文档时 flow 应为 None"
    assert FLOW_SECTION not in page, "未给流程文档时不应出现流程段"
    found = [ln for ln in page.splitlines() if ln.startswith("<section id=")]
    assert found == _EXISTING_SECTIONS, f"既有六段或其次序被改动：{found}"
    # 不新增 CSS：`_CSS` 位于每个页面同一个 <style> 内，增行会泄漏到所有页面
    assert "verdict.clear" not in viewer._CSS, "_CSS 新增了 verdict.clear（会破坏默认关闭时的页面不变性）"
    assert "verdict.impacted" not in viewer._CSS, "_CSS 新增了 verdict.impacted"
    assert doc == default, "默认参数路径（省略 flow_doc / diff_file）结果应完全一致"


def test_flow_section_matches_flow_counts() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        design = _write(td, "design.md", _DESIGN)
        fdoc = _write(td, "flow.md", _FLOW_DOC)
        doc = viewer.analyze(root, design, None, fdoc)
        expected = flow.analyze(fdoc, root)
        page = viewer.render_html(doc)
    assert FLOW_SECTION in page, "给了流程文档就应出现流程段"
    assert f"业务流影响面（流程 {expected['flow_count']} / 步骤 {expected['step_count']} / 边 {expected['edge_count']}）" in page
    assert '<details class="flow" id="flow-FL-001">' in page
    assert '<details class="flow" id="flow-FL-002">' in page
    assert "（4 步 / 3 边）" in page, "FL-001 无失联步骤，摘要不应带失联数"
    assert "（2 步 / 1 边，失联 1）" in page, "FL-002 有 1 个失联步骤（R2）"


def test_step_status_badges_from_flow() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        design = _write(td, "design.md", _DESIGN)
        fdoc = _write(td, "flow.md", _FLOW_DOC)
        doc = viewer.analyze(root, design, None, fdoc)
        expected = flow.analyze(fdoc, root)
        page = viewer.render_html(doc)
    body = _flow_body(page)
    assert (
        '<li><code>S1</code> 校验库存<span class="badge active">活性</span> '
        '<span class="muted">src/app/api.py</span></li>'
    ) in body
    assert (
        '<li><code>S4</code> 人工复核<span class="badge unanchored">无锚</span> '
        '<span class="muted">（无证据）</span></li>'
    ) in body
    assert (
        '<li><code>R2</code> 归档<span class="badge dangling">失联</span> '
        '<span class="muted">src/app/archive.py</span></li>'
    ) in body
    # 段内各态徽标数必须等于 flow 里对应 status 的步骤数（逐态钉住，防自造口径）
    for status in ("active", "dangling", "unanchored"):
        want = sum(1 for f in expected["flows"] for s in f["steps"] if s["status"] == status)
        assert body.count(f'badge {status}') == want, f"{status} 徽标数与 flow 不一致"


def test_no_diff_no_impact_list() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        design = _write(td, "design.md", _DESIGN)
        fdoc = _write(td, "flow.md", _FLOW_DOC)
        doc = viewer.analyze(root, design, None, fdoc)
        page = viewer.render_html(doc)
    assert doc["flow"]["impact"] is None, "没给 diff 时 impact 应为 None"
    assert '<p class="kv muted">未提供 diff（仅呈现流程结构与锚活性）</p>' in page
    assert "<h3>影响清单</h3>" not in page, "没给 diff 时不应出现影响清单"


def test_impact_values_from_flow() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        design = _write(td, "design.md", _DESIGN)
        fdoc = _write(td, "flow.md", _FLOW_DOC)
        diff = _write(td, "d.diff", _DIFF_CORE)
        doc = viewer.analyze(root, design, None, fdoc, diff)
        expected = flow.analyze(fdoc, root, diff)
        page = viewer.render_html(doc)
    impact = expected["impact"]
    assert doc["flow"] == expected, "段内数据必须就是 flow.analyze 的返回文档"
    assert '<p class="verdict drift">判定：impacted</p>' in page, "verdict=impacted 应复用既有 drift 配色"
    for title, items in (
        ("changed files", expected["impact"]["changed_files"]),
        ("direct steps", expected["impact"]["direct_steps"]),
        ("affected steps", expected["impact"]["affected_steps"]),
        ("dangling steps", expected["impact"]["dangling_steps"]),
    ):
        assert f"<li>{title}：{len(items)}</li>" in page, f"{title} 计数与 flow 不一致"
        assert f"<details><summary>{title}（{len(items)}）</summary>" in page, f"{title} 分组标题不符"
    assert "<li class=\"kv\">src/app/core.py</li>" in page
    for pair in ("FL-001/S2", "FL-001/S3", "FL-001/S4", "FL-002/R2"):
        assert f'<li class="kv">{pair}</li>' in page, f"清单缺 {pair}"
    assert impact["verdict"] == "impacted" and len(impact["affected_steps"]) == 3


def test_single_collection() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        design = _write(td, "design.md", _DESIGN)
        fdoc = _write(td, "flow.md", _FLOW_DOC)
        diff = _write(td, "d.diff", _DIFF_CORE)
        doc = viewer.analyze(root, design, None, fdoc, diff)
        expected = flow.analyze(fdoc, root, diff)
        page = viewer.render_html(doc)
    assert doc["flow"] == expected, "可视面应原样复用同一次 flow.analyze 结果（不得二次跑或重算）"
    assert f"流程 {expected['flow_count']} / 步骤 {expected['step_count']} / 边 {expected['edge_count']}" in page


def test_determinism() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        design = _write(td, "design.md", _DESIGN)
        fdoc = _write(td, "flow.md", _FLOW_DOC)
        diff = _write(td, "d.diff", _DIFF_CORE)
        first = viewer.render_html(viewer.analyze(root, design, None, fdoc, diff))
        second = viewer.render_html(viewer.analyze(root, design, None, fdoc, diff))
    assert first == second, "同输入两次渲染应逐字节一致"


def test_render_is_readonly() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        design = _write(td, "design.md", _DESIGN)
        fdoc = _write(td, "flow.md", _FLOW_DOC)
        diff = _write(td, "d.diff", _DIFF_CORE)
        before = _tree_digest(td)
        viewer.render_html(viewer.analyze(root, design, None, fdoc, diff))
        after = _tree_digest(td)
    assert after == before, "渲染过程改动了夹具内容（应全程只读）"


def test_cli_bytes() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        design = _write(td, "design.md", _DESIGN)
        fdoc = _write(td, "flow.md", _FLOW_DOC)
        diff = _write(td, "d.diff", _DIFF_CORE)

        code, out, err = _cli("view", str(root), str(design), "--flow", str(fdoc), "--diff", str(diff))
        expected = viewer.render_html(viewer.analyze(root, design, None, fdoc, diff))
        assert code == 0, f"带流程段应退出 0，实际 {code}；stderr={err!r}"
        assert out == expected.encode("utf-8"), "CLI stdout 与库渲染非逐字节一致"
        assert b"\r\n" not in out, "stdout 出现 \\r\\n 翻译，说明未走字节流输出"

        code, out, err = _cli("view", str(root), str(design))
        expected = viewer.render_html(viewer.analyze(root, design))
        assert code == 0, f"无流程段应退出 0，实际 {code}；stderr={err!r}"
        assert out == expected.encode("utf-8"), "无流程段 CLI stdout 与库渲染非逐字节一致"
        assert b"\r\n" not in out, "stdout 出现 \\r\\n 翻译"


def test_cli_rejects_bad_inputs() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        design = _write(td, "design.md", _DESIGN)
        fdoc = _write(td, "flow.md", _FLOW_DOC)

        bad_flow = _write(td, "bad-flow.md", "这不是合法流程文档\n")
        code, out, err = _cli("view", str(root), str(design), "--flow", str(bad_flow))
        assert code == 1, f"坏流程文档应退出 1，实际 {code}"
        assert err.strip() and not out, "坏流程文档应仅向 stderr 报错、不写 stdout"

        bad_diff = _write(td, "bad.diff", "这不是统一 diff\n")
        code, out, err = _cli("view", str(root), str(design), "--flow", str(fdoc), "--diff", str(bad_diff))
        assert code == 1, f"坏 diff 应退出 1，实际 {code}"
        assert err.strip() and not out, "坏 diff 应仅向 stderr 报错"

        code, out, err = _cli("view", str(root))
        assert code == 2, f"参数不足应退出 2（用法错误），实际 {code}"
        assert err.strip() and not out, "用法错误应仅向 stderr 报错"

        code, out, err = _cli("view", str(root), str(design), "--flow", str(fdoc), "--diff")
        assert code == 2, f"--diff 缺值应退出 2（用法错误），实际 {code}"
        assert err.strip() and not out, "--diff 缺值应仅向 stderr 报错"

        code, out, err = _cli("view", str(root), str(design), "--diff", str(_write(td, "d.diff", _DIFF_CORE)))
        assert code == 2, f"--diff 无 --flow 应退出 2（不静默丢弃），实际 {code}"
        assert err.strip() and not out, "--diff 无 --flow 应仅向 stderr 报错"


def main() -> int:
    tests = (
        test_no_flow_page_unchanged,
        test_flow_section_matches_flow_counts,
        test_step_status_badges_from_flow,
        test_no_diff_no_impact_list,
        test_impact_values_from_flow,
        test_single_collection,
        test_determinism,
        test_render_is_readonly,
        test_cli_bytes,
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
