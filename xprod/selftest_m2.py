"""M2 自测：把 M2 的验收点写成可执行断言。

扫描根由图构建器之外传入（命令行第一个参数），本文件不写死任何具体路径，
以维持与冻结链的物理隔离（由 M0 自测第三条校验本包源码不含冻结链目录名）。

覆盖：
    ① 节点数/边数/符号总数/环与固定真值一致；
    ② 构建结果与 `samples/expected-graph.json` 完全一致且序列化逐字节一致；
    ③ 下钻 `src/eval/types.py` 的文本与 `samples/expected-tree-eval-types.txt` 逐字节一致；
    ④ 循环依赖被检出且构建正常收敛（不卡死）；
    ⑤ 两条易错解析规则的回归护栏：绝对导入不得冠当前包名（不出现 `src.` 前缀模块名）、
       重导出边只能从包 `__init__.py` 发出；
    ⑥ 同输入两次构建逐字节一致（确定性）；
    ⑦ 构建全程只读：根下文件复合摘要前后不变；
    ⑧ CLI `graph` 退出码 0 且 stdout 与真值逐字节一致；`--tree` 同理；
    ⑨ CLI 未知节点必须退出码 1 并向 stderr 报错（边界否定用例）。

沿用 M0/M1 约定：不用 `subprocess` 管道，改临时文件重定向（本机沙箱禁建管道）。
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from .graph_builder import build_graph, render_node_tree, to_json

PKG_DIR = Path(__file__).resolve().parent
EXPECTED_GRAPH = PKG_DIR / "samples" / "expected-graph.json"
EXPECTED_TREE = PKG_DIR / "samples" / "expected-tree-eval-types.txt"
DRILL_NODE = "src/eval/types.py"

# 固定真值（人工从只读副本静态推导并独立对账，见 M2 结果报告）
NODE_COUNT = 25
EDGE_COUNT = 47
SYMBOL_TOTAL = 207
KNOWN_CYCLES = [["src/eval/types.py", "src/eval/validator.py"]]


def _root() -> Path:
    """取命令行传入的扫描根；缺失即报用法错误，绝不回退到某个内置默认路径。"""
    if len(sys.argv) < 2:
        raise SystemExit("usage: python -m xprod.selftest_m2 <code-root>")
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


def test_matches_expected() -> None:
    actual = build_graph(ROOT)
    expected = json.loads(EXPECTED_GRAPH.read_text(encoding="utf-8"))
    assert actual == expected, "构建结果与 expected-graph.json 不一致"


def test_json_bytes_equal_expected() -> None:
    text = to_json(build_graph(ROOT))
    assert text == EXPECTED_GRAPH.read_text(encoding="utf-8"), "序列化文本与期望文件非逐字节一致"


def test_counts_and_cycles() -> None:
    doc = build_graph(ROOT)
    assert doc["node_count"] == NODE_COUNT, f"节点数应为 {NODE_COUNT}，实际 {doc['node_count']}"
    assert doc["edge_count"] == EDGE_COUNT, f"边数应为 {EDGE_COUNT}，实际 {doc['edge_count']}"
    symbols = sum(len(n["symbols"]) for n in doc["nodes"])
    assert symbols == SYMBOL_TOTAL, f"符号总数应为 {SYMBOL_TOTAL}，实际 {symbols}"
    assert doc["node_count"] == len(doc["nodes"]), "node_count 与 nodes 长度不一致"
    assert doc["edge_count"] == len(doc["edges"]), "edge_count 与 edges 长度不一致"


def test_cycle_detected_and_build_terminates() -> None:
    doc = build_graph(ROOT)
    assert doc["cycles"] == KNOWN_CYCLES, f"环应为 {KNOWN_CYCLES}，实际 {doc['cycles']}"


def test_resolution_rules_regression() -> None:
    doc = build_graph(ROOT)
    # `src/` 目录无 __init__.py，不是正规包；绝对导入若被误冠当前包名，
    # 会凭空造出 `src.cdm.domain` 这类假模块名（`tests.` 前缀则合法，根下有 __init__.py）
    bad = [n["id"] for n in doc["nodes"] if n["module"] == "src" or n["module"].startswith("src.")]
    assert not bad, f"出现被误冠导入根前缀的假模块名：{bad}"
    # 重导出按定义只能由包 `__init__.py` 发出
    offenders = [e["from"] for e in doc["edges"] if e["kind"] == "reexport"]
    assert all(f.endswith("__init__.py") for f in offenders), f"重导出边来自非包初始化文件：{offenders}"
    kinds = {e["kind"] for e in doc["edges"]}
    assert kinds <= {"import", "reexport"}, f"出现未定义边类型：{kinds - {'import', 'reexport'}}"


def test_determinism() -> None:
    first = to_json(build_graph(ROOT))
    second = to_json(build_graph(ROOT))
    assert first == second, "同输入两次构建应完全一致"


def test_build_is_readonly() -> None:
    before = _tree_digest(ROOT)
    build_graph(ROOT)
    assert _tree_digest(ROOT) == before, "构建过程改动了扫描根内容（应全程只读）"


def test_cli_graph_json_bytes() -> None:
    code, out, err = _cli("graph", str(ROOT))
    assert code == 0, f"退出码应为 0，实际 {code}；stderr={err!r}"
    assert out == EXPECTED_GRAPH.read_bytes(), "CLI stdout 与期望文件非逐字节一致"


def test_cli_tree_bytes() -> None:
    code, out, err = _cli("graph", str(ROOT), "--tree", DRILL_NODE)
    assert code == 0, f"退出码应为 0，实际 {code}；stderr={err!r}"
    assert out == EXPECTED_TREE.read_bytes(), "下钻文本与期望文件非逐字节一致"


def test_cli_unknown_node_rejected() -> None:
    code, out, err = _cli("graph", str(ROOT), "--tree", "not/a/module.py")
    assert code == 1, f"未知节点退出码应为 1，实际 {code}"
    assert err.strip(), "未知节点应向 stderr 报错"
    assert not out, "未知节点不应写出 stdout"


def main() -> int:
    print(f"scan root: {ROOT}")
    tests = (
        test_matches_expected,
        test_json_bytes_equal_expected,
        test_counts_and_cycles,
        test_cycle_detected_and_build_terminates,
        test_resolution_rules_regression,
        test_determinism,
        test_build_is_readonly,
        test_cli_graph_json_bytes,
        test_cli_tree_bytes,
        test_cli_unknown_node_rejected,
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
