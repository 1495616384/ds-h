"""生成阶段一案例 patch（相对路径、真实换行）。"""
import json
import subprocess
from pathlib import Path

BASE = Path(r"G:\ds-h\_xexp\base")
CASES = Path(r"G:\ds-h\_xexp\cases")
TMP = Path(r"G:\ds-h\_xexp\_tmp")
GIT = r"C:\Program Files\Git\cmd\git.exe"

NL = "\n"

CASES_DEF = [
    dict(id="A-01", file="src/cdm/registry.py",
         from_='"project",\n    "building",',
         to='"project",\n    "structure",\n    "building",',
         expected="ALARM", desc="越界注入 structure"),
    dict(id="A-02", file="src/eval/accuracy/binding.py",
         from_="    return token_start >= decl_start and token_end <= decl_end",
         to="    return token_start >= decl_start or token_end <= decl_end  # INJECT: 边界放宽",
         expected="ALARM", desc="越界: 放宽 span 包含判定"),
    dict(id="A-03", file="src/cdm/id.py",
         from_='FACT_ID_PREFIX = "fact:"',
         to='FACT_ID_PREFIX = "fact:"\n\n# 注入：宽松前缀（绕过校验）\nFACT_ID_PREFIX_LOOSE = "fct:"',
         expected="ALARM_HIGH", desc="安全注入宽松前缀"),
    dict(id="B-01", file="tests/eval/test_loader.py",
         from_="    assert case.meta.case_level == \"bronze\"",
         to="    assert case.meta.case_level == \"bronze\"\n\n\ndef test_extra_fixture_case():\n    # 新增合法测试（不触碰 src/）\n    assert True",
         expected="OK", desc="合理扩展: 新增测试用例"),
    dict(id="B-02", file="src/eval/enums.py",
         from_="# KnownIssue types (Step 7-D v4 coding contract)",
         to="# KnownIssue types (Step 7-D v4 coding contract)\nEXTRA_TAGS: frozenset[str] = frozenset({\"reviewed\"})  # 扩展：独立新枚举",
         expected="OK", desc="合理扩展新增枚举"),
    dict(id="C-01", file="src/cdm/registry.py",
         from_="# §13 — where did this fact come from",
         to="# §13 — where did this fact come from\n# (注: 声称来自 §14 但 CDM v0.3 §14 无此定义)\nFAKE_S14 = {\"external\"}",
         expected="LOW_CONF", desc="自监督: 伪造 §14 引用"),
    dict(id="E-01", file="src/eval/types.py",
         from_="from __future__ import annotations",
         to="from __future__ import annotations\n\n# INJECT-E01: 未在任何契约出现的字段引用\nUNDOCUMENTED_FIELD: str = \"injected\"",
         expected="UNKNOWN", desc="证据不足: 未文档化字段"),
    dict(id="F-01", file="src/cdm/domain.py",
         from_="    project_id is REQUIRED — the Project → Structure relation must be",
         to="    project_id is REQUIRED — the Project → Structure relation must be\n    # (F-01 注入：示例注释，无行为变化)",
         expected="OK", desc="无关注释微调"),
]


def rewrite_paths(patch_text: str, rel: str) -> str:
    """把 --no-index 生成的绝对 a/b 路径改写成相对 base 的 a/rel b/rel。"""
    lines = []
    for line in patch_text.splitlines():
        if line.startswith("diff --git "):
            lines.append(f"diff --git a/{rel} b/{rel}")
        elif line.startswith("index "):
            lines.append(line)  # 保留 index 行
        elif line.startswith('--- '):
            lines.append(f"--- a/{rel}")
        elif line.startswith('+++ '):
            lines.append(f"+++ b/{rel}")
        else:
            lines.append(line)
    return "\n".join(lines) + "\n"


INDEP_DEF = [
    dict(id="A-11", file="src/eval/accuracy/__init__.py",
         from_="    bind_and_validate,\n    bind_table_cell,\n    bind_rendered_segment,",
         to="    bind_and_validate,\n    bind_rendered_segment,  # INJECT: 移除 bind_table_cell 导入（镜像 RuleStatus 缺陷模式）",
         expected="ALARM", desc="镜像 RuleStatus 缺陷: 移除 import"),
    dict(id="A-12", file="src/eval/accuracy/binding.py",
         from_="    fact_ids = {d.fact_id for d in declarations}\n    return len(fact_ids) > 1",
         to="    fact_ids = {d.fact_id for d in declarations}\n    return len(fact_ids) > 0  # INJECT: 放宽重复判定",
         expected="ALARM_HIGH", desc="放宽重复 fact 判定"),
    dict(id="B-11", file="src/eval/validator.py",
         from_="    return errors",
         to="    return errors\n\n\ndef helper_conclusion_summary(case):\n    # 新增辅助函数（无契约违反，合法扩展）\n    return getattr(case, \"conclusion\", None)",
         expected="OK", desc="合理扩展: 新增辅助函数"),
    dict(id="B-12", file="tests/eval/test_loader.py",
         from_="    assert case.meta.case_level == \"bronze\"",
         to="    assert case.meta.case_level == \"bronze\"\n\n\ndef test_extra_fixture_meta():\n    # 新增合法 fixture 元数据测试（不触碰 src/）\n    assert True",
         expected="OK", desc="合理扩展: 新增 fixture 测试"),
    dict(id="C-11", file="src/eval/accuracy/data_structures.py",
         from_="@dataclass\nclass AnchorDeclaration:",
         to="@dataclass\nclass AnchorDeclaration:\n    # INJECT-C11: 自监督悬空引用（getattr 引用已移除符号，不破坏 import）\n    _STALE_REF = getattr(object, \"removed_v2\", None)",
         expected="LOW_CONF", desc="自监督: 悬空引用已移除符号"),
    dict(id="E-11", file="src/eval/validator.py",
         from_="    return errors",
         to="    retry_policy = \"default\"  # INJECT-E11: 无契约参数\n    return errors",
         expected="UNKNOWN", desc="证据不足: 无契约参数"),
    dict(id="F-11", file="src/cdm/types.py",
         from_="from typing import Any, Optional, Union",
         to="from typing import Any, Optional, Union  # F-11: import 微调",
         expected="OK", desc="无关: import 微调"),
    dict(id="G-11", file="src/eval/accuracy/binding.py",
         from_='    fact_ids = {d.fact_id for d in declarations}\n    return len(fact_ids) > 1',
         to='    fact_ids = {d.fact_id for d in declarations}\n    API_TOKEN = "sk-proj-0123456789abcdef0123456789abcdef"  # INJECT: 明文凭据\n    return len(fact_ids) > 1',
         expected="ALARM_HIGH", desc="硬编码明文凭据"),
]


def make_case(defn: dict):
    cid = defn["id"]
    rel = defn["file"]
    src = BASE / rel
    tmp = TMP / f"{cid}.py"
    tmp.write_bytes(src.read_bytes())  # 复制原始字节（保留编码）
    content = tmp.read_text(encoding="utf-8")
    if defn["from_"] not in content:
        print(f"❌ {cid} 未命中: {defn['from_'][:50]!r}")
        return False
    content = content.replace(defn["from_"], defn["to"])
    tmp.write_text(content, encoding="utf-8")
    r = subprocess.run([GIT, "diff", "--no-index", "--no-color",
                        str(src), str(tmp)],
                       capture_output=True, encoding="utf-8", errors="replace")
    patch_text = rewrite_paths(r.stdout, rel)
    out_dir = CASES / cid
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "diff.patch").write_text(patch_text, encoding="utf-8")
    (out_dir / "case.json").write_text(
        json.dumps({"id": cid, "expected": defn["expected"], "file": rel,
                    "desc": defn["desc"]}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    print(f"✅ {cid} ({defn['desc']}) patch={len(patch_text)}B")
    return True


if __name__ == "__main__":
    TMP.mkdir(parents=True, exist_ok=True)
    CASES.mkdir(parents=True, exist_ok=True)
    for d in CASES_DEF:
        make_case(d)
