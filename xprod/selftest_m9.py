"""M9 自测：把「逻辑控制面可视面」的验收点写成可执行断言。

核心思路：**夹具临时自建**——每次测试在临时目录里现造一个最小代码根 + 设计文档，使本自测
**不依赖**任何归档基线副本、不依赖网络；本文件与 `viewer.py` 同样不含冻结链目录名字面量
（由 M0 自测第三条校验）。

覆盖：
    ① 自包含：产物以 `<!DOCTYPE html>` 起头、以 `</html>` 收尾，且**不含**任何外部引用
       （`http(s)://` / `<script` / `@import` / `src=` / `href=`）；
    ② 条目齐全：设计文档的每个条目 id 都出现在页面上；
    ③ 判定呈现：全活性夹具显示 `ok`；含失联锚夹具显示 `drift` 并列出失联原因；
    ④ 可下钻：页面含原生 `<details>` / `<summary>`，且数量不少于条目数（零脚本下钻）；
    ⑤ 确定性：同输入两次渲染逐字节一致；
    ⑥ 全程只读：夹具文件复合摘要前后不变；
    ⑦ 不新增判定语义：`viewer.analyze` 的判定与计数与 `drift.analyze` 完全一致；
    ⑧ CLI `view` 的 stdout 与库输出逐字节一致（含无 `\\r\\n` 翻译）、退出码 0；
    ⑨ 非法输入：代码根非目录 / 设计文档不合格式 → 退出码 1；参数不足 → 退出码 2。

沿用 M0–M8 约定：不用 `subprocess` 管道，改临时文件重定向（本机沙箱禁建管道）。
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path

from . import drift, viewer

PKG_DIR = Path(__file__).resolve().parent

_DESIGN_OK = (
    "# 夹具设计文档（M9 自测专用）\n"
    "\n"
    "### OK-001 — 精确锚 core.py\n"
    "- type: 数据完整性\n"
    "- invariant: 示例不变量\n"
    "- change_control: free\n"
    "- severity: normal\n"
    "- evidence:\n"
    "  - src/app/core.py\n"
    "- action_policy: 警告\n"
    "\n"
    "### OK-002 — 前缀锚 docs/\n"
    "- type: 公共接口\n"
    "- invariant: 示例不变量\n"
    "- change_control: free\n"
    "- severity: normal\n"
    "- evidence:\n"
    "  - docs/\n"
    "- action_policy: 警告\n"
    "\n"
    "### OK-003 — 无斜杠锚（unanchored）\n"
    "- type: 公共接口\n"
    "- invariant: 示例不变量\n"
    "- change_control: free\n"
    "- severity: normal\n"
    "- evidence:\n"
    "  - just-a-token\n"
    "- action_policy: 警告\n"
    "\n"
    "### OK-004 — 精确锚 api.py\n"
    "- type: 数据完整性\n"
    "- invariant: 示例不变量\n"
    "- change_control: free\n"
    "- severity: normal\n"
    "- evidence:\n"
    "  - src/app/api.py\n"
    "- action_policy: 警告\n"
)

_DESIGN_DRIFT = _DESIGN_OK + (
    "\n"
    "### BAD-001 — 精确锚指向不存在文件\n"
    "- type: 数据完整性\n"
    "- invariant: 示例不变量\n"
    "- change_control: free\n"
    "- severity: normal\n"
    "- evidence:\n"
    "  - src/app/missing.py\n"
    "- action_policy: 警告\n"
)

_ENTRY_IDS = ("OK-001", "OK-002", "OK-003", "OK-004")


def _make_root(td: Path) -> Path:
    """建最小代码根：正规包（层层 `__init__.py`，使依赖图有节点）+ 两个非 `.py` 载体。"""
    root = td / "root"
    (root / "src" / "app").mkdir(parents=True)
    (root / "docs").mkdir(parents=True)
    (root / "src" / "app" / "__init__.py").write_text("", encoding="utf-8")
    (root / "src" / "app" / "core.py").write_text("X = 1\n", encoding="utf-8")
    (root / "src" / "app" / "api.py").write_text("from app.core import X\n\nY = 2\n", encoding="utf-8")
    (root / "src" / "app" / "other.py").write_text("Z = 3\n", encoding="utf-8")
    (root / "docs" / "guide.md").write_text("# 指南\n", encoding="utf-8")
    (root / "docs" / "spec.md").write_text("# 规格\n", encoding="utf-8")
    return root


def _write(td: Path, name: str, text: str) -> Path:
    p = td / name
    p.write_text(text, encoding="utf-8")
    return p


def _cli(*args: str) -> tuple[int, bytes, str]:
    """以临时文件重定向方式跑一次 CLI，返回（退出码, stdout 字节, stderr 文本）。"""
    with tempfile.TemporaryDirectory() as td:
        out_p, err_p = Path(td) / "out.bin", Path(td) / "err.txt"
        with open(out_p, "wb") as fo, open(err_p, "w", encoding="utf-8") as fe:
            proc = subprocess.run(
                [sys.executable, "-m", "xprod", *args],
                cwd=str(PKG_DIR.parent),
                stdout=fo,
                stderr=fe,
            )
        return proc.returncode, out_p.read_bytes(), err_p.read_text(encoding="utf-8")


def _tree_digest(root: Path) -> str:
    """根下全部文件的复合摘要：逐文件 SHA-256 按相对路径排序后汇总。"""
    rows = []
    for p in sorted(q for q in root.rglob("*") if q.is_file()):
        rows.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(root).as_posix()}")
    return hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest()


def test_html_is_self_contained() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        design = _write(td, "design.md", _DESIGN_OK)
        page = viewer.render_html(viewer.analyze(str(root), str(design)))
    assert page.startswith("<!DOCTYPE html>\n"), page[:40]
    assert page.endswith("</html>\n"), page[-20:]
    for forbidden in ("http://", "https://", "<script", "@import", "src=", "href="):
        assert forbidden not in page, f"产物出现外部引用/脚本痕迹：{forbidden!r}"


def test_html_lists_all_entries() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        design = _write(td, "design.md", _DESIGN_OK)
        page = viewer.render_html(viewer.analyze(str(root), str(design)))
    for cid in _ENTRY_IDS:
        assert f'id="entry-{cid}"' in page, f"页面缺少条目锚点 {cid}"
    assert "判定：ok" in page, "全活性夹具的判定应为 ok"


def test_html_shows_drift_and_reason() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        design = _write(td, "design.md", _DESIGN_DRIFT)
        page = viewer.render_html(viewer.analyze(str(root), str(design)))
    assert "判定：drift" in page, "含失联锚的夹具判定应为 drift"
    assert "src/app/missing.py" in page, "失联锚路径应被列出"
    assert drift.REASON_PATH_MISSING in page, "失联原因应被呈现"


def test_drilldown_is_script_free() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        design = _write(td, "design.md", _DESIGN_OK)
        doc = viewer.analyze(str(root), str(design))
        page = viewer.render_html(doc)
    assert "<details" in page and "<summary>" in page, "下钻应使用原生 details/summary"
    assert page.count("<details") >= len(doc["entries"]), "每个条目都应有可展开的下钻块"


def test_determinism() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        design = _write(td, "design.md", _DESIGN_OK)
        first = viewer.render_html(viewer.analyze(str(root), str(design)))
        second = viewer.render_html(viewer.analyze(str(root), str(design)))
    assert first == second, "同输入两次渲染应完全一致"


def test_render_is_readonly() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        design = _write(td, "design.md", _DESIGN_OK)
        before = _tree_digest(td)
        viewer.render_html(viewer.analyze(str(root), str(design)))
        after = _tree_digest(td)
    assert after == before, "渲染过程改动了夹具内容（应全程只读）"


def test_verdict_matches_drift() -> None:
    """可视面只做呈现：判定与各计数必须与 `drift` 完全一致。"""
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        design = _write(td, "design.md", _DESIGN_DRIFT)
        composed = viewer.analyze(str(root), str(design))
        base = drift.analyze(str(root), str(design))
    assert composed["verdict"] == base["verdict"], "可视面判定与 drift 出现分叉"
    assert composed["entry_count"] == base["entry_count"]
    assert composed["active_count"] == base["active_count"]
    assert composed["dangling_count"] == base["dangling_count"]
    assert composed["unanchored_count"] == len(base["unanchored_evidence"])
    assert composed["uncovered_file_count"] == base["uncovered_file_count"]
    assert composed["active_anchors"] == base["active_anchors"]
    assert composed["dangling_anchors"] == base["dangling_anchors"]


def test_cli_bytes() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        design = _write(td, "design.md", _DESIGN_OK)
        code, out, err = _cli("view", str(root), str(design))
        expected = viewer.render_html(viewer.analyze(str(root), str(design)))
    assert code == 0, f"退出码应为 0，实际 {code}；stderr={err!r}"
    assert out == expected.encode("utf-8"), "CLI stdout 与库输出非逐字节一致"
    assert b"\r\n" not in out, "stdout 出现 \\r\\n 翻译，说明未走字节流输出"


def test_cli_rejects_bad_inputs() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        design = _write(td, "design.md", _DESIGN_OK)

        not_dir = _write(td, "not-a-dir.txt", "x\n")
        code, out, err = _cli("view", str(not_dir), str(design))
        assert code == 1, f"代码根非目录应退出 1，实际 {code}"
        assert err.strip() and not out, "代码根非目录应仅向 stderr 报错、不写 stdout"

        bad_design = _write(td, "bad.md", "这不是合法设计文档\n")
        code, out, err = _cli("view", str(root), str(bad_design))
        assert code == 1, f"设计文档不合格式应退出 1，实际 {code}"
        assert err.strip() and not out, "设计文档不合格式应仅向 stderr 报错"

        code, out, err = _cli("view", str(root))
        assert code == 2, f"参数不足应退出 2（用法错误），实际 {code}"
        assert err.strip() and not out, "用法错误应仅向 stderr 报错"


def main() -> int:
    tests = (
        test_html_is_self_contained,
        test_html_lists_all_entries,
        test_html_shows_drift_and_reason,
        test_drilldown_is_script_free,
        test_determinism,
        test_render_is_readonly,
        test_verdict_matches_drift,
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
