"""M1 自测：把 M1 的验收点写成可执行断言。

覆盖：① 样例条目数等于期望且与 expected-entries.json 完全一致；
② 每条必填字段非空、类型与值域正确；③ 同输入两次解析结果一致（确定性）；
④ 不合格式的输入必须抛 ParseError（边界否定用例）；
⑤ CLI `python -m xprod parse` 退出码 0 且 stdout 与期望逐字节一致。

沿用 M0 约定：不用 `subprocess` 管道，改临时文件重定向（本机沙箱禁建管道）。
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from . import parser

PKG_DIR = Path(__file__).resolve().parent
SAMPLE = PKG_DIR / "samples" / "design-sample.md"
EXPECTED = PKG_DIR / "samples" / "expected-entries.json"

_REQUIRED_FIELDS = (
    "constraint_id",
    "title",
    "constraint_type",
    "expected_invariant",
    "change_control",
    "severity",
    "required_evidence",
    "action_policy",
)

_VALID_MINIMAL_DOC = """### X-001 — 示例
- type: 公共接口
- invariant: 示例不变量
- change_control: free
- severity: normal
- evidence:
  - 证据一
- action_policy: 警告
"""


def test_matches_expected() -> None:
    actual = parser.parse_file(SAMPLE)
    expected = json.loads(EXPECTED.read_text(encoding="utf-8"))
    assert actual == expected, "解析结果与 expected-entries.json 不一致"


def test_json_bytes_equal_expected() -> None:
    text = parser.to_json(parser.parse_file(SAMPLE))
    assert text == EXPECTED.read_text(encoding="utf-8"), "序列化文本与期望文件非逐字节一致"


def test_entry_count() -> None:
    doc = parser.parse_file(SAMPLE)
    assert doc["entry_count"] == 3, f"条目数应为 3，实际 {doc['entry_count']}"
    assert doc["entry_count"] == len(doc["entries"]), "entry_count 与 entries 长度不一致"


def test_required_fields_nonempty_and_typed() -> None:
    for e in parser.parse_file(SAMPLE)["entries"]:
        for key in _REQUIRED_FIELDS:
            assert key in e, f"条目 {e.get('constraint_id')} 缺少字段 {key}"
        for key in _REQUIRED_FIELDS:
            if key == "required_evidence":
                assert isinstance(e[key], list) and e[key], "required_evidence 应为非空列表"
                assert all(isinstance(x, str) and x.strip() for x in e[key]), "证据项不得为空串"
            else:
                assert isinstance(e[key], str) and e[key].strip(), f"字段 {key} 不得为空串"
        assert e["change_control"] in parser.CHANGE_CONTROL_DOMAIN
        assert e["severity"] in parser.SEVERITY_DOMAIN


def test_determinism() -> None:
    text = SAMPLE.read_text(encoding="utf-8")
    first = parser.to_json(parser.parse_text(text))
    second = parser.to_json(parser.parse_text(text))
    assert first == second, "同输入两次解析应完全一致"


def test_rejects_malformed() -> None:
    cases = {
        "缺少必填字段": _VALID_MINIMAL_DOC.replace("- action_policy: 警告\n", ""),
        "非法枚举值": _VALID_MINIMAL_DOC.replace("severity: normal", "severity: bogus"),
        "未知字段键": _VALID_MINIMAL_DOC + "- foo: bar\n",
        "证据列表为空": _VALID_MINIMAL_DOC.replace("  - 证据一\n", ""),
        "条目 ID 重复": _VALID_MINIMAL_DOC + _VALID_MINIMAL_DOC,
    }
    for name, bad in cases.items():
        try:
            parser.parse_text(bad)
        except parser.ParseError:
            continue
        raise AssertionError(f"格式非法（{name}）时应抛 ParseError，但未抛出")


def test_cli_parse() -> None:
    expected_text = EXPECTED.read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as td:
        out_p = Path(td) / "out.txt"
        err_p = Path(td) / "err.txt"
        with open(out_p, "w", encoding="utf-8") as fo, open(err_p, "w", encoding="utf-8") as fe:
            proc = subprocess.run(
                [sys.executable, "-m", "xprod", "parse", str(SAMPLE)],
                cwd=str(PKG_DIR.parent),
                stdout=fo,
                stderr=fe,
            )
        out = out_p.read_text(encoding="utf-8")
        err = err_p.read_text(encoding="utf-8")
    assert proc.returncode == 0, f"退出码应为 0，实际 {proc.returncode}；stderr={err!r}"
    assert out == expected_text, "CLI stdout 与期望文件非逐字节一致"


def main() -> int:
    tests = (
        test_matches_expected,
        test_json_bytes_equal_expected,
        test_entry_count,
        test_required_fields_nonempty_and_typed,
        test_determinism,
        test_rejects_malformed,
        test_cli_parse,
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
