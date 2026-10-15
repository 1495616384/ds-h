"""M1 设计文档解析器：把写死格式的设计文档析为「条目—约束—证据」模型。

输入格式（写死；示例见 `samples/design-sample.md`）：
    ① 条目以标题行 `### <ID> — <标题>` 起头（ID 形如 `CV-001`，分隔符为全角破折号「—」）；
    ② 标题行之下为字段行 `- <键>: <值>`，键限定为
       type / invariant / change_control / severity / evidence / action_policy；
    ③ `evidence` 的值是其下若干缩进行 `  - <引用>`（至少 1 条），不得写成行内值；
    ④ 条目按出现顺序输出，ID 不得重复；
    ⑤ 首个条目之前只允许文档头/引用行（以 `#` 或 `>` 起头），其余内容一律报错。

输出字段口径对齐 `RISK-REGISTRY v1`（同一 ID/字段空间，便于 M3 直接承接，不另造体系）：
    constraint_id / constraint_type / expected_invariant / change_control /
    severity / required_evidence / action_policy；
另加 `title`——「条目」的可读名（RISK-REGISTRY 为纯约束登记，无此列）。

仅依赖 Python 标准库（M1 边界：不引入未安装依赖）。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

# 值域与 RISK-REGISTRY v1 保持一致：解析阶段只做「取值合法性」校验，
# 不做严重度/变更控制的语义判定（那是判定阶段的事，M1 不越界）。
SEVERITY_DOMAIN = ("high", "normal", "PENDING")
CHANGE_CONTROL_DOMAIN = ("frozen", "approval-required", "free", "PENDING")

# 输入键 → 输出字段名（对齐 RISK-REGISTRY 的列名）
_KEY_TO_FIELD = {
    "type": "constraint_type",
    "invariant": "expected_invariant",
    "change_control": "change_control",
    "severity": "severity",
    "evidence": "required_evidence",
    "action_policy": "action_policy",
}
# 除 evidence（列表）外的必填标量键
_REQUIRED_SCALAR_KEYS = ("type", "invariant", "change_control", "severity", "action_policy")

_HEADING = re.compile(r"^###\s+(?P<id>[A-Za-z]+-\d{3,})\s+—\s+(?P<title>.+?)\s*$")
_FIELD = re.compile(r"^-\s+(?P<key>[A-Za-z_]+)\s*:\s*(?P<value>.*?)\s*$")
_EVIDENCE_ITEM = re.compile(r"^[ \t]+-\s+(?P<value>.+?)\s*$")


class ParseError(ValueError):
    """设计文档不符合写死格式时抛出；消息中带行号，便于人工定位。"""


@dataclass(frozen=True)
class Entry:
    """单条「条目—约束—证据」，字段名与 RISK-REGISTRY v1 对齐。"""

    constraint_id: str
    title: str
    constraint_type: str
    expected_invariant: str
    change_control: str
    severity: str
    required_evidence: tuple[str, ...]
    action_policy: str

    def to_dict(self) -> dict:
        """输出为有序字典（键序固定，保证 JSON 逐字节可复现）。"""
        return {
            "constraint_id": self.constraint_id,
            "title": self.title,
            "constraint_type": self.constraint_type,
            "expected_invariant": self.expected_invariant,
            "change_control": self.change_control,
            "severity": self.severity,
            "required_evidence": list(self.required_evidence),
            "action_policy": self.action_policy,
        }


def _to_entry(cur: dict) -> Entry:
    """把解析中途的原始字段字典校验并转换为 Entry。"""
    cid = cur["id"]
    missing = [k for k in _REQUIRED_SCALAR_KEYS if k not in cur["fields"]]
    if not cur["evidence"]:
        missing.append("evidence")
    if missing:
        raise ParseError(f"条目 {cid}（第 {cur['line']} 行起）缺少必填字段：{missing}")

    cc = cur["fields"]["change_control"]
    if cc not in CHANGE_CONTROL_DOMAIN:
        raise ParseError(
            f"条目 {cid}：change_control 取值 {cc!r} 不在值域 {CHANGE_CONTROL_DOMAIN}"
        )
    sev = cur["fields"]["severity"]
    if sev not in SEVERITY_DOMAIN:
        raise ParseError(f"条目 {cid}：severity 取值 {sev!r} 不在值域 {SEVERITY_DOMAIN}")

    return Entry(
        constraint_id=cid,
        title=cur["title"],
        constraint_type=cur["fields"]["type"],
        expected_invariant=cur["fields"]["invariant"],
        change_control=cc,
        severity=sev,
        required_evidence=tuple(cur["evidence"]),
        action_policy=cur["fields"]["action_policy"],
    )


def parse_design_doc(text: str) -> list[Entry]:
    """把设计文档文本解析为 Entry 列表；不合格式即抛 ParseError。"""
    entries: list[Entry] = []
    cur: dict | None = None
    seen: set[str] = set()

    def flush() -> None:
        if cur is not None:
            entries.append(_to_entry(cur))

    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.rstrip()  # 只去尾部空白，保留缩进用于识别证据条目
        if not line.strip():
            continue

        m = _HEADING.match(line)
        if m:
            flush()
            cid = m.group("id")
            if cid in seen:
                raise ParseError(f"第 {lineno} 行：条目 ID 重复：{cid}")
            seen.add(cid)
            cur = {
                "id": cid,
                "title": m.group("title"),
                "fields": {},
                "evidence": [],
                "section": None,  # 当前字段键；值为 "evidence" 表示正处于证据列表
                "line": lineno,
            }
            continue

        if cur is None:
            if line.lstrip().startswith(("#", ">")):
                continue  # 首个条目前的文档头部/引用行，忽略
            raise ParseError(f"第 {lineno} 行：首个条目之前出现无法解析的内容：{line!r}")

        m = _EVIDENCE_ITEM.match(line)
        if m:
            if cur["section"] != "evidence":
                raise ParseError(f"第 {lineno} 行：证据条目出现在非 evidence 区段")
            cur["evidence"].append(m.group("value"))
            continue

        m = _FIELD.match(line)
        if m:
            key, value = m.group("key"), m.group("value")
            if key not in _KEY_TO_FIELD:
                raise ParseError(f"第 {lineno} 行：未知字段键 {key!r}")
            if key in cur["fields"] or key == cur["section"]:
                raise ParseError(f"第 {lineno} 行：字段键重复 {key!r}（条目 {cur['id']}）")
            if key == "evidence":
                if value:
                    raise ParseError(
                        f"第 {lineno} 行：evidence 不得写成行内值，应为缩进列表"
                    )
                cur["section"] = "evidence"
            else:
                if not value:
                    raise ParseError(f"第 {lineno} 行：字段 {key!r} 的值不得为空")
                cur["fields"][key] = value
                cur["section"] = key
            continue

        raise ParseError(f"第 {lineno} 行：无法解析的行：{line!r}")

    flush()
    if not entries:
        raise ParseError("未解析到任何条目")
    return entries


def parse_text(text: str) -> dict:
    """解析文本并返回文档级输出结构：{entry_count, entries}。"""
    entries = parse_design_doc(text)
    return {"entry_count": len(entries), "entries": [e.to_dict() for e in entries]}


def parse_file(path: str | Path) -> dict:
    """解析 UTF-8 设计文档文件。"""
    return parse_text(Path(path).read_text(encoding="utf-8"))


def to_json(doc: dict) -> str:
    """稳定序列化：UTF-8、缩进 2、键序按插入顺序、末尾单换行。"""
    return json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
