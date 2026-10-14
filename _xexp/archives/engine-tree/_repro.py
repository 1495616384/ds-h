# 复现 assoc_analyze 对 H2-01/H2-04 diff 的输出（只读，不改文件）
import sys
sys.path.insert(0, r"G:\ds-h\_xexp_dev2")
import detect_x0
from pathlib import Path

BASE = Path(r"G:\ds-h\_xexp\base")
pre_inv = detect_x0.code_inventory(BASE)
idx = detect_x0.build_design_index(BASE)
active = set()
for names in pre_inv.values():
    active |= names

for cid in ["H2-01", "H2-04"]:
    diff = (Path(r"G:\ds-h\_xexp\cases") / cid / "diff.patch").read_text(encoding="utf-8")
    print(f"===== {cid} =====")
    clues = detect_x0.assoc_analyze(BASE, diff, idx, pre_inv)
    print("clues:", [(c[0], c[1]) for c in clues])
    # 提取 + 行和 - 行
    plus = [l[1:] for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++")]
    minus = [l[1:] for l in diff.splitlines() if l.startswith("-") and not l.startswith("---")]
    print("+ 行:", plus)
    print("- 行:", minus)
    # 赋值目标提取（引擎逻辑）
    import re
    added_ids = set()
    for line in plus:
        s = re.sub(r"#.*", "", line).strip()
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*(?::[^=]+)?=", s)
        if m:
            added_ids.add(m.group(1))
    print("引擎提取的 added_ids:", sorted(added_ids))
    for nm in sorted(added_ids):
        print(f"  {nm}: in_code={nm in active}")
