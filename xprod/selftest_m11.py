"""M11 自测：把「控制面增量呈现（view --baseline）」的验收点写成可执行断言。

核心思路：**夹具临时自建**——每次测试在临时目录里现造一个最小代码根 + 设计文档，使本自测
**不依赖**任何归档基线副本、不依赖网络；本文件与 `viewer.py` 同样不含冻结链目录名字面量
（由 M0 自测第三条校验）。

夹具（决定各测试期望值）：
    代码根文件（6 个）：src/app/__init__.py、src/app/core.py、src/app/api.py、src/app/other.py、
                       docs/guide.md、docs/spec.md
    设计 A：SY-001→src/app/core.py；SY-002→docs/；SY-003→just-a-token（无锚）；SY-004→src/app/api.py
    盲区：src/app/__init__.py、src/app/other.py（无锚覆盖）

覆盖：
    ① 无基线：文档 `sync` 为 None，渲染结果**不出现** `<section id="sync">`（与 M9 页面一致）；
    ② 基线=此刻：判定 `unchanged` 且**出现**增量段（反证 ① 的「条件渲染」确实生效）；
    ③ 基线后删掉被锚文件：判定 `regressed`、newly_dangling 命中该证据、页面出现 `regressed`；
    ④ **防分叉**：可视面增量 与 `sync.compare_snapshots` 直算的结果**逐字节一致**；
    ⑤ 确定性：同输入两次 `analyze` + 渲染逐字节一致；
    ⑥ 只读：`analyze` 全程不改动夹具内容；
    ⑦ 自包含：带基线的页面不含外部引用（http(s)://、<script、<link）；
    ⑧ CLI `view --baseline` stdout 与库渲染逐字节一致（含无 `\\r\\n` 翻译）、退出码 0；
    ⑨ CLI `view`（无基线）stdout 与库渲染逐字节一致、退出码 0；
    ⑩ 非法输入：坏基线 → 退出码 1；`--baseline` 缺值 / 多余位置参数 → 退出码 2。

沿用 M0–M10 约定：不用 `subprocess` 管道，改临时文件重定向（本机沙箱禁建管道）。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from . import sync, viewer
from .selftest_kit import cli as _cli, dir_digest as _tree_digest

PKG_DIR = Path(__file__).resolve().parent

SYNC_SECTION = '<section id="sync">'

_HEAD = (
    "- type: 数据完整性\n"
    "- invariant: 示例不变量\n"
    "- change_control: free\n"
    "- severity: normal\n"
)


def _entry(cid: str, title: str, anchors: tuple[str, ...]) -> str:
    lines = [f"### {cid} — {title}", _HEAD.rstrip("\n"), "- evidence:"]
    lines.extend(f"  - {a}" for a in anchors)
    lines.append("- action_policy: 警告")
    return "\n".join(lines) + "\n"


_DESIGN_A = (
    "# 夹具设计 A（M11 自测专用）\n\n"
    + _entry("SY-001", "精确锚 core.py", ("src/app/core.py",))
    + "\n"
    + _entry("SY-002", "前缀锚 docs/", ("docs/",))
    + "\n"
    + _entry("SY-003", "无斜杠锚", ("just-a-token",))
    + "\n"
    + _entry("SY-004", "精确锚 api.py", ("src/app/api.py",))
)


def _make_root(td: Path) -> Path:
    """建最小代码根；`core.py` 由 `_with_core` 控制（用于造「失联」状态）。"""
    root = td / "root"
    (root / "src" / "app").mkdir(parents=True)
    (root / "docs").mkdir(parents=True)
    (root / "src" / "app" / "__init__.py").write_text("", encoding="utf-8")
    (root / "src" / "app" / "api.py").write_text("Y = 2\n", encoding="utf-8")
    (root / "src" / "app" / "other.py").write_text("Z = 3\n", encoding="utf-8")
    (root / "docs" / "guide.md").write_text("# 指南\n", encoding="utf-8")
    (root / "docs" / "spec.md").write_text("# 规格\n", encoding="utf-8")
    return root


def _with_core(root: Path) -> None:
    (root / "src" / "app" / "core.py").write_text("X = 1\n", encoding="utf-8")


def _write(td: Path, name: str, text: str) -> Path:
    p = td / name
    p.write_text(text, encoding="utf-8")
    return p


def _keys(records: list[dict]) -> list[tuple[str, str]]:
    return [(r["constraint_id"], r["evidence"]) for r in records]


def test_no_baseline_has_no_sync_section() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        _with_core(root)
        design = _write(td, "design.md", _DESIGN_A)
        doc = viewer.analyze(str(root), str(design))
        html = viewer.render_html(doc)
    assert doc["sync"] is None, f"未给基线时 sync 应为 None：{doc['sync']!r}"
    assert SYNC_SECTION not in html, "无基线时不应出现增量段"
    assert "同步增量" not in html, "无基线时不应渲染增量标题"


def test_baseline_current_is_unchanged_and_renders() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        _with_core(root)
        design = _write(td, "design.md", _DESIGN_A)
        base = sync.snapshot(str(root), str(design))
        doc = viewer.analyze(str(root), str(design), base)
        html = viewer.render_html(doc)
    assert doc["sync"] is not None, "给了基线就应出现增量段"
    assert doc["sync"]["verdict"] == sync.VERDICT_UNCHANGED, doc["sync"]["verdict"]
    assert doc["sync"]["change_count"] == 0, doc["sync"]["change_count"]
    assert SYNC_SECTION in html, "给了基线就应出现 <section id=\"sync\">"
    assert "判定：unchanged" in html, "页面应显示 unchanged 判定"


def test_deleted_anchor_is_regressed() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        _with_core(root)
        design = _write(td, "design.md", _DESIGN_A)
        base = sync.snapshot(str(root), str(design))
        (root / "src" / "app" / "core.py").unlink()  # 锚指向的文件消失
        doc = viewer.analyze(str(root), str(design), base)
        html = viewer.render_html(doc)
    assert doc["sync"]["verdict"] == sync.VERDICT_REGRESSED, doc["sync"]["verdict"]
    assert _keys(doc["sync"]["newly_dangling"]) == [("SY-001", "src/app/core.py")], doc["sync"]["newly_dangling"]
    assert "判定：regressed" in html, "页面应显示 regressed 判定"
    assert "SY-001" in html and "新增失联" in html, "页面应列出新增失联明细"


def test_increment_not_forked_from_sync() -> None:
    """可视面增量必须与 M10 `sync.compare_snapshots` 直算结果**逐字节一致**（防口径分叉）。"""
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        _with_core(root)
        design = _write(td, "design.md", _DESIGN_A)
        base = sync.snapshot(str(root), str(design))
        (root / "src" / "app" / "other.py").unlink()  # 造一次「盲区变化」而非失联
        doc = viewer.analyze(str(root), str(design), base)
        direct = sync.compare_snapshots(base, sync.snapshot(str(root), str(design)))
    assert sync.to_json(doc["sync"]) == sync.to_json(direct), "可视面增量与 M10 直算结果不一致（口径分叉）"
    assert doc["sync"]["verdict"] == sync.VERDICT_CHANGED, doc["sync"]["verdict"]


def test_deterministic_render() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        _with_core(root)
        design = _write(td, "design.md", _DESIGN_A)
        base = sync.snapshot(str(root), str(design))
        first = viewer.render_html(viewer.analyze(str(root), str(design), base))
        second = viewer.render_html(viewer.analyze(str(root), str(design), base))
    assert first == second, "同输入两次渲染应逐字节一致"


def test_analyze_is_readonly() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        _with_core(root)
        design = _write(td, "design.md", _DESIGN_A)
        base = sync.snapshot(str(root), str(design))
        before = _tree_digest(td)
        viewer.render_html(viewer.analyze(str(root), str(design), base))
        viewer.render_html(viewer.analyze(str(root), str(design)))
        after = _tree_digest(td)
    assert after == before, "analyze/render 改动了夹具内容（应全程只读）"


def test_html_self_contained() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        _with_core(root)
        design = _write(td, "design.md", _DESIGN_A)
        base = sync.snapshot(str(root), str(design))
        html = viewer.render_html(viewer.analyze(str(root), str(design), base))
    assert "http://" not in html and "https://" not in html, "页面不应含外部引用"
    assert "<script" not in html.lower(), "页面不应含脚本"
    assert "<link" not in html.lower(), "页面不应含外部样式链接"


def test_cli_view_with_baseline_bytes() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        _with_core(root)
        design = _write(td, "design.md", _DESIGN_A)
        base_p = td / "base.json"
        sync.save_snapshot(base_p, sync.snapshot(str(root), str(design)))
        code, out, err = _cli("view", str(root), str(design), "--baseline", str(base_p))
        expected = viewer.render_html(
            viewer.analyze(str(root), str(design), sync.load_snapshot(base_p))
        )
    assert code == 0, f"退出码应为 0，实际 {code}；stderr={err!r}"
    assert out == expected.encode("utf-8"), "CLI stdout 与库渲染非逐字节一致"
    assert b"\r\n" not in out, "stdout 出现 \\r\\n 翻译"
    assert SYNC_SECTION.encode("utf-8") in out, "带基线的 CLI 输出应含增量段"


def test_cli_view_without_baseline_bytes() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        _with_core(root)
        design = _write(td, "design.md", _DESIGN_A)
        code, out, err = _cli("view", str(root), str(design))
        expected = viewer.render_html(viewer.analyze(str(root), str(design)))
    assert code == 0, f"无基线也应退出 0，实际 {code}；stderr={err!r}"
    assert out == expected.encode("utf-8"), "CLI stdout 与库渲染非逐字节一致"
    assert SYNC_SECTION.encode("utf-8") not in out, "无基线 CLI 输出不应含增量段"


def test_cli_rejects_bad_inputs() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        _with_core(root)
        design = _write(td, "design.md", _DESIGN_A)

        bad_base = _write(td, "bad.json", "not json")
        code, out, err = _cli("view", str(root), str(design), "--baseline", str(bad_base))
        assert code == 1, f"坏基线应退出 1，实际 {code}"
        assert err.strip() and not out, "坏基线应仅向 stderr 报错、不写 stdout"

        code, out, err = _cli("view", str(root), str(design), "--baseline")
        assert code == 2, f"--baseline 缺值应退出 2（用法错误），实际 {code}"
        assert err.strip() and not out, "用法错误应仅向 stderr 报错"

        code, out, err = _cli("view", str(root), str(design), "extra")
        assert code == 2, f"多余位置参数应退出 2（用法错误），实际 {code}"
        assert err.strip() and not out, "用法错误应仅向 stderr 报错"


def main() -> int:
    tests = (
        test_no_baseline_has_no_sync_section,
        test_baseline_current_is_unchanged_and_renders,
        test_deleted_anchor_is_regressed,
        test_increment_not_forked_from_sync,
        test_deterministic_render,
        test_analyze_is_readonly,
        test_html_self_contained,
        test_cli_view_with_baseline_bytes,
        test_cli_view_without_baseline_bytes,
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
