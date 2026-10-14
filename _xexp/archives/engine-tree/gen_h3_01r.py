"""生成 H3-01R 替代案例（相对路径 diff + 前置校验）。

H3-01R：src/eval/__init__.py 从 import 块移除 validate_case 导出
  预期 ALARM（导出缺失；IMPORT_GATE __all__ 完整性检查应捕获）
  与 A-11 不同文件不同符号；与原失败案例 H3-01（cdm/__init__.py）不同文件。
"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, r"G:\ds-h\_xexp")
import gen_cases  # 复用 rewrite_paths（相对路径重写）

BASE = Path(r"G:\ds-h\_xexp\base")
CASES = Path(r"G:\ds-h\_xexp\cases")
TMP = Path(r"G:\ds-h\_xexp\_tmp")
GIT = r"C:\Program Files\Git\cmd\git.exe"

REL = "src/eval/__init__.py"
FROM = "    validate_case,"
TO = "    # H3-01R: 移除 validate_case 导出"


def main():
    cid = "H3-01R"
    src = BASE / REL
    tmp = TMP / f"{cid}.py"
    tmp.write_bytes(src.read_bytes())
    content = tmp.read_text(encoding="utf-8")
    if FROM not in content:
        print(f"FAIL: 锚点未命中 {FROM!r}")
        return 1
    if content.count(FROM) != 1:
        print(f"FAIL: 锚点出现 {content.count(FROM)} 次（需唯一）")
        return 1
    tmp.write_text(content.replace(FROM, TO), encoding="utf-8")

    r = subprocess.run([GIT, "diff", "--no-index", "--no-color", str(src), str(tmp)],
                       capture_output=True, encoding="utf-8", errors="replace")
    patch = gen_cases.rewrite_paths(r.stdout, REL)  # 关键：重写为相对路径

    out_dir = CASES / cid
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "diff.patch").write_text(patch, encoding="utf-8")
    (out_dir / "case.json").write_text(json.dumps(
        {"id": cid, "expected": "ALARM", "file": REL,
         "desc": "eval/__init__.py import 块移除 validate_case 导出"},
        ensure_ascii=False, indent=2), encoding="utf-8")

    print("--- 生成的 diff.patch 头 4 行 ---")
    for line in patch.splitlines()[:4]:
        print(line)
    print(f"patch 字节: {len(patch)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
