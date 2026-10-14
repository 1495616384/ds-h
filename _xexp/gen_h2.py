"""生成 H2 独立 holdout 案例 diff（不修改 detect_x0.py）。"""
import json
import subprocess
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
import gen_cases  # 复用 rewrite_paths

BASE = Path(r"G:\ds-h\_xexp\base")
CASES = Path(r"G:\ds-h\_xexp\cases")
TMP = Path(r"G:\ds-h\_xexp\_tmp")
GIT = r"C:\Program Files\Git\cmd\git.exe"
NL = "\n"

H2_DEF = [
    dict(id="H2-01", file="src/eval/accuracy/tokenizer.py",
         from_="            val = float(number_body)",
         to="            val = float(\"0\" + number_body)  # H2-01: 破坏数值解析",
         expected="ALARM", desc="tokenizer 冻结解析被修改"),
    dict(id="H2-02", file="src/cdm/domain.py",
         from_='"""L3 Domain Objects — engineering semantic entities built from Facts.',
         to='"""L3 Domain Objects — engineering semantic entities built from Facts.\n# H2-02: 追加说明注释（无行为变化）',
         expected="OK", desc="docstring 注释无行为变化"),
    dict(id="H2-03", file="src/eval/accuracy/frozen_round.py",
         from_="from decimal import Decimal, ROUND_HALF_UP",
         to="from decimal import Decimal, ROUND_HALF_UP\n\nLEGACY_ROUND_MODE = \"banker\"  # H2-03: 未文档化常量",
         expected="UNKNOWN", desc="未文档化新增常量"),
    dict(id="H2-04", file="src/cdm/domain_validate.py",
         from_='    e = _check_id_non_empty("Defect", defect.id)',
         to='    e = _check_id_non_empty("Defect", str(defect.id))  # H2-04: 放宽 id 校验',
         expected="ALARM_HIGH", desc="放宽 Defect id 校验"),
]


def make(defn):
    cid = defn["id"]
    rel = defn["file"]
    src = BASE / rel
    tmp = TMP / f"{cid}.py"
    if not src.exists():
        print(f"FAIL {cid}: 源文件不存在 {rel}")
        return
    tmp.write_bytes(src.read_bytes())
    content = tmp.read_text(encoding="utf-8")
    if defn["from_"] not in content:
        print(f"FAIL {cid}: 锚点未命中: {defn['from_'][:60]!r}")
        return
    content = content.replace(defn["from_"], defn["to"])
    tmp.write_text(content, encoding="utf-8")
    r = subprocess.run([GIT, "diff", "--no-index", "--no-color", str(src), str(tmp)],
                       capture_output=True, encoding="utf-8", errors="replace")
    patch = gen_cases.rewrite_paths(r.stdout, rel)
    out_dir = CASES / cid
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "diff.patch").write_text(patch, encoding="utf-8")
    (out_dir / "case.json").write_text(
        json.dumps({"id": cid, "expected": defn["expected"], "file": rel,
                    "desc": defn["desc"]}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK {cid} ({defn['desc']}) patch={len(patch)}B")


if __name__ == "__main__":
    TMP.mkdir(parents=True, exist_ok=True)
    CASES.mkdir(parents=True, exist_ok=True)
    for d in H2_DEF:
        make(d)
