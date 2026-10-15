"""M3 自测：把 M3 的验收点写成可执行断言。

扫描根由命令行第一个参数传入，本文件不写死任何具体路径，
以维持与冻结链的物理隔离（由 M0 自测第三条校验本包源码不含冻结链目录名）。

覆盖（对应设计稿 §验收标准 ①–⑨）：
    ① 受影响条目集合 = {CV-001, DI-001}，且 PI-001 不命中（锚在别的文件上）；
    ② 受影响文件集合（含最小深度）与**人工推导真值**逐项一致；
    ③ 图外变更文件（docs/*.md）单独列出、不参与传播、不产深度；
    ④ 空 diff → 全空清单、退出码 0（用异常表达「没改东西」是错的）；
    ⑤ 非法 diff（缺 `+++` 头 / 根本不是 diff）→ 抛 ImpactError、CLI 退出码 1；
    ⑥ 同输入两次分析逐字节一致（确定性）；
    ⑦ 分析全程只读：扫描根文件复合摘要前后不变；
    ⑧ CLI `impact` JSON stdout 与库输出逐字节一致（含无 `\\r\\n` 翻译）、退出码 0；
    ⑨ CLI `impact --text` 同理；
    ⑩ 锚规则回归：无 `/` 的锚被**显式登记**为 unanchored（不静默丢弃），
       目录前缀锚按前缀命中并标注 match_kind=prefix。

沿用 M0–M2 约定：不用 `subprocess` 管道，改临时文件重定向（本机沙箱禁建管道）。
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path

from . import impact_analyzer

PKG_DIR = Path(__file__).resolve().parent
SAMPLE_DIFF = PKG_DIR / "samples" / "simulated.diff"
SAMPLE_DESIGN = PKG_DIR / "samples" / "design-sample.md"

# ---- 人工推导真值（依据 expected-graph.json 的 47 条边做反向可达性推演） ----
# 直接变更（深度 0）＝ registry.py / id.py / enums.py；docs 不在图中，单独列。
AFFECTED_ENTRIES = ["CV-001", "DI-001"]
CHANGED_FILES = [
    "docs/05_EVALUATION.md",
    "src/cdm/id.py",
    "src/cdm/registry.py",
    "src/eval/enums.py",
]
IN_GRAPH_CHANGES = ["src/cdm/id.py", "src/cdm/registry.py", "src/eval/enums.py"]
OUT_OF_GRAPH_CHANGES = ["docs/05_EVALUATION.md"]
# (文件, 最小深度)：深度 1 = 直接依赖被改文件者；深度 2 为反向传递闭包的末层。
# 复核要点：「cdm/types.py」与「eval/types.py」是两个不同模块——`cdm/domain.py`
# 依赖的是前者，而前者不在受影响集合中，故 domain.py **不受**本次变更影响。
AFFECTED_FILES = [
    ("src/cdm/id.py", 0),
    ("src/cdm/registry.py", 0),
    ("src/eval/enums.py", 0),
    ("src/cdm/__init__.py", 1),
    ("src/cdm/domain_validate.py", 1),
    ("src/cdm/validate.py", 1),
    ("src/eval/__init__.py", 1),
    ("src/eval/accuracy/__init__.py", 1),
    ("src/eval/accuracy/binding.py", 1),
    ("src/eval/validator.py", 1),
    ("tests/cdm/test_domain.py", 1),
    ("tests/cdm/test_types.py", 1),
    ("src/eval/types.py", 2),
    ("tests/eval/test_accuracy.py", 2),
    ("tests/eval/test_loader.py", 2),
    ("tests/eval/test_types.py", 2),
    ("tests/eval/test_validator.py", 2),
]
MAX_DEPTH = 2

_UNANCHORED_DOC = """### T-001 — 无斜杠锚
- type: 数据完整性
- invariant: 示例
- change_control: free
- severity: normal
- evidence:
  - nodocs 口头约定
- action_policy: 警告

### T-002 — 目录前缀锚
- type: 公共接口
- invariant: 示例
- change_control: free
- severity: normal
- evidence:
  - docs/ 下的评测文档
- action_policy: 警告
"""


def _root() -> Path:
    """取命令行传入的扫描根；缺失即报用法错误，绝不回退到某个内置默认路径。"""
    if len(sys.argv) < 2:
        raise SystemExit("usage: python -m xprod.selftest_m3 <code-root>")
    root = Path(sys.argv[1])
    if not root.is_dir():
        raise SystemExit(f"扫描根不是目录：{root}")
    return root


ROOT = _root()


def _tree_digest(root: Path) -> str:
    """根下全部文件的复合摘要：逐文件 SHA-256 按相对路径排序后汇总。"""
    rows = []
    for p in sorted(q for q in root.rglob("*") if q.is_file()):
        rows.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(root).as_posix()}")
    return hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest()


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


def _doc() -> dict:
    return impact_analyzer.analyze_files(SAMPLE_DIFF, ROOT, SAMPLE_DESIGN)


def test_affected_entries() -> None:
    doc = _doc()
    ids = [e["constraint_id"] for e in doc["affected_entries"]]
    assert ids == AFFECTED_ENTRIES, f"受影响条目应为 {AFFECTED_ENTRIES}，实际 {ids}"
    assert "PI-001" not in ids, "PI-001 的锚（src/eval/__init__.py、tests/）均不在本次变更集内，不应命中"
    # CV-001 由「精确锚 src/eval/enums.py」+「精确锚 docs/05_EVALUATION.md」命中
    cv = doc["affected_entries"][0]
    kinds = {(m["matched_file"], m["match_kind"]) for m in cv["matched_evidence"]}
    assert kinds == {("src/eval/enums.py", "exact"), ("docs/05_EVALUATION.md", "exact")}, kinds
    assert len(cv["matched_evidence"]) == 2, "CV-001 的 3 条证据里只有 2 条锚落在变更集内"
    di = doc["affected_entries"][1]
    assert [m["matched_file"] for m in di["matched_evidence"]] == ["src/cdm/id.py"], "DI-001 应仅由 id.py 命中"
    assert doc["unanchored_evidence"] == [], "样例设计文档的锚均含 `/`，不应产生 unanchored 记录"


def test_affected_files_and_depth() -> None:
    doc = _doc()
    actual = [(f["id"], f["depth"]) for f in doc["affected_files"]]
    assert actual == AFFECTED_FILES, f"受影响文件/深度与真值不一致：\n{actual}"
    assert doc["affected_file_count"] == len(AFFECTED_FILES), "affected_file_count 与清单长度不一致"
    assert doc["affected_file_count"] == len(doc["affected_files"]), "计数与清单长度不一致"
    assert doc["max_depth"] == MAX_DEPTH, f"最大深度应为 {MAX_DEPTH}，实际 {doc['max_depth']}"
    # 反向闭包不越过「我是谁的依赖」：domain.py 依赖 cdm/types.py（不在受影响集合），
    # 故它不因 registry/id/enums 的改动而进入受影响集合
    ids = {f["id"] for f in doc["affected_files"]}
    for absent in (
        "src/cdm/domain.py",
        "src/cdm/types.py",
        "src/eval/accuracy/data_structures.py",
        "tests/__init__.py",
    ):
        assert absent not in ids, f"{absent} 不应出现在受影响集合中"


def test_out_of_graph_listed_and_not_propagated() -> None:
    doc = _doc()
    assert doc["changed_file_count"] == len(CHANGED_FILES), "变更文件计数与真值不一致"
    assert doc["changed_files"] == CHANGED_FILES, f"变更文件清单与真值不一致：{doc['changed_files']}"
    assert doc["in_graph_changes"] == IN_GRAPH_CHANGES, doc["in_graph_changes"]
    assert doc["out_of_graph_changes"] == OUT_OF_GRAPH_CHANGES, doc["out_of_graph_changes"]
    assert "docs/05_EVALUATION.md" not in {f["id"] for f in doc["affected_files"]}, "图外文件不得进入传播结果"


def test_determinism() -> None:
    first = impact_analyzer.to_json(_doc())
    second = impact_analyzer.to_json(_doc())
    assert first == second, "同输入两次分析应完全一致"


def test_analysis_is_readonly() -> None:
    before = _tree_digest(ROOT)
    _doc()
    assert _tree_digest(ROOT) == before, "分析过程改动了扫描根内容（应全程只读）"


def test_empty_diff_yields_empty_result() -> None:
    with tempfile.TemporaryDirectory() as td:
        empty = Path(td) / "empty.diff"
        empty.write_bytes(b"")
        doc = impact_analyzer.analyze_files(empty, ROOT, SAMPLE_DESIGN)
        assert doc["changed_file_count"] == 0 and doc["changed_files"] == [], "空 diff 不应有变更文件"
        assert doc["affected_entries"] == [] and doc["unanchored_evidence"] == [], "空 diff 不应有条目命中"
        assert doc["affected_file_count"] == 0 and doc["affected_files"] == [], "空 diff 不应有受影响文件"
        assert doc["max_depth"] is None, "空 diff 的最大深度应为 None"
        code, out, err = _cli("impact", str(empty), str(ROOT), str(SAMPLE_DESIGN))
    assert code == 0, f"空 diff 退出码应为 0，实际 {code}；stderr={err!r}"
    assert out == impact_analyzer.to_json(doc).encode("utf-8"), "空 diff 的 CLI stdout 与库输出不一致"


def test_malformed_diff_rejected() -> None:
    cases = {
        "缺少 +++ 头": "diff --git a/x.py b/x.py\n--- a/x.py\n@@ -1 +1 @@\n-a\n+b\n",
        "根本不是 diff": "hello world\n",
    }
    for name, bad in cases.items():
        try:
            impact_analyzer.analyze(bad, ROOT, SAMPLE_DESIGN)
        except impact_analyzer.ImpactError:
            pass
        else:
            raise AssertionError(f"非法 diff（{name}）应抛 ImpactError，但未抛出")
    with tempfile.TemporaryDirectory() as td:
        bad_p = Path(td) / "bad.diff"
        bad_p.write_text(cases["缺少 +++ 头"], encoding="utf-8")
        code, out, err = _cli("impact", str(bad_p), str(ROOT), str(SAMPLE_DESIGN))
    assert code == 1, f"非法 diff 的退出码应为 1，实际 {code}"
    assert err.strip(), "非法 diff 应向 stderr 报错"
    assert not out, "非法 diff 不应写出 stdout"


def test_cli_json_bytes() -> None:
    code, out, err = _cli("impact", str(SAMPLE_DIFF), str(ROOT), str(SAMPLE_DESIGN))
    assert code == 0, f"退出码应为 0，实际 {code}；stderr={err!r}"
    assert out == impact_analyzer.to_json(_doc()).encode("utf-8"), "CLI JSON stdout 与库输出非逐字节一致"
    assert b"\r\n" not in out, "stdout 出现 \\r\\n 翻译，说明未走字节流输出"


def test_cli_text_bytes() -> None:
    code, out, err = _cli("impact", str(SAMPLE_DIFF), str(ROOT), str(SAMPLE_DESIGN), "--text")
    assert code == 0, f"退出码应为 0，实际 {code}；stderr={err!r}"
    assert out == impact_analyzer.render_text(_doc()).encode("utf-8"), "CLI --text stdout 与库输出非逐字节一致"
    assert b"\r\n" not in out, "stdout 出现 \\r\\n 翻译，说明未走字节流输出"


def test_anchor_rules_regression() -> None:
    with tempfile.TemporaryDirectory() as td:
        design = Path(td) / "anchors.md"
        design.write_text(_UNANCHORED_DOC, encoding="utf-8")
        doc = impact_analyzer.analyze_files(SAMPLE_DIFF, ROOT, design)
    ids = [e["constraint_id"] for e in doc["affected_entries"]]
    assert ids == ["T-002"], f"仅前缀锚应命中，实际受影响条目 {ids}"
    assert doc["affected_entries"][0]["matched_evidence"][0]["match_kind"] == "prefix", "应标注为前缀匹配"
    assert doc["affected_entries"][0]["matched_evidence"][0]["matched_file"] == "docs/05_EVALUATION.md"
    assert [u["constraint_id"] for u in doc["unanchored_evidence"]] == ["T-001"], "无 `/` 的锚必须显式登记"
    assert doc["unanchored_evidence"][0]["evidence"] == "nodocs 口头约定", "应原样保留证据串"


def main() -> int:
    print(f"scan root: {ROOT}")
    tests = (
        test_affected_entries,
        test_affected_files_and_depth,
        test_out_of_graph_listed_and_not_propagated,
        test_determinism,
        test_analysis_is_readonly,
        test_empty_diff_yields_empty_result,
        test_malformed_diff_rejected,
        test_cli_json_bytes,
        test_cli_text_bytes,
        test_anchor_rules_regression,
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
