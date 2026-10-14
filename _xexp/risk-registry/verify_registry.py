"""RISK-REGISTRY 校验（扩展版 v3）——结构检查 + 一致性 + 绑定 + 待决限制。

覆盖范围（自动可验证）：
  1. 八字段齐备与值域检查
  2. constraint_id 唯一性
  3. required_evidence 的实际来源可访问性（对冻结基线的路径存在性）
  4. change_control / severity / action_policy 一致性
  5. 待决（PENDING）条目的使用限制
  6. 登记表与冻结基线的绑定关系（subject_baseline vs 实测 base HEAD/tree）

v2 -> v3 修正（判定标准未变，仅健壮性）：
  * **F-1 编码崩溃**：GBK 代码页下打印符号会抛 UnicodeEncodeError → 先固定 UTF-8 标准流。
  * **F-5 管道不可用**：受限沙箱禁止建管道，`capture_output=True` 抛
    `PermissionError(WinError 5)`，脚本以退出码 1 崩溃、丢失全部结论
    → 改用 `_xexp/tools/proc_capture.run_captured`（自动回退临时文件重定向）。
  * git 命令失败时**显式报告真实 stderr 与返回码**，不再静默得到空字符串。
  * 新增 `--root`（被核验根目录，自测隔离用）与 `--registry`（登记表路径）参数。

明确不覆盖（须人工审查）：见脚本末尾 MANUAL REVIEW 清单。
注意：结构检查通过 ≠ 语义正确。
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from proc_capture import force_utf8_stdio, run_captured, capture_mode  # noqa: E402

force_utf8_stdio()

_ap = argparse.ArgumentParser(description="RISK-REGISTRY 校验 v3")
_ap.add_argument("--root", default=r"G:\ds-h", help="被核验根目录（默认 G:\\ds-h）")
_ap.add_argument("--registry", default=None, help="登记表路径（默认 <脚本目录>/RISK-REGISTRY-v1.json）")
_args = _ap.parse_args()

ROOT = Path(_args.root).resolve()
REG = Path(_args.registry) if _args.registry else Path(__file__).parent / "RISK-REGISTRY-v1.json"
BASE = ROOT / "_xexp" / "base"
GIT = r"C:\Program Files\Git\cmd\git.exe"
FIELDS = ["constraint_id", "constraint_type", "expected_invariant",
          "change_control", "severity", "impact_rationale",
          "required_evidence", "action_policy"]
MISSING_MARKERS = ("缺失", "待补", "不在基线")

data = json.loads(REG.read_text(encoding="utf-8"))
entries = data["entries"]
fail = []
GIT_ERRORS = []

print(f"registry_version: {data['registry_version']}")
print(f"条目总数: {len(entries)}")
print(f"根目录: {ROOT}")

# ── 1. 八字段齐备与值域 ────────────────────────────────────────────
print("\n=== 1. 八字段齐备与值域 ===")
bad = [(e.get("constraint_id", "?"), [f for f in FIELDS if f not in e or e[f] in ("", None, [])])
       for e in entries]
bad = [(c, m) for c, m in bad if m]
if bad:
    fail.append(f"字段缺失: {bad}")
    print(f"  FAIL 字段缺失: {bad}")
else:
    print(f"  全部 {len(entries)} 条目八字段齐备 OK")
cc_dom = set(data["change_control_value_domain"])
sv_dom = set(data["severity_value_domain"])
vbad = [(e["constraint_id"], e["change_control"], e["severity"]) for e in entries
        if e["change_control"] not in cc_dom or e["severity"] not in sv_dom]
if vbad:
    fail.append(f"值域违规: {vbad}")
    print(f"  FAIL 值域违规: {vbad}")
else:
    print("  值域合规 OK")

# ── 2. constraint_id 唯一性 ───────────────────────────────────────
print("\n=== 2. constraint_id 唯一性 ===")
ids = [e["constraint_id"] for e in entries]
dups = sorted({i for i in ids if ids.count(i) > 1})
if dups:
    fail.append(f"重复 ID: {dups}")
    print(f"  FAIL 重复 ID: {dups}")
else:
    print(f"  {len(ids)} 个 ID 全部唯一 OK")

# ── 3. required_evidence 来源可访问性 ─────────────────────────────
print("\n=== 3. required_evidence 来源可访问性（对冻结基线路径存在性）===")
PATH_RE = re.compile(r"(?:src|tests|docs|\.)/[\w./\-]+|[\w\-]+\.(?:py|md|json|ini|toml|txt)")
unexplained = []
checked = 0
for e in entries:
    for ev in e["required_evidence"]:
        if any(mk in ev for mk in MISSING_MARKERS):
            continue  # 已显式声明缺失/待补 → 合规
        for tok in PATH_RE.findall(ev):
            tok_clean = tok.lstrip("./").replace("/", "\\")
            if not (BASE / tok_clean).exists():
                unexplained.append((e["constraint_id"], ev, tok))
            else:
                checked += 1
if unexplained:
    fail.append(f"未声明缺失的来源: {unexplained}")
    print("  FAIL 以下来源在基线中不存在且未显式声明缺失：")
    for cid, ev, tok in unexplained:
        print(f"    {cid}: '{tok}'（{ev}）")
else:
    print(f"  已解析 {checked} 个基线内路径，全部存在；其余条目均带显式缺失/待补声明 OK")

# ── 4. change_control / severity / action_policy 一致性 ───────────
print("\n=== 4. change_control / severity / action_policy 一致性 ===")
inc = []
for e in entries:
    cc, sv, ap = e["change_control"], e["severity"], e["action_policy"]
    if sv == "high" and cc != "PENDING" and ap != "阻断合并":
        inc.append((e["constraint_id"], f"severity=high 且 change_control={cc} 但 action_policy={ap}（应阻断合并）"))
    if sv == "normal" and ap not in ("警告", "人工复核"):
        inc.append((e["constraint_id"], f"severity=normal 但 action_policy={ap}"))
    if sv == "PENDING" and ap != "人工复核":
        inc.append((e["constraint_id"], f"severity=PENDING 但 action_policy={ap}（应人工复核）"))
    if cc == "PENDING" and not any(mk in "".join(e["required_evidence"]) for mk in MISSING_MARKERS):
        inc.append((e["constraint_id"], "change_control=PENDING 但 required_evidence 未声明缺失/待补"))
    if cc == "frozen" and ap not in ("阻断合并", "人工复核"):
        inc.append((e["constraint_id"], f"change_control=frozen 但 action_policy={ap}"))
if inc:
    fail.append(f"一致性违规: {inc}")
    print("  FAIL 一致性违规：")
    for cid, msg in inc:
        print(f"    {cid}: {msg}")
else:
    print("  规则 R1-R5 全部通过 OK")

# ── 5. 待决条目使用限制 ───────────────────────────────────────────
print("\n=== 5. 待决（PENDING）条目使用限制 ===")
pending = [e for e in entries if "PENDING" in (e["change_control"], e["severity"])]
blocking_pending = [e["constraint_id"] for e in pending if e["action_policy"] == "阻断合并"]
if blocking_pending:
    fail.append(f"PENDING 条目被标记为阻断: {blocking_pending}")
    print(f"  FAIL 以下待决条目被标记为『阻断合并』（待决不得直接阻断）：{blocking_pending}")
else:
    print(f"  {len(pending)} 个待决条目均未标记为阻断 OK")
print("  已声明规则：severity=PENDING 的条目不得用于判定 ALARM_HIGH（须先补齐证据）")
for e in pending:
    print(f"    - {e['constraint_id']}: change_control={e['change_control']} severity={e['severity']}")

# ── 6. 登记表与冻结基线绑定 ───────────────────────────────────────
print("\n=== 6. 登记表与冻结基线绑定关系 ===")
sb = data["subject_baseline"]


def git_rev(rev):
    rc, out, err = run_captured([GIT, "-C", str(BASE), "rev-parse", rev])
    if rc != 0:
        GIT_ERRORS.append((rev, rc, err.strip()))
        return ""
    return out.strip()


actual_commit = git_rev("HEAD")
actual_tree = git_rev("HEAD^{tree}")
if GIT_ERRORS:
    print(f"  ！git 命令失败（真实 stderr 与返回码），绑定判定按失败处理：")
    for rev, rc, err in GIT_ERRORS:
        print(f"    git rev-parse {rev} -> 返回码 {rc}: {err}")
    fail.append("git 命令执行失败")
print(f"  登记表记录 commit: {sb['commit']}")
print(f"  实测基线   commit: {actual_commit or '<git 失败>'}")
print(f"  登记表记录 tree  : {sb['tree']}")
print(f"  实测基线   tree  : {actual_tree or '<git 失败>'}")
if GIT_ERRORS:
    print("  FAIL 基线绑定无法核验（git 失败）")
elif sb["commit"] == actual_commit and sb["tree"] == actual_tree:
    print("  绑定一致 OK")
else:
    fail.append("基线绑定不一致")
    print("  FAIL 基线绑定不一致")

# ── 总结果 ────────────────────────────────────────────────────────
print("\n=== 自动校验总结果: {} ===".format("通过" if not fail else "未通过"))
print(f"（git 输出捕获方式：{capture_mode() or '未调用'}）")
for f in fail:
    print(f"  - {f}")

print("\n=== MANUAL REVIEW（脚本不可验证的语义内容，须人工审查）===")
for item in [
    "① impact_rationale 是否真正证成其 severity（因果成立，而非断言）",
    "② constraint_type 归类是否正确（权限/安全/完整性/公共接口/验收）",
    "③ expected_invariant 是否可判定（无歧义、可被测试或人工核验）",
    "④ action_policy 是否符合项目既定政策（阻断/复核/警告的取舍）",
    "⑤ 证据是否真支撑不变量（如 03_CDM §8/§9 条文是否确如所引）",
    "⑥ 待决条目的待决理由是否充分（是否本可判定而误判为待决）",
    "⑦ 登记表完整性：是否存在应登记而未登记的高风险约束（结构检查无法发现遗漏）",
    "⑧ 与引擎 HIGH_RISK_CONTRACT_FUNCS 的差异是否被如实记录（不得据此反推 severity）",
]:
    print(f"  {item}")

sys.exit(0 if not fail else 1)
