"""Step 7-E Accuracy Validator — data structures (§4 Coding Contract v10).

All structures are frozen by Step_7_E_Coding_Contract_v10.md §4.
B5 adds anchor_declarations to TableCell only.  AnchorDeclaration,
RenderedSegment, StructuredTable, SystemOutput, ActualIssue unchanged.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import List, Optional


# ── §4 AnchorDeclaration (冻结，不得修改) ──────────────────────────

@dataclass
class AnchorDeclaration:
    """§4 — AnchorDeclaration.

    Matches 04_REPORT_IR §13.1 anchors {token, fact_id}.
    char_start / char_end: offset relative to the CARRIER text
        (RenderedSegment.raw_text  OR  TableCell.raw_text).
    """
    token: str
    fact_id: str
    char_start: int
    char_end: int


# ── §4 RenderedSegment (冻结，不得修改) ─────────────────────────────

@dataclass
class RenderedSegment:
    """§4 — RenderedSegment (prose / 图注 / Table title / note)."""
    segment_location: str
    raw_text: str
    anchor_declarations: List[AnchorDeclaration] = field(default_factory=list)


# ── §4 TableCell (B5 新增 anchor_declarations；cell.fact_id 保留) ───

@dataclass
class TableCell:
    """§4 — TableCell.

    B5 changes ONLY: adds anchor_declarations list.
    legacy cell.fact_id kept for single-token legacy path only
    (see Step_7_E_B5_Design_Check.md §4.1).
    """
    raw_text: str
    fact_id: Optional[str] = None
    # B5: per-cell per-token binding declarations
    anchor_declarations: List[AnchorDeclaration] = field(default_factory=list)


# ── §4 StructuredTable (冻结，不得修改) ────────────────────────────

@dataclass
class StructuredTable:
    """§4 — StructuredTable."""
    table_id: str
    headers: List[TableCell] = field(default_factory=list)
    rows: List[List[TableCell]] = field(default_factory=list)


# ── §4 SystemOutput (冻结，不得修改) ────────────────────────────────

@dataclass
class SystemIssue:
    """Diagnostic — not used by Validator judgment flow."""
    rule_id: str
    severity: str
    message: str
    fact_id: Optional[str] = None


@dataclass
class SystemEvaluation:
    """Diagnostic — not used by Validator judgment flow."""
    evaluation_id: str
    status: str


@dataclass
class SystemOutput:
    """§4 — SystemOutput.

    Validator does NOT trust TokenOccurrence — it tokenizes itself.
    """
    report_ir: dict
    rendered_segments: List[RenderedSegment] = field(default_factory=list)
    structured_tables: List[StructuredTable] = field(default_factory=list)
    system_reported_issues: List[SystemIssue] = field(default_factory=list)
    system_evaluations: List[SystemEvaluation] = field(default_factory=list)


# ── §11 ActualIssue (build-only 构造守卫) ──────────────────────────

class ActualIssueLocation(str):
    """Type alias for location strings like 'rendered_segments[2]:char[15-20]'."""
    pass


@dataclass
class ActualIssue:
    """§11 — ActualIssue (build-only).

    Identity is 6-tuple (frozen, INV-17):
        (issue_type, location, fact_id, evaluation_id, occurrence_id, table_aggregate)

    CONSTRUCTOR GUARD (B3):
        Any ActualIssue(...) direct construction → TypeError.
        Only ActualIssue.build(...) produces valid instances.
        build() uses object.__new__ to bypass __init__/__post_init__.
    """
    # ── Public constructor fields ──
    rule_id: str                              # belongs to P0 Rule, NOT in identity
    severity: str                             # error | warning, NOT in identity
    issue_type: str                           # identity[0]
    location: str                             # identity[1]
    message: str                              # diagnostic, NOT in identity

    fact_id: Optional[str] = None             # identity[2]
    evaluation_id: Optional[str] = None       # identity[3]
    occurrence_id: Optional[str] = None       # identity[4]
    table_aggregate: Optional[str] = None     # identity[5]

    # ── NOT in public constructor (init=False) ──
    identity: tuple = field(init=False, repr=False)
    issue_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        # B3 build-only guard: __post_init__ runs ONLY after dataclass __init__.
        # build() uses object.__new__ which bypasses __init__ → __post_init__.
        raise TypeError(
            "ActualIssue is build-only; use ActualIssue.build(...) instead of direct construction"
        )

    @classmethod
    def build(
        cls,
        rule_id: str,
        severity: str,
        issue_type: str,
        location: str,
        message: str,
        fact_id: Optional[str] = None,
        evaluation_id: Optional[str] = None,
        occurrence_id: Optional[str] = None,
        table_aggregate: Optional[str] = None,
    ) -> "ActualIssue":
        """§11.3 — sole valid constructor entry point.

        Uses object.__new__ to bypass __init__ (and thus __post_init__ guard),
        then manually sets all fields including identity + issue_id.
        """
        instance = object.__new__(cls)
        object.__setattr__(instance, "rule_id", rule_id)
        object.__setattr__(instance, "severity", severity)
        object.__setattr__(instance, "issue_type", issue_type)
        object.__setattr__(instance, "location", location)
        object.__setattr__(instance, "message", message)
        object.__setattr__(instance, "fact_id", fact_id)
        object.__setattr__(instance, "evaluation_id", evaluation_id)
        object.__setattr__(instance, "occurrence_id", occurrence_id)
        object.__setattr__(instance, "table_aggregate", table_aggregate)

        # identity — §11.1 frozen 6-tuple
        identity = (
            issue_type,
            location,
            fact_id,
            evaluation_id,
            occurrence_id,
            table_aggregate,
        )
        object.__setattr__(instance, "identity", identity)
        object.__setattr__(instance, "issue_id", _compute_issue_id(identity))
        return instance


def _compute_issue_id(identity: tuple) -> str:
    """§11.4 — issue_id = SHA-256(canonical JSON of identity tuple)."""
    canonical_json = json.dumps(identity, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
