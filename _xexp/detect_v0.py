"""工具组合版 X v0 — 阶段一检测引擎（对照基线）。

用途：对注入案例跑确定性检测，输出五标签 + 证据链。
被测对象身份：工具组合版 X v0（pytest + import 检查 + 冻结值域检查 + 行为回归，无自有关联/偏差模型）。

检测信号：
  1. IMPORT_GATE   — 全量 import src 包（捕获 __all__/导出不一致，镜像 RuleStatus 类缺陷）
  2. REGISTRY_GATE — 冻结值域检查（cdm/registry.py 的 SCOPE_CLASSES/METHODS/PROVENANCES 必须与 CDM 文档一致）
  3. PYTEST_GATE   — 全量 pytest（排除已知收集失败文件），比较通过数是否回归
  4. LINT_GATE     — 疑似凭据/敏感模式扫描

输出标签规则（确定性，无语义推断）：
  - PYTEST_GATE 失败或 IMPORT_GATE 失败 → ALARM
  - REGISTRY_GATE 失败（冻结值域被改）→ ALARM（更高置信）
  - LINT_GATE 命中凭据模式 → ALARM_HIGH
  - 全部通过 → OK
  - （工具组合版**不能**产生 LOW_CONF / UNKNOWN —— 这是工具组合版与 X 最小原型的已知差距，如实记录）

用法：python detect_v0.py <case_dir>
  case_dir 内含 diff.patch（相对 base/ 的改动）与 case.json（预期标签等元数据）。
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

BASE = Path(r"G:\ds-h\_xexp\base")
VENV_PY = r"G:\workspace\.venv-zixun4\Scripts\python.exe"
KNOWN_COLLECT_FAIL = ["tests/eval/test_validator_framework.py"]
BASELINE_PASS = 273  # HEAD 冻结基线实测
FROZEN_SCOPE = {"project", "building", "component", "defect", "point", "sample", "material"}
FROZEN_METHODS = {"measured", "observed", "computed", "quoted", "inferred"}
FROZEN_PROV = {"program", "ai", "human"}
CRED_RE = re.compile(r"(sk-(?:proj-)?[A-Za-z0-9]{16,}|api[_-]?key\s*=\s*['\"][^'\"]{12,}|password\s*=\s*['\"][^'\"]{8,})", re.I)


def run(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, encoding="utf-8",
                          errors="replace", timeout=120)


def check_import_gate():
    """全量导入 src 下所有模块（cwd=src 使包可导入），并校验 __all__ 完整性。"""
    failures = []
    src_dir = BASE / "src"
    for py in sorted(src_dir.rglob("*.py")):
        if py.name == "__init__.py":
            continue
        rel = py.relative_to(src_dir)
        mod = ".".join(rel.with_suffix("").parts)
        p = run([VENV_PY, "-c", f"import {mod}"], src_dir)
        if p.returncode != 0:
            tail = (p.stderr or "").strip().splitlines()[-1:] or [""]
            failures.append(f"{mod}: {tail[0]}")
            continue
        # __all__ 完整性：验证 __all__ 中每个名字在模块命名空间存在
        script = (
            f"import importlib; m = importlib.import_module('{mod}'); "
            f"missing = [n for n in getattr(m, '__all__', []) if not hasattr(m, n)]; "
            f"assert not missing, f'missing from module: {{missing}}'"
        )
        p2 = run([VENV_PY, "-c", script], src_dir)
        if p2.returncode != 0:
            tail = (p2.stderr or "").strip().splitlines()[-1:] or [""]
            failures.append(f"{mod}.__all__: {tail[0]}")
    return failures


def check_registry_gate():
    """验证 cdm/registry.py 冻结值域未被改动。"""
    src = (BASE / "src" / "cdm" / "registry.py").read_text(encoding="utf-8", errors="replace")
    issues = []
    # 提取 SCOPE_CLASSES 集合
    m = re.search(r"SCOPE_CLASSES:.*?frozenset\(\{.*?\}\)", src, re.S)
    if m:
        vals = set(re.findall(r'"([a-z_]+)"', m.group(0)))
        if vals != FROZEN_SCOPE:
            issues.append(f"SCOPE_CLASSES 变更: {sorted(vals)}")
    m = re.search(r"METHODS:.*?frozenset\(\{.*?\}\)", src, re.S)
    if m:
        vals = set(re.findall(r'"([a-z_]+)"', m.group(0)))
        if vals != FROZEN_METHODS:
            issues.append(f"METHODS 变更: {sorted(vals)}")
    m = re.search(r"PROVENANCES:.*?frozenset\(\{.*?\}\)", src, re.S)
    if m:
        vals = set(re.findall(r'"([a-z_]+)"', m.group(0)))
        if vals != FROZEN_PROV:
            issues.append(f"PROVENANCES 变更: {sorted(vals)}")
    return issues


def check_pytest_gate():
    """全量 pytest，返回通过数。"""
    ignore_args = []
    for f in KNOWN_COLLECT_FAIL:
        ignore_args += ["--ignore", f]
    p = run([VENV_PY, "-m", "pytest", "-q", *ignore_args], BASE)
    out = (p.stdout or "") + (p.stderr or "")
    m = re.search(r"(\d+) passed", out)
    passed = int(m.group(1)) if m else 0
    failed = "failed" in out.lower()
    return passed, failed, out.splitlines()[-3:]


def check_lint_gate():
    """扫描疑似凭据/敏感模式。"""
    hits = []
    for py in sorted((BASE / "src").rglob("*.py")):
        for i, line in enumerate(py.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if CRED_RE.search(line):
                hits.append(f"{py.relative_to(BASE)}:{i}")
    return hits


def main():
    case_dir = Path(sys.argv[1])
    meta = json.loads((case_dir / "case.json").read_text(encoding="utf-8"))
    case_id = meta["id"]
    expected = meta.get("expected", "?")
    print(f"\n===== 案例 {case_id} (预期={expected}) =====")

    # 应用 diff（一次性，之后回滚）
    patch = case_dir / "diff.patch"
    patch_arg = str(patch.resolve()).replace("\\", "/")
    if patch.exists():
        # git apply --check 先验证
        ck = run([r"C:\Program Files\Git\cmd\git.exe", "apply", "--check", patch_arg], BASE)
        if ck.returncode != 0:
            print(f"[APPLY FAIL] {ck.stderr.strip()[:300]}")
            return
        run([r"C:\Program Files\Git\cmd\git.exe", "apply", patch_arg], BASE)

    try:
        imp_fail = check_import_gate()
        reg_issues = check_registry_gate()
        passed, failed, tail = check_pytest_gate()
        lint_hits = check_lint_gate()

        # 证据
        evidence = []
        if reg_issues:
            evidence.append(f"REGISTRY_GATE: {'; '.join(reg_issues)}")
        if imp_fail:
            evidence.append(f"IMPORT_GATE: {len(imp_fail)} 失败 e.g. {imp_fail[0][:80]}")
        evidence.append(f"PYTEST_GATE: {passed} passed (基线 {BASELINE_PASS})")
        if lint_hits:
            evidence.append(f"LINT_GATE: {len(lint_hits)} 命中 e.g. {lint_hits[0]}")

        # 判定
        label = "OK"
        if lint_hits:
            label = "ALARM_HIGH"
        elif reg_issues or imp_fail:
            label = "ALARM"
        elif passed < BASELINE_PASS:
            label = "ALARM"
        print(f"判定: {label}")
        print(f"证据: " + " | ".join(evidence))
        print(f"工具组合版能力边界: 输出 {label}（LOW_CONF/UNKNOWN 非本对象可产出的语义）")
        print(f"正确性: {'✅ 与预期一致' if label == expected else '❌ 与预期不一致'}")
    finally:
        # 回滚（--hard 确保干净恢复）
        run([r"C:\Program Files\Git\cmd\git.exe", "checkout", "--", "."], BASE)
        run([r"C:\Program Files\Git\cmd\git.exe", "clean", "-fd", "."], BASE)


if __name__ == "__main__":
    main()
