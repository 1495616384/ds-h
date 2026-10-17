"""M8 自测：把「一致性漂移校验（锚活性）」的验收点写成可执行断言。

核心思路：**夹具临时自建**——每次测试在临时目录里现造一个最小代码根 + 设计文档，使本自测
**不依赖**任何归档基线副本、不依赖网络；本文件与 `drift.py` 同样不含冻结链目录名字面量
（由 M0 自测第三条校验）。

夹具的「锚活性」设计（决定各测试的期望值）：
    代码根文件（5 个）：src/app/core.py、src/app/api.py、src/app/other.py、docs/guide.md、docs/spec.md
    设计文档条目：
      OK-001 精确锚 `src/app/core.py`  → 命中 1 个文件
      OK-002 前缀锚 `docs/`            → 命中 docs/guide.md、docs/spec.md（2 个，全部列出）
      OK-003 无斜杠锚 `just-a-token`   → unanchored（显式列出、不参与判定）
      OK-004 精确锚 `src/app/api.py`   → 命中 1 个文件
    覆盖集合 = {core.py, api.py, docs/guide.md, docs/spec.md} → 盲区恰为 src/app/other.py

覆盖：
    ① 全活性：主夹具锚全部活性 → `ok`、无 dangling、active 记录数 = 3、entry 数 = 4；
    ② 精确锚指向不存在文件 → `drift`、dangling 1 条、reason = 路径不存在；
    ③ 前缀锚无匹配 → `drift`、reason = 前缀下无文件；
    ④ 前缀多命中**全部列出**（docs/ 下 2 个文件，排序稳定）；
    ⑤ 无斜杠锚被**显式列出**且**不参与**判定（主夹具仍 `ok`）；
    ⑥ 设计盲区 `uncovered_files` 恰为 other.py，且**不影响**判定；
    ⑦ 确定性：同输入两次分析逐字节一致；
    ⑧ 全程只读：夹具文件复合摘要前后不变；
    ⑨ CLI `drift` JSON stdout 与库输出逐字节一致（含无 `\\r\\n` 翻译）、退出码 0；
    ⑩ CLI `drift --text` 同理，且文本末尾判定为 `ok`；
    ⑪ 非法输入：代码根非目录 / 设计文档不合格式 → 退出码 1；参数不足 → 退出码 2；
    ⑫ 锚规则**唯一实现**（结构性断言）：锚规则已收口到 `parser.anchor_of`，
       M3（`impact_analyzer`）与 M8（`drift`）**不再**各持本地复刻（源码中不存在 `def _anchor_of`），
       且共享函数在探针集上判定符合预期。

沿用 M0–M7 约定：不用 `subprocess` 管道，改临时文件重定向（本机沙箱禁建管道）。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from . import drift, parser
from .selftest_kit import PKG_DIR, cli as _cli, dir_digest as _tree_digest, write_text_at as _write


_DESIGN_OK = (
    "# 夹具设计文档（M8 自测专用）\n"
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


def _one_entry_design(cid: str, anchor: str) -> str:
    """造一份只有单条证据锚的最小设计文档，用于钉住某一类活性判定。"""
    return (
        "# 单条目夹具\n"
        "\n"
        f"### {cid} — 单锚\n"
        "- type: 数据完整性\n"
        "- invariant: 示例不变量\n"
        "- change_control: free\n"
        "- severity: normal\n"
        "- evidence:\n"
        f"  - {anchor}\n"
        "- action_policy: 警告\n"
    )


def _make_root(td: Path) -> Path:
    """建最小代码根（5 个文件）；drift 只做文件系统存在性核对，无需 `__init__.py`。"""
    root = td / "root"
    (root / "src" / "app").mkdir(parents=True)
    (root / "docs").mkdir(parents=True)
    (root / "src" / "app" / "core.py").write_text("X = 1\n", encoding="utf-8")
    (root / "src" / "app" / "api.py").write_text("from app.core import X\n\nY = 2\n", encoding="utf-8")
    (root / "src" / "app" / "other.py").write_text("Z = 3\n", encoding="utf-8")
    (root / "docs" / "guide.md").write_text("# 指南\n", encoding="utf-8")
    (root / "docs" / "spec.md").write_text("# 规格\n", encoding="utf-8")
    return root


def _record_for(doc: dict, cid: str) -> dict:
    for r in doc["active_anchors"]:
        if r["constraint_id"] == cid:
            return r
    raise AssertionError(f"活性锚里没有条目 {cid}")


def test_all_anchors_active() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        design = _write(td, "design.md", _DESIGN_OK)
        doc = drift.analyze(root, design)
    assert doc["verdict"] == drift.VERDICT_OK, doc["verdict"]
    assert doc["dangling_count"] == 0 and doc["dangling_anchors"] == [], "不应有失联锚"
    assert doc["active_count"] == 3, f"应恰有 3 条活性锚（OK-003 为 unanchored）：{doc['active_count']}"
    assert doc["entry_count"] == 4, doc["entry_count"]
    assert doc["code_root_file_count"] == 5, doc["code_root_file_count"]


def test_exact_anchor_missing_is_drift() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        design = _write(td, "design.md", _one_entry_design("BAD-001", "src/app/missing.py"))
        doc = drift.analyze(root, design)
    assert doc["verdict"] == drift.VERDICT_DRIFT, doc["verdict"]
    assert doc["dangling_count"] == 1, doc["dangling_count"]
    d = doc["dangling_anchors"][0]
    assert d["anchor"] == "src/app/missing.py", d
    assert d["reason"] == drift.REASON_PATH_MISSING, d
    assert d["match_kind"] == drift.ANCHOR_EXACT, d


def test_prefix_anchor_no_match_is_drift() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        design = _write(td, "design.md", _one_entry_design("BAD-002", "no-such-dir/"))
        doc = drift.analyze(root, design)
    assert doc["verdict"] == drift.VERDICT_DRIFT, doc["verdict"]
    d = doc["dangling_anchors"][0]
    assert d["anchor"] == "no-such-dir/", d
    assert d["match_kind"] == drift.ANCHOR_PREFIX, d
    assert d["reason"] == drift.REASON_PREFIX_EMPTY, d


def test_prefix_multi_match_all_listed() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        design = _write(td, "design.md", _DESIGN_OK)
        doc = drift.analyze(root, design)
    r = _record_for(doc, "OK-002")
    assert r["match_kind"] == drift.ANCHOR_PREFIX, r
    assert r["matched_files"] == ["docs/guide.md", "docs/spec.md"], r["matched_files"]


def test_unanchored_listed_but_not_judged() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        design = _write(td, "design.md", _DESIGN_OK)
        doc = drift.analyze(root, design)
    assert doc["verdict"] == drift.VERDICT_OK, "unanchored 证据不参与判定，不应造成 drift"
    assert len(doc["unanchored_evidence"]) == 1, doc["unanchored_evidence"]
    u = doc["unanchored_evidence"][0]
    assert (u["constraint_id"], u["evidence"]) == ("OK-003", "just-a-token"), u


def test_uncovered_files_reference_only() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        design = _write(td, "design.md", _DESIGN_OK)
        doc = drift.analyze(root, design)
    assert doc["uncovered_files"] == ["src/app/other.py"], doc["uncovered_files"]
    assert doc["uncovered_file_count"] == 1, doc["uncovered_file_count"]
    assert doc["verdict"] == drift.VERDICT_OK, "盲区只作参考，不得改变判定"


def test_determinism() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        design = _write(td, "design.md", _DESIGN_OK)
        first = drift.to_json(drift.analyze(root, design))
        second = drift.to_json(drift.analyze(root, design))
    assert first == second, "同输入两次分析应完全一致"


def test_analysis_is_readonly() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        design = _write(td, "design.md", _DESIGN_OK)
        before = _tree_digest(td)
        drift.analyze(root, design)
        after = _tree_digest(td)
    assert after == before, "分析过程改动了夹具内容（应全程只读）"


def test_cli_json_bytes() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        design = _write(td, "design.md", _DESIGN_OK)
        code, out, err = _cli("drift", str(root), str(design))
        expected = drift.analyze(root, design)
    assert code == 0, f"退出码应为 0，实际 {code}；stderr={err!r}"
    assert out == drift.to_json(expected).encode("utf-8"), "CLI JSON stdout 与库输出非逐字节一致"
    assert b"\r\n" not in out, "stdout 出现 \\r\\n 翻译，说明未走字节流输出"


def test_cli_text_bytes() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        design = _write(td, "design.md", _DESIGN_OK)
        code, out, err = _cli("drift", str(root), str(design), "--text")
        expected = drift.analyze(root, design)
    assert code == 0, f"文本模式应退出 0，实际 {code}；stderr={err!r}"
    assert out == drift.render_text(expected).encode("utf-8"), "CLI --text stdout 与库输出不一致"
    assert b"\r\n" not in out, "stdout 出现 \\r\\n 翻译"
    assert b"verdict: ok\n" in out, "全活性夹具的文本判定应为 ok"


def test_cli_rejects_bad_inputs() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        design = _write(td, "design.md", _DESIGN_OK)

        not_dir = _write(td, "not-a-dir.txt", "x\n")
        code, out, err = _cli("drift", str(not_dir), str(design))
        assert code == 1, f"代码根非目录应退出 1，实际 {code}"
        assert err.strip() and not out, "代码根非目录应仅向 stderr 报错、不写 stdout"

        bad_design = _write(td, "bad.md", "这不是合法设计文档\n")
        code, out, err = _cli("drift", str(root), str(bad_design))
        assert code == 1, f"设计文档不合格式应退出 1，实际 {code}"
        assert err.strip() and not out, "设计文档不合格式应仅向 stderr 报错"

        code, out, err = _cli("drift", str(root))
        assert code == 2, f"参数不足应退出 2（用法错误），实际 {code}"
        assert err.strip() and not out, "用法错误应仅向 stderr 报错"


def test_anchor_rule_single_source() -> None:
    """锚规则收口为 `parser.anchor_of` 唯一实现：M3 / M8 不再各持一份本地复刻。"""
    probes = (
        "src/app/core.py",
        "docs/",
        "just-a-token",
        "src/app/x.py 附带说明文字",
        "a/b c/d",
        "",
        "   ",
    )
    expected = ["src/app/core.py", "docs/", None, "src/app/x.py", "a/b", None, None]
    assert [parser.anchor_of(e) for e in probes] == expected, "共享锚规则结果不符预期"

    # 结构性断言：产品源码中不应再有 `def _anchor_of` 本地复刻（全仓唯一实现只在 parser）
    offenders = []
    for py in PKG_DIR.rglob("*.py"):
        if py.name.startswith("selftest"):
            continue  # 自测里的断言文本不计入产品代码
        if "def _anchor_of" in py.read_text(encoding="utf-8"):
            offenders.append(py.relative_to(PKG_DIR).as_posix())
    assert not offenders, f"锚规则仍存在本地复刻（应收口到 parser.anchor_of）：{offenders}"


def main() -> int:
    tests = (
        test_all_anchors_active,
        test_exact_anchor_missing_is_drift,
        test_prefix_anchor_no_match_is_drift,
        test_prefix_multi_match_all_listed,
        test_unanchored_listed_but_not_judged,
        test_uncovered_files_reference_only,
        test_determinism,
        test_analysis_is_readonly,
        test_cli_json_bytes,
        test_cli_text_bytes,
        test_cli_rejects_bad_inputs,
        test_anchor_rule_single_source,
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
