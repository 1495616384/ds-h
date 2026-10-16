"""M8 一致性漂移校验（锚活性）：把「设计文档的证据锚在代码里是否仍然有效」做成可运行、可断言的检查。

为什么需要它（问题背景，大白话）：
    逻辑模型（条目—约束—证据）是从设计文档解析出来的，它的每条证据都指向代码里的某个文件或目录。
    代码会重命名、移动、删除：一旦锚指向的目标消失，这条约束就**悄悄失联**了——没人会注意到。
    M8 回答一个朴素的问题：「**逻辑模型还跟代码对得上吗**」。

设计口径（对齐 `X产品化路线图-v1.md` §十二 M8 行与「判定口径（写死）」）：
    ① 输入 = **代码根** + **设计文档**（与 M1/M2 同参；**不需要 diff**——漂移与某次改动无关）；
    ② 锚规则**与 M3 一致**（实现已收口到 `parser.anchor_of`，全仓唯一）：取每条证据串的首个空白分隔
       token；不含 `/` 者记为 `unanchored`（显式列出，**不参与**活性判定）；
    ③ 锚**活性**定义在**文件系统存在性**（不是「是否为依赖图节点」）
       （实现已收口到 `anchor_state`，全仓唯一，M12 流程层复用同一份）：
         精确锚（不以 `/` 结尾）：活性 = 路径存在（文件或目录）；命中集合 = 文件本身，目录则列其下全部文件；
         前缀锚（以 `/` 结尾）  ：活性 = 存在以该前缀起头的文件；命中文件**全部列出**；
       不满足 → 记 `dangling`（失联锚）；
    ④ **判定只看 dangling**：有任一 dangling → `drift`，否则 `ok`。`ok` **只**表示「本次口径下锚
       全部活性」，**不**表示设计完整或正确；
    ⑤ `uncovered_files`（未被任何活性锚覆盖的文件）**仅供参考、不影响判定**；
    ⑥ 输出默认稳定 JSON，`--text` 给人类可读清单。

为什么这样定：
    * 把「活性」定在**文件系统存在性**而非「是否为依赖图节点」：否则锚到 `docs/*.md` 这类非 `.py`
      载体会被**系统性误报**为失联；
    * 把**判定**与**覆盖**解耦：覆盖是**信息**不是**判据**——「设计没写到」与「代码与设计不一致」
      是两件事，混在一起会把设计缺口冒充成漂移；
    * 多命中**全部列出**：本模块只报事实，不需要像 M3 那样为可判定性裁剪成「只取首个」。

隔离约定：本模块**不写死**任何冻结链路径；代码根 / 设计文档一律由调用方传入
（由 M0 自测第三条校验本包源码不含冻结链目录名）。仅依赖 Python 标准库。
"""

from __future__ import annotations

import json
from pathlib import Path

from . import parser

ANCHOR_EXACT = "exact"
ANCHOR_PREFIX = "prefix"

STATUS_ACTIVE = "active"
STATUS_DANGLING = "dangling"
STATUS_UNANCHORED = "unanchored"

VERDICT_OK = "ok"
VERDICT_DRIFT = "drift"

REASON_PREFIX_EMPTY = "前缀下无文件"
REASON_PATH_MISSING = "路径不存在"

_DRIFT_NOTE = "note: ok 仅表示本次口径下锚全部活性，不表示设计完整或正确"


class DriftError(ValueError):
    """代码根不可用（不是目录）时抛出；设计文档不合格式由 M1 `ParseError` 直接上抛。"""


def scan_tree(root: Path) -> tuple[list[str], set[str], set[str]]:
    """枚举代码根下全部文件与目录（相对 POSIX 路径），返回（files 已排序, dirs, files 集合）。

    公开成函数供 M12 `flow` 复用**同一份**文件枚举口径（与 M8 同源），
    避免「扫描」逻辑各写一份后悄悄漂移。
    """
    files: list[str] = []
    dirs: set[str] = set()
    for p in root.rglob("*"):
        rel = p.relative_to(root).as_posix()
        if p.is_dir():
            dirs.add(rel)
        else:
            files.append(rel)
    files.sort()
    return files, dirs, set(files)


def anchor_state(
    anchor: str | None,
    files: list[str],
    dirs: set[str],
    file_set: set[str],
) -> dict:
    """锚活性判定（写死口径；**全仓唯一实现**，M8 / M12 一律经此，不得各自复刻）。

    为什么收口成一个函数：活性判定曾按「大体相同的规则」在 drift 与 flow 各写一遍，
    一旦某处补了分支（如「精确锚命中目录」）另一处没补，同一份证据锚就会在两处给出
    相反的三态，而两边各自的输出看上去都「正常」——这类**隐性漂移**只能靠结构上
    只留一份实现来堵死（由 `selftest_m12` 的结构断言强制）。

    规则（与 M8 判定口径逐字对齐）：
        `anchor is None`                → `unanchored`（不参与活性判定）
        以 `/` 结尾（前缀锚）           → 存在以该前缀起头的文件即 `active`（命中文件全部列出），
                                          否则 `dangling`（前缀下无文件）
        其余（精确锚）                  → 命中文件本身即 `active`；锚是**目录**则命中其下全部文件；
                                          都不成立 → `dangling`（路径不存在）
    返回 `{"status", "match_kind"[, "matched_files"][, "reason"]}`——`matched_files` 仅活性时有，
    `reason` 仅失联时有，以便 M8 的文本清单能逐字节复现原输出。
    """
    if anchor is None:
        return {"status": STATUS_UNANCHORED}
    if anchor.endswith("/"):
        matched = [f for f in files if f.startswith(anchor)]
        if matched:
            return {"status": STATUS_ACTIVE, "match_kind": ANCHOR_PREFIX, "matched_files": matched}
        return {"status": STATUS_DANGLING, "match_kind": ANCHOR_PREFIX, "reason": REASON_PREFIX_EMPTY}
    if anchor in file_set:
        return {"status": STATUS_ACTIVE, "match_kind": ANCHOR_EXACT, "matched_files": [anchor]}
    if anchor in dirs:
        matched = [f for f in files if f.startswith(anchor + "/")]
        return {"status": STATUS_ACTIVE, "match_kind": ANCHOR_EXACT, "matched_files": matched}
    return {"status": STATUS_DANGLING, "match_kind": ANCHOR_EXACT, "reason": REASON_PATH_MISSING}


def _by_entry(record: dict) -> tuple[str, str]:
    """活性 / 失联 / 无锚记录的稳定排序键：先条目 id，再证据原文。"""
    return (record["constraint_id"], record["evidence"])


def analyze(code_root: str | Path, design_doc: str | Path) -> dict:
    """逐条证据锚解析活性，返回键序固定、可逐字节复现的结果文档。"""
    root = Path(code_root)
    if not root.is_dir():
        raise DriftError(f"代码根不是目录：{root}")
    files, dirs, file_set = scan_tree(root)
    design = parser.parse_file(design_doc)

    active: list[dict] = []
    dangling: list[dict] = []
    unanchored: list[dict] = []
    covered: set[str] = set()

    for entry in design["entries"]:
        cid = entry["constraint_id"]
        for evidence in entry["required_evidence"]:
            anchor = parser.anchor_of(evidence)
            if anchor is None:
                unanchored.append({"constraint_id": cid, "evidence": evidence})
                continue
            record = {
                "constraint_id": cid,
                "evidence": evidence,
                "anchor": anchor,
            }
            state = anchor_state(anchor, files, dirs, file_set)
            record["match_kind"] = state["match_kind"]
            if state["status"] == STATUS_DANGLING:
                record["reason"] = state["reason"]
                dangling.append(record)
                continue
            matched = state["matched_files"]
            covered.update(matched)
            record["matched_files"] = matched
            active.append(record)

    active.sort(key=_by_entry)
    dangling.sort(key=_by_entry)
    unanchored.sort(key=_by_entry)
    uncovered = sorted(file_set - covered)

    return {
        "code_root_file_count": len(files),
        "entry_count": design["entry_count"],
        "active_count": len(active),
        "dangling_count": len(dangling),
        "active_anchors": active,
        "dangling_anchors": dangling,
        "unanchored_evidence": unanchored,
        "uncovered_file_count": len(uncovered),
        "uncovered_files": uncovered,
        "verdict": VERDICT_DRIFT if dangling else VERDICT_OK,
    }


def render_text(doc: dict) -> str:
    """把结果文档渲染为确定性 ASCII 清单（人类可读；逐字节可断言）。

    各段固定打印计数（空段也打印），组内按（条目 id, 证据原文）排序。
    """
    lines = [
        f"design entries ({doc['entry_count']}), code files ({doc['code_root_file_count']}):",
        f"active anchors ({doc['active_count']}):",
    ]
    for a in doc["active_anchors"]:
        lines.append(f"    {a['constraint_id']}  {a['anchor']} [{a['match_kind']}]")
        lines.extend(f"        -> {path}" for path in a["matched_files"])
    lines.append(f"dangling anchors ({doc['dangling_count']}):")
    for d in doc["dangling_anchors"]:
        lines.append(f"    {d['constraint_id']}  {d['anchor']} [{d['match_kind']}] {d['reason']}")
    lines.append(f"unanchored evidence ({len(doc['unanchored_evidence'])}):")
    for u in doc["unanchored_evidence"]:
        lines.append(f"    {u['constraint_id']}: {u['evidence']}")
    lines.append(f"uncovered files ({doc['uncovered_file_count']}) — 仅供参考，不参与判定:")
    lines.extend(f"    {path}" for path in doc["uncovered_files"])
    lines.append(f"verdict: {doc['verdict']}")
    lines.append(_DRIFT_NOTE)
    return "\n".join(lines) + "\n"


def to_json(doc: dict) -> str:
    """稳定序列化：UTF-8、缩进 2、键序按插入顺序、末尾单换行（与 M1–M7 同口径）。"""
    return json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
