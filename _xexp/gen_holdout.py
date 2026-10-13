"""Holdout 案例（防过拟合审计）— 不参与引擎调参，验证 X v0 泛化能力。"""
import json
import subprocess
from pathlib import Path
import gen_cases

BASE = Path(r"G:\ds-h\_xexp\base")
CASES = Path(r"G:\ds-h\_xexp\cases")
TMP = Path(r"G:\ds-h\_xexp\_tmp")
GIT = r"C:\Program Files\Git\cmd\git.exe"
NL = "\n"

HOLDOUT_DEF = [
    dict(id="H-01", file="src/cdm/domain_validate.py",
         from_="    elif struct.structure_type not in STRUCTURE_TYPES:",
         to="    elif struct.structure_type not in STRUCTURE_TYPES and False:  # H-01 INJECT: 绕过结构类型校验",
         expected="ALARM", desc="越界: 绕过 structure_type 校验"),
    dict(id="H-02", file="tests/cdm/test_domain.py",
         from_="            \"building\", \"floor\", \"axis\", \"zone\", \"structure_unit\",\n        })",
         to="            \"building\", \"floor\", \"axis\", \"zone\", \"structure_unit\",\n        })\n\n\n    def test_holdout_extra(self):\n        # 新增合法测试（合理扩展）\n        assert True",
         expected="OK", desc="合理扩展: 新增测试"),
    dict(id="H-03", file="src/cdm/validate.py",
         from_="def validate_source_ref(sr: SourceRef) -> list[str]:",
         to="_HOLDOUT_UNDOCUMENTED = \"injected\"  # H-03 INJECT: 未文档化常量\n\n\ndef validate_source_ref(sr: SourceRef) -> list[str]:",
         expected="UNKNOWN", desc="证据不足: 未文档化常量"),
    dict(id="H-04", file="src/cdm/id.py",
         from_="    if not isinstance(raw, str) or not raw.startswith(FACT_ID_PREFIX):\n        return None",
         to="    if not isinstance(raw, str) or not raw.startswith(FACT_ID_PREFIX):\n        return None\n    # H-04 INJECT: 允许 2 段 ID（放宽严格解析）\n    if raw.count(\".\") == 1:\n        raw = raw + \".untyped\"",
         expected="ALARM_HIGH", desc="安全: 放宽 ID 严格解析"),
]

def make_holdout(defn):
    cid = defn["id"]
    rel = defn["file"]
    src = BASE / rel
    tmp = TMP / f"{cid}.py"
    tmp.write_bytes(src.read_bytes())
    content = tmp.read_text(encoding="utf-8")
    if defn["from_"] not in content:
        print(f"FAIL {cid}: anchor not found: {defn['from_'][:60]!r}")
        return False
    content = content.replace(defn["from_"], defn["to"])
    tmp.write_text(content, encoding="utf-8")
    r = subprocess.run([GIT, "diff", "--no-index", "--no-color", str(src), str(tmp)],
                       capture_output=True, encoding="utf-8", errors="replace")
    patch_text = gen_cases.rewrite_paths(r.stdout, rel)
    out_dir = CASES / cid
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "diff.patch").write_text(patch_text, encoding="utf-8")
    (out_dir / "case.json").write_text(
        json.dumps({"id": cid, "expected": defn["expected"], "file": rel,
                    "desc": defn["desc"]}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK {cid} ({defn['desc']})")
    return True

if __name__ == "__main__":
    for d in HOLDOUT_DEF:
        make_holdout(d)
