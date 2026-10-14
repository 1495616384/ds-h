"""X 引擎回归测试（H2 缺陷修复验证）。

覆盖：
  1. H2-01/H2-04：不再因假性 undocumented 判 UNKNOWN（修复 1）
  2. H2-01/H2-04：冻结模块修改检测 → ALARM/ALARM_HIGH（修复 2）
  3. H2-02/H2-03：不破坏正确案例
  4. 既有 20 案例：无回归

注意：本测试是开发阶段回归，H2 独立验证结论（2/4 未通过）不变。
"""
import json
import subprocess
import sys
from pathlib import Path

ENGINE = Path(__file__).parent / "detect_x0.py"
PY = r"G:\workspace\.venv-zixun4\Scripts\python.exe"
CASES = Path(r"G:\ds-h\_xexp\cases")

ALL_CASES = [
    "A-01","A-02","A-03","B-01","B-02","C-01","E-01","F-01",
    "A-11","A-12","B-11","B-12","C-11","E-11","F-11","G-11",
    "H-01","H-02","H-03","H-04",
    "H2-01","H2-02","H2-03","H2-04",
]


def run_case(cid: str):
    out = subprocess.run(
        [PY, str(ENGINE), str(CASES / cid)],
        capture_output=True, encoding="utf-8", errors="replace")
    label = ""
    for line in out.stdout.splitlines():
        if line.startswith("判定: "):
            label = line.replace("判定: ", "").strip()
            break
    exp = json.loads((CASES / cid / "case.json").read_text(encoding="utf-8"))["expected"]
    return label, exp, out.returncode


def run_fixture_error_case(cid: str):
    """fixture 错误案例：补丁无法应用 → 引擎必须以非零退出码结束并在 stderr 报错。"""
    out = subprocess.run(
        [PY, str(ENGINE), str(CASES / cid)],
        capture_output=True, encoding="utf-8", errors="replace")
    return out.returncode, out.stderr


def main():
    results = []
    for cid in ALL_CASES:
        label, exp, rc = run_case(cid)
        ok = (label == exp) and (rc == 0)
        results.append((cid, exp, label, rc, ok))
        print(f"{cid}: exp={exp} got={label} rc={rc} {'OK' if ok else 'FAIL'}")

    passed = sum(1 for r in results if r[4])
    total = len(results)
    print(f"\n=== 回归结果: {passed}/{total} ===")

    # fixture 错误处理测试（不计入检测成绩）
    print("\n=== fixture 错误处理测试（此测试不计入检测成绩）===")
    fixt_ok = True
    if (CASES / "H3-01" / "diff.patch").exists():
        rc, err = run_fixture_error_case("H3-01")  # 绝对路径补丁，预期无法应用
        has_marker = "INCONCLUSIVE_FIXTURE_ERROR" in err
        ok = (rc == 2) and has_marker
        print(f"H3-01(fixture错误样本): rc={rc} (期望2) stderr含标记={has_marker} "
              f"{'OK' if ok else 'FAIL'}")
        fixt_ok = fixt_ok and ok
    else:
        print("H3-01 fixture 样本不存在，跳过")

    if passed != total or not fixt_ok:
        fails = [r[0] for r in results if not r[4]]
        if fails:
            print("FAILED:", ", ".join(fails))
        sys.exit(1)
    print("\n全部通过（开发阶段回归；H2 独立验证结论不变）")


if __name__ == "__main__":
    main()
