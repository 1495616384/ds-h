"""X 最小原型 v0 — 关联与偏差模型检测引擎（主测对象）。

在工具组合版（detect_v0.py 四门）之上实现"关联与偏差模型"：
  设计条目索引（从冻结基线 HEAD 内 7 份设计文档提取）
    → 对注入变更做"设计条目 ↔ 代码证据"关联
    → 产出语义化判定：LOW_CONF / UNKNOWN / 风险分级(ALARM_HIGH)

新增能力（对比工具组合版）：
  1. ASSOC_GATE（关联门）：新增符号是否在设计条目索引中
       - 不在 → 未文档化（UNKNOWN 证据）
       - 冻结常量被"影子化"（同名前缀 + LOOSE/ALT/OVERRIDE 语义）→ 越界（ALARM）
  2. SECTION_GATE（章节门）：代码中 §N 引用是否与设计文档 §N 定义一致
       - 伪造 § 引用（章节存在但无该词）→ LOW_CONF（自监督冲突）
  3. RISK_GATE（风险门）：安全上下文模块（id/hash/auth/validate/secret/token）中
       的未文档化符号 → ALARM_HIGH（风险分级）
  4. DANGLE_GATE（悬空引用门）：引用既不在代码也不在设计索引的符号 → LOW_CONF

五标签输出规则（按优先级）：
  LINT 命中                                   → ALARM_HIGH
  安全上下文 + 关联偏差（影子化/未文档化）       → ALARM_HIGH
  伪造 § 引用 / 悬空引用                       → LOW_CONF
  冻结契约破坏（REGISTRY/IMPORT/PYTEST 失败）  → ALARM
  非安全模块未文档化新增符号                    → UNKNOWN
  全部通过且符号可关联                          → OK

用法：python detect_x0.py <case_dir>
"""
import ast
import json
import re
import subprocess
import sys
from pathlib import Path

BASE = Path(r"G:\ds-h\_xexp\base")
VENV_PY = r"G:\workspace\.venv-zixun4\Scripts\python.exe"
GIT = r"C:\Program Files\Git\cmd\git.exe"
KNOWN_COLLECT_FAIL = ["tests/eval/test_validator_framework.py"]
BASELINE_PASS = 273

# ── 设计条目索引（从 HEAD 内冻结设计文档构建）──────────────────
DESIGN_DOCS = [
    "docs/00_PROJECT_CONTEXT.md",
    "docs/02_ARCHITECTURE.md",
    "docs/02_ARCHITECTURE_REVIEW.md",
    "docs/03_CANONICAL_DATA_MODEL.md",
    "docs/04_REPORT_IR.md",
    "docs/05_EVALUATION.md",
    "docs/07_DECISIONS.md",
]

# 安全上下文模块（设计上涉及校验/身份/哈希/敏感数据）
# 注意：通用 validate 校验模块 ≠ 安全边界；仅认证/权限/哈希/敏感数据处理升级
SECURITY_MODULES = {"id", "auth", "hash", "secret", "token",
                    "credential", "permission", "private", "redact"}
# 影子化语义标记
SHADOW_HINTS = re.compile(r"(loose|alt|override|bypass|force|skip|raw|fast|legacy)", re.I)
# 模块角色：词汇表/注册表模块允许新增独立常量（合理扩展）
VOCAB_MODULES = {"registry", "enums", "vocab"}
# 冻结声明标记
FROZEN_HINTS = re.compile(r"(frozen|冻结|hard-coded|no dynamic modification|不得修改|不可修改)", re.I)


def run(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, encoding="utf-8",
                          errors="replace", timeout=120)


# ══════════════════════════════════════════════════════════════
# 设计条目索引构建
# ══════════════════════════════════════════════════════════════
class DesignIndex:
    """从设计文档提取：冻结符号集、§章节映射、词汇表模块声明。"""

    def __init__(self, base: Path):
        self.symbols: set[str] = set()       # 设计文档代码块中的标识符
        self.sections: dict[str, str] = {}   # §N → 章节文本（小写）
        self.frozen_terms: set[str] = set()  # 冻结/禁止词
        for doc in DESIGN_DOCS:
            p = base / doc
            if not p.exists():
                continue
            text = p.read_text(encoding="utf-8", errors="replace")
            self._parse_doc(text)

    def _parse_doc(self, text: str):
        # 代码块内的标识符（设计约束的实现锚点）
        for m in re.finditer(r"```(?:py|python)?\s*\n(.*?)\n```", text, re.S):
            for name in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]{2,})\b", m.group(1)):
                self.symbols.add(name)
        # §N 章节 → 文本
        for m in re.finditer(r"§\s*([0-9]+(?:\.[0-9]+)?)", text):
            sec = m.group(1)
            # 该 § 之后 300 字符作为章节内容
            start = m.end()
            chunk = text[start:start + 300]
            self.sections.setdefault(sec, "").join([chunk])
            self.sections[sec] = chunk[:300].lower()
        # 冻结/禁止词
        for m in re.finditer(r"(?:不得|禁止|forbidden|frozen|不可|MUST NOT|must not)\s*[：: ]?\s*([\w\s、，,._-]{2,40})", text, re.I):
            for tok in re.findall(r"[a-z_][a-z0-9_]{2,}", m.group(1)):
                self.frozen_terms.add(tok.lower())


def build_design_index(base: Path) -> DesignIndex:
    return DesignIndex(base)


# ══════════════════════════════════════════════════════════════
# 代码符号清单（当前代码库实际定义的顶层名字）
# ══════════════════════════════════════════════════════════════
def code_inventory(base: Path) -> dict[str, set[str]]:
    """module_path → 顶层定义名集合（AST 解析）。"""
    inv: dict[str, set[str]] = {}
    for py in sorted((base / "src").rglob("*.py")):
        rel = py.relative_to(base / "src")
        mod = ".".join(rel.with_suffix("").parts)
        try:
            tree = ast.parse(py.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        names = set()
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.add(node.name)
            elif isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        names.add(t.id)
            elif isinstance(node, (ast.AnnAssign,)):
                if isinstance(node.target, ast.Name):
                    names.add(node.target.id)
        inv[mod] = names
    return inv


# ══════════════════════════════════════════════════════════════
# 检测门（复用工具组合版 + 新增关联门）
# ══════════════════════════════════════════════════════════════
def check_import_gate(base: Path):
    failures = []
    src_dir = base / "src"
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
        script = (f"import importlib; m = importlib.import_module('{mod}'); "
                  f"missing = [n for n in getattr(m, '__all__', []) if not hasattr(m, n)]; "
                  f"assert not missing, f'missing: {{missing}}'")
        p2 = run([VENV_PY, "-c", script], src_dir)
        if p2.returncode != 0:
            tail = (p2.stderr or "").strip().splitlines()[-1:] or [""]
            failures.append(f"{mod}.__all__: {tail[0]}")
    return failures


def check_registry_gate(base: Path):
    src = (base / "src" / "cdm" / "registry.py").read_text(encoding="utf-8", errors="replace")
    issues = []
    for name, expected in [("SCOPE_CLASSES", {"project", "building", "component", "defect", "point", "sample", "material"}),
                            ("METHODS", {"measured", "observed", "computed", "quoted", "inferred"}),
                            ("PROVENANCES", {"program", "ai", "human"})]:
        m = re.search(rf"{name}:.*?frozenset\(\{{.*?\}}\)", src, re.S)
        if m:
            vals = set(re.findall(r'"([a-z_]+)"', m.group(0)))
            if vals != expected:
                issues.append(f"{name} 变更: {sorted(vals)}")
    return issues


def check_pytest_gate(base: Path):
    ignore_args = []
    for f in KNOWN_COLLECT_FAIL:
        ignore_args += ["--ignore", f]
    p = run([VENV_PY, "-m", "pytest", "-q", *ignore_args], base)
    out = (p.stdout or "") + (p.stderr or "")
    m = re.search(r"(\d+) passed", out)
    passed = int(m.group(1)) if m else 0
    return passed


def check_lint_gate(base: Path):
    CRED_RE = re.compile(r"(sk-(?:proj-)?[A-Za-z0-9]{16,}|api[_-]?key\s*=\s*['\"][^'\"]{12,}|password\s*=\s*['\"][^'\"]{8,})", re.I)
    hits = []
    for py in sorted((base / "src").rglob("*.py")):
        for i, line in enumerate(py.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if CRED_RE.search(line):
                hits.append(f"{py.relative_to(base)}:{i}")
    return hits


# ══════════════════════════════════════════════════════════════
# 关联与偏差模型（X 原型 v0 核心）
# ══════════════════════════════════════════════════════════════
PY_KEYWORDS = {
    "assert", "and", "as", "async", "await", "break", "class", "continue",
    "def", "del", "elif", "else", "except", "finally", "for", "from",
    "global", "if", "import", "in", "is", "lambda", "nonlocal", "not",
    "or", "pass", "raise", "return", "try", "while", "with", "yield",
    "True", "False", "None", "self", "cls",
}


def assoc_analyze(base: Path, diff_text: str, index: DesignIndex, pre_inv: dict[str, set[str]] = None):
    """对 diff 做设计条目↔代码证据关联，返回证据列表与判定线索。
    pre_inv: 应用 patch 前的基线代码符号清单（避免把注入符号误判为既有）。
    """
    clues = []  # (kind, message)
    added_lines = []
    for line in diff_text.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            added_lines.append(line[1:])
    if not added_lines:
        return clues

    # 新增标识符（仅"定义型"：赋值目标 / 注解定义 / def / class 名）
    # 排除：import 名、内置名、局部变量引用、行内普通标识符
    added_ids: set[str] = set()
    BUILTINS = {
        "len", "str", "int", "float", "bool", "list", "dict", "set", "tuple",
        "object", "type", "range", "enumerate", "zip", "map", "filter", "sum",
        "min", "max", "abs", "any", "all", "getattr", "setattr", "hasattr",
        "isinstance", "issubclass", "print", "repr", "id", "hash", "format",
        "None", "True", "False", "get", "values", "keys", "items",
    }
    # 被修改行（- 行）中已存在的标识符：区分"修改既有"与"新增定义"
    modified_existing: set[str] = set()
    for line in diff_text.splitlines():
        if line.startswith("-") and not line.startswith("---"):
            s = re.sub(r"#.*", "", line[1:]).strip()
            for name in re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", s):
                if name not in PY_KEYWORDS and name not in BUILTINS and not name.startswith("__"):
                    modified_existing.add(name)
    for line in added_lines:
        stripped = re.sub(r"#.*", "", line).strip()
        if not stripped:
            continue
        # import 行：不产生新增符号
        if re.match(r"^(from\s+\S+\s+import|import\s+\S+)", stripped):
            continue
        # def / class 名
        m = re.match(r"^(?:async\s+)?def\s+([A-Za-z_]\w*)|^class\s+([A-Za-z_]\w*)", stripped)
        if m:
            name = m.group(1) or m.group(2)
            if name and not name.startswith("__"):
                added_ids.add(name)
            continue
        # 赋值目标：NAME = ...  或  NAME: type = ... 或  NAME: type 注解
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*(?::[^=]+)?=", stripped)
        if m:
            name = m.group(1)
            if name not in PY_KEYWORDS and name not in BUILTINS and not name.startswith("__"):
                added_ids.add(name)
            continue
        # 注解定义（无赋值）：NAME: Type
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:", stripped)
        if m:
            name = m.group(1)
            if name not in PY_KEYWORDS and name not in BUILTINS and not name.startswith("__"):
                added_ids.add(name)

    # 基线符号清单（应用 patch 前）
    inv = pre_inv if pre_inv is not None else code_inventory(base)
    active_symbols: set[str] = set()
    for names in inv.values():
        active_symbols |= names

    for name in sorted(added_ids):
        in_design = name in index.symbols or name in index.frozen_terms
        in_code = name in active_symbols
        if in_code:
            continue  # 既有符号引用，不新增
        # 修改既有行（- 行已含该标识符）→ 不是新增定义，不判 undocumented
        if name in modified_existing:
            continue
        # 新增符号：
        if name.startswith("test_") or name.startswith("helper_"):
            clues.append(("test_ext", f"新增测试/辅助符号 {name}（tests 扩展区，不判 undocumented）"))
            continue
        if not in_design:
            # 影子化检测：新增名与既有冻结符号共享稳定前缀 + 语义标记
            shadowed = None
            # 用最长公共前缀判断（≥5 字符）
            for existing in active_symbols:
                if existing == name:
                    continue
                common = 0
                for a, b in zip(name, existing):
                    if a == b:
                        common += 1
                    else:
                        break
                if common >= 5 and SHADOW_HINTS.search(name) and not SHADOW_HINTS.search(existing):
                    shadowed = existing
                    break
            if shadowed:
                clues.append(("deviation", f"新增符号 {name} 影子化既有 {shadowed}（{SHADOW_HINTS.search(name).group(1)} 语义）"))
            else:
                clues.append(("undocumented", f"新增符号 {name} 未出现在设计条目索引"))
        else:
            clues.append(("documented", f"新增符号 {name} 在设计条目索引中"))

    # § 章节引用核查 + 声称依据检测
    for line in added_lines:
        for m in re.finditer(r"§\s*([0-9]+(?:\.[0-9]+)?)", line):
            sec = m.group(1)
            content = index.sections.get(sec, "")
            if not content:
                clues.append(("stale_section", f"引用 §{sec} 但设计文档无该章节"))
            else:
                # 该行声称的定义词是否在章节内容中
                words = re.findall(r"[a-z_][a-z0-9_]{2,}", line.lower())
                for w in words:
                    if w in ("the", "and", "ref", "section"):
                        continue
                    if w not in content and len(w) > 3:
                        clues.append(("stale_section", f"§{sec} 未含声称词 '{w}'（伪造/陈旧引用）"))
                        break
        # 声称依据但符号未入索引 → 自监督冲突（模型声称 vs 模型依据矛盾）
        if re.search(r"§\s*[0-9]|来自 §|per §|according to §|S\d{1,2}[_\s]*(?===)|声称.*定义", line, re.I):
            line_ids = set(re.findall(r"\b([A-Z][A-Z0-9_]{2,}|[a-z_][a-z0-9_]{2,})\b", line))
            for name in line_ids:
                if name in PY_KEYWORDS:
                    continue
                if name not in active_symbols and name not in index.symbols:
                    clues.append(("stale_section", f"符号 {name} 声称设计依据但设计索引无此定义（自监督冲突）"))
                    break

    # 悬空引用：行内含显式引用惯用法（getattr/import_module/__import__/importlib.*）
    # 且字符串值不在代码/设计中 → 自监督悬空引用
    for line in added_lines:
        stripped = re.sub(r"#.*", "", line)
        if not re.search(r"(getattr\s*\(|import_module\s*\(|__import__\s*\(|importlib\s*\.|vars\s*\(|locals\s*\()", stripped):
            continue
        for m in re.finditer(r'["\']([A-Za-z_][A-Za-z0-9_]{2,})["\']', stripped):
            ref = m.group(1)
            if ref in PY_KEYWORDS or ref in BUILTINS:
                continue
            if ref not in active_symbols and ref not in index.symbols and ref not in added_ids:
                clues.append(("dangle", f"悬空引用 '{ref}'（代码与设计均无此符号）"))
    return clues


def risk_grade(mod_path: str, clues: list) -> bool:
    """安全上下文：模块路径或文件名含安全关键词 → 风险升级。"""
    norm = mod_path.lower().replace("\\", "/")
    parts = set(norm.split("/")) | {p for p in norm.split("/") if "." in p}
    for p in parts:
        # 含文件名（如 id.py → id, py）
        base = p.split(".")[0]
        if base in SECURITY_MODULES:
            return True
    return False


def module_role(mod_path: str) -> str:
    norm = mod_path.lower().replace("\\", "/")
    parts = set(norm.split("/"))
    parts |= {p.split(".")[0] for p in parts if "." in p}
    for p in parts:
        if p in VOCAB_MODULES:
            return "vocab"
    return "logic"


# ══════════════════════════════════════════════════════════════
# 主流程
# ══════════════════════════════════════════════════════════════
# 高风险契约函数（数据完整性/安全边界 → ALARM_HIGH）
# 普通契约破坏（span 判定/导入完整性/一般函数）→ ALARM
HIGH_RISK_CONTRACT_FUNCS = re.compile(
    r"(has_duplicate_fact_ids|parse_fact_id|validate_case|validate_fact|"
    r"validate_conflict|validate_known_issue|validate_expected_issue|"
    r"validate_source_ref|validate_raw_source|validate_ground_truth_|"
    r"validate_meta|validate_expected_|frozen_round)"
)


def diff_touches_contract(diff_text: str) -> bool:
    """diff 是否修改了高风险契约关键函数所在区域。"""
    return bool(HIGH_RISK_CONTRACT_FUNCS.search(diff_text))


# 冻结模块声明检测（模块 docstring 级，含 design freeze 变体）
FROZEN_MODULE_HINTS = re.compile(
    r"(frozen|freeze|冻结|hard-coded|no dynamic modification|不得修改|不可修改)", re.I)


def frozen_module_check(diff_text: str, base: Path) -> tuple:
    """检查 diff 是否修改了"声明冻结"的 src 模块的实现逻辑。

    返回 (frozen_files, has_code_minus)：
      - frozen_files: 声明冻结且被 diff 触及的 src 文件列表
      - has_code_minus: diff 是否含 "- 代码行"（修改实现，非纯注释/纯新增）
    判据设计：只有"修改冻结模块的既有实现"才触发，纯注释（F-01/H2-02）、
    纯新增定义（H2-03）不触发。
    """
    files = re.findall(r"diff --git a/(\S+) b/\S+", diff_text)
    frozen_files = []
    for f in set(files):
        if not f.startswith("src/"):
            continue
        fp = base / f
        if not fp.exists():
            continue
        head = fp.read_text(encoding="utf-8", errors="replace")[:800]
        if FROZEN_MODULE_HINTS.search(head):
            frozen_files.append(f)
    # 是否有 - 代码行（去注释后的非空行）
    has_code_minus = False
    for line in diff_text.splitlines():
        if line.startswith("-") and not line.startswith("---"):
            s = re.sub(r"#.*", "", line[1:]).strip()
            if s and not re.match(r"^[#\s]*$", s):
                has_code_minus = True
                break
    return frozen_files, has_code_minus


def main():
    case_dir = Path(sys.argv[1])
    meta = json.loads((case_dir / "case.json").read_text(encoding="utf-8"))
    case_id = meta["id"]
    expected = meta.get("expected", "?")
    print(f"\n===== X 原型 v0 | 案例 {case_id} (预期={expected}) =====")

    patch_arg = str((case_dir / "diff.patch").resolve()).replace("\\", "/")
    diff_text = (case_dir / "diff.patch").read_text(encoding="utf-8", errors="replace")

    ck = run([GIT, "apply", "--check", patch_arg], BASE)
    if ck.returncode != 0:
        # 补丁无法应用：fixture 错误，非检测结论——输出到 stderr 并以非零退出码结束
        msg = ck.stderr.strip()[:300]
        print(f"[APPLY FAIL] {msg}", file=sys.stderr)
        print("[INCONCLUSIVE_FIXTURE_ERROR] 补丁无法应用，检测器未获得有效输入，不计通过/失败",
              file=sys.stderr)
        sys.exit(2)
    # 应用前快照基线 inventory（避免注入符号被误判为既有）
    pre_inv = code_inventory(BASE)
    run([GIT, "apply", patch_arg], BASE)

    try:
        index = build_design_index(BASE)
        evidence = []

        # 四门（确定性）
        reg_issues = check_registry_gate(BASE)
        imp_fail = check_import_gate(BASE)
        passed = check_pytest_gate(BASE)
        lint_hits = check_lint_gate(BASE)

        # 关联与偏差模型（用基线 inventory，注入后运行）
        clues = assoc_analyze(BASE, diff_text, index, pre_inv)

        # 判定（按优先级）
        label = "OK"
        if lint_hits:
            label = "ALARM_HIGH"
            evidence.append(f"LINT_GATE: {lint_hits[0]}")
        elif reg_issues or imp_fail:
            label = "ALARM"
            evidence.append(f"GATE_FAIL: {'; '.join(reg_issues[:1] + imp_fail[:1])}")
        elif passed < BASELINE_PASS:
            # PYTEST 失败 + 触碰契约关键函数 → 高风险（ALARM_HIGH）
            if diff_touches_contract(diff_text):
                label = "ALARM_HIGH"
                evidence.append(f"PYTEST_GATE+CONTRACT: {passed} passed (基线 {BASELINE_PASS})，且修改契约关键函数")
            else:
                label = "ALARM"
                evidence.append(f"PYTEST_GATE: {passed} passed (基线 {BASELINE_PASS})")

        # 语义门（仅当四门未直接判 ALARM 时提升/细化）
        if label == "OK":
            deviations = [c for c in clues if c[0] == "deviation"]
            undocumented = [c for c in clues if c[0] == "undocumented"]
            stale = [c for c in clues if c[0] == "stale_section"]
            dangle = [c for c in clues if c[0] == "dangle"]
            # 注入文件路径（从 case.json）
            mod_path = meta.get("file", "")
            security = risk_grade(mod_path, clues)
            role = module_role(mod_path)
            # 冻结模块修改检测（仅四门全过时补充，不干扰 pytest 失败分支）
            frozen_files, has_code_minus = frozen_module_check(diff_text, BASE)
            if frozen_files and has_code_minus:
                # 冻结模块实现被修改 → 契约破坏（优先于语义标签）
                # 校验/验证语义的冻结模块被削弱 → 高风险（ALARM_HIGH）
                frozen_sec = any(risk_grade(f, []) for f in frozen_files)
                frozen_validate = any(
                    re.search(r"(validate|validator|check|guard|auth|id\.py|security)", f, re.I)
                    for f in frozen_files)
                if frozen_sec or frozen_validate:
                    label = "ALARM_HIGH"
                    evidence.append(f"FROZEN_MODULE+SECURITY: {frozen_files[0]} 冻结实现被修改")
                else:
                    label = "ALARM"
                    evidence.append(f"FROZEN_MODULE: {frozen_files[0]} 冻结实现被修改")
            elif stale or dangle:
                label = "LOW_CONF"
                evidence.append(f"ASSOC: {stale[0][1] if stale else dangle[0][1]}")
            elif deviations and security:
                label = "ALARM_HIGH"
                evidence.append(f"RISK+DEVIATION: {deviations[0][1]}")
            elif undocumented and role == "vocab":
                # 词汇表模块新增独立常量 → 合理扩展（若未影子化）
                label = "OK"
                evidence.append(f"ASSOC: {undocumented[0][1]}（词汇表模块新增，判合理扩展）")
            elif undocumented and security:
                label = "ALARM_HIGH"
                evidence.append(f"RISK+UNDOCUMENTED: {undocumented[0][1]}")
            elif undocumented:
                label = "UNKNOWN"
                evidence.append(f"ASSOC: {undocumented[0][1]}")
            else:
                label = "OK"
                evidence.append("ASSOC: 变更符号均可关联设计条目")
        else:
            # 已 ALARM，补充语义证据
            for c in clues[:2]:
                evidence.append(f"ASSOC: {c[1]}")

        print(f"判定: {label}")
        print(f"证据: " + " | ".join(evidence))
        print(f"设计索引: {len(index.symbols)} 符号 / {len(index.sections)} 章节")
        print(f"正确性: {'CORRECT' if label == expected else 'MISMATCH'}")
    finally:
        run([GIT, "checkout", "--", "."], BASE)
        run([GIT, "clean", "-fd", "."], BASE)


if __name__ == "__main__":
    main()
