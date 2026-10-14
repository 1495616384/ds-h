"""Validators for Evaluation Case (Step 7-D, v4 Coding Contract).

7 sub-validators + 1 top-level validate_case.
All functions operate on ALREADY-CONSTRUCTED objects — they do NOT
catch KeyError / FileNotFoundError / JSONDecodeError.
That responsibility belongs to from_dict() / from_dir() and their tests.

Reuses from Step 7-B:
    is_valid_fact_id(raw)        → grammar-level validation (no registry lookup)
    is_valid_quantity_kind(v)    → QUANTITY_KINDS enum membership check
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from cdm.id import is_valid_fact_id
from cdm.registry import is_valid_quantity_kind

from .enums import (
    CASE_LEVELS,
    ISSUE_TYPES,
    SEVERITIES,
    is_valid_case_level,
    is_valid_issue_type,
    is_valid_severity,
)
from .types import (
    EvaluationCase,
    GroundTruthConclusion,
    GroundTruthFact,
    GroundTruthFactList,
    GroundTruthStructure,
    KnownIssue,
    Meta,
    ExpectedIssue,
)


# ── 1. validate_meta ───────────────────────────────────────────────

def validate_meta(meta: Meta) -> List[str]:
    errors: List[str] = []

    if not is_valid_case_level(meta.case_level):
        errors.append(
            f"Meta.case_level '{meta.case_level}' is not in allowed set: {sorted(CASE_LEVELS)}"
        )

    for field_name, field_val in [
        ("case_id", meta.case_id),
        ("report_type", meta.report_type),
        ("source_project", meta.source_project),
    ]:
        if not isinstance(field_val, str) or not field_val.strip():
            errors.append(f"Meta.{field_name} must be a non-empty string, got: {field_val!r}")

    # created_at must parse as ISO 8601
    try:
        datetime.fromisoformat(meta.created_at.replace("Z", "+00:00"))
    except (ValueError, AttributeError, TypeError):
        errors.append(f"Meta.created_at '{meta.created_at}' is not a valid ISO 8601 datetime")

    return errors


# ── 2. validate_ground_truth_fact (single) ────────────────────────

_ALLOWED_VALUE_TYPES = (int, float, str, bool)


def validate_ground_truth_fact(fact: GroundTruthFact) -> List[str]:
    """Validate a single GroundTruthFact (G3)."""
    errors: List[str] = []

    # fact_id grammar — reuse Step 7-B
    err = is_valid_fact_id(fact.fact_id)
    if err is not None:
        errors.append(f"GroundTruthFact.fact_id: {err}")

    # quantity_kind enum — reuse Step 7-B
    if not is_valid_quantity_kind(fact.quantity_kind):
        errors.append(
            f"GroundTruthFact.quantity_kind '{fact.quantity_kind}' is not in QUANTITY_KINDS"
        )

    # precision >= 0
    if not isinstance(fact.precision, int) or fact.precision < 0:
        errors.append(
            f"GroundTruthFact.precision must be int >= 0, got {fact.precision!r}"
        )

    # v4: value must be non-None and be one of int/float/str/bool
    if fact.value is None:
        errors.append(
            f"GroundTruthFact.value must not be None (G3 is confirmed Ground Truth, "
            f"CDM missing uses value=null; bronze uses facts=[])"
        )
    elif not isinstance(fact.value, _ALLOWED_VALUE_TYPES):
        errors.append(
            f"GroundTruthFact.value must be int|float|str|bool, got {type(fact.value).__name__}"
        )

    return errors


def validate_ground_truth_facts(facts: List[GroundTruthFact]) -> List[str]:
    """Validate a list of GroundTruthFact (G3). Also checks intra-list uniqueness."""
    errors: List[str] = []

    seen_ids: set[str] = set()
    for idx, fact in enumerate(facts):
        errors.extend(validate_ground_truth_fact(fact))
        if fact.fact_id in seen_ids:
            errors.append(
                f"G3 GroundTruthFact list contains duplicate fact_id: "
                f"'{fact.fact_id}' at index {idx}"
            )
        seen_ids.add(fact.fact_id)

    return errors


# ── 3. validate_ground_truth_fact_list ────────────────────────────

def validate_ground_truth_fact_list(ftl: GroundTruthFactList) -> List[str]:
    """Validate G2 fact list: grammar + intra-list uniqueness."""
    errors: List[str] = []

    seen: set[str] = set()
    for idx, fid in enumerate(ftl.fact_ids):
        if not isinstance(fid, str) or not fid.strip():
            errors.append(f"G2 fact_ids[{idx}] must be a non-empty string")
        else:
            err = is_valid_fact_id(fid)
            if err is not None:
                errors.append(f"G2 fact_ids[{idx}]: {err}")
            if fid in seen:
                errors.append(
                    f"G2 fact_ids contains duplicate fact_id: '{fid}' at index {idx}"
                )
            seen.add(fid)

    return errors


# ── 4. validate_ground_truth_structure ─────────────────────────────

def validate_ground_truth_structure(gs: GroundTruthStructure) -> List[str]:
    errors: List[str] = []

    if gs.table_count < 0:
        errors.append(f"GroundTruthStructure.table_count must be >= 0, got {gs.table_count}")
    if gs.figure_count < 0:
        errors.append(f"GroundTruthStructure.figure_count must be >= 0, got {gs.figure_count}")

    for i, cp in enumerate(gs.chapter_paths):
        if not isinstance(cp, str) or not cp.strip():
            errors.append(f"GroundTruthStructure.chapter_paths[{i}] must be non-empty string")

    for i, hdr in enumerate(gs.table_headers):
        if not isinstance(hdr, list):
            errors.append(f"GroundTruthStructure.table_headers[{i}] must be a list")
            continue
        for j, col in enumerate(hdr):
            if not isinstance(col, str) or not col.strip():
                errors.append(
                    f"GroundTruthStructure.table_headers[{i}][{j}] must be non-empty string"
                )

    for i, el in enumerate(gs.required_elements):
        if not isinstance(el, str) or not el.strip():
            errors.append(f"GroundTruthStructure.required_elements[{i}] must be non-empty string")

    return errors


# ── 5. validate_ground_truth_conclusion ───────────────────────────

def validate_ground_truth_conclusion(gc: GroundTruthConclusion) -> List[str]:
    """Validate G4 conclusion.

    direction: check non-empty only (business enum provided by ConclusionRule).
    required_evaluation_ids: opaque — no grammar check, only non-empty + no duplicates.
    """
    errors: List[str] = []

    if not isinstance(gc.direction, str) or not gc.direction.strip():
        errors.append("GroundTruthConclusion.direction must be a non-empty string")

    ids = gc.required_evaluation_ids
    if not isinstance(ids, list) or len(ids) == 0:
        errors.append("GroundTruthConclusion.required_evaluation_ids must be a non-empty list")
    else:
        seen: set[str] = set()
        for idx, eid in enumerate(ids):
            if not isinstance(eid, str) or not eid.strip():
                errors.append(
                    f"GroundTruthConclusion.required_evaluation_ids[{idx}] "
                    f"must be a non-empty string"
                )
            elif eid in seen:
                errors.append(
                    f"GroundTruthConclusion.required_evaluation_ids contains duplicate: "
                    f"'{eid}' at index {idx}"
                )
            else:
                seen.add(eid)

    return errors


# ── 6. validate_known_issue(s) ────────────────────────────────────

def validate_known_issue(ki: KnownIssue) -> List[str]:
    errors: List[str] = []

    if not is_valid_issue_type(ki.issue_type):
        errors.append(
            f"KnownIssue.issue_type '{ki.issue_type}' is not in allowed set: {sorted(ISSUE_TYPES)}"
        )

    # conditional-required: fact_id required when issue_type=fact_value_error
    if ki.issue_type == "fact_value_error":
        if not ki.fact_id:
            errors.append(
                "KnownIssue.fact_id is required when issue_type='fact_value_error' "
                "(conditional-required)"
            )
        else:
            err = is_valid_fact_id(ki.fact_id)
            if err is not None:
                errors.append(f"KnownIssue.fact_id: {err}")
    # conclusion_error: fact_id can be None — no extra check

    # confirmed_at ISO 8601
    try:
        datetime.fromisoformat(ki.confirmed_at.replace("Z", "+00:00"))
    except (ValueError, AttributeError, TypeError):
        errors.append(f"KnownIssue.confirmed_at '{ki.confirmed_at}' is not valid ISO 8601")

    if not isinstance(ki.confirmed_by, str) or not ki.confirmed_by.strip():
        errors.append("KnownIssue.confirmed_by must be non-empty string")

    if ki.original_value == ki.correct_value:
        errors.append(
            "KnownIssue.original_value and correct_value must differ "
            "(otherwise it's not an error)"
        )

    if not isinstance(ki.reason, str) or not ki.reason.strip():
        errors.append("KnownIssue.reason must be non-empty string")

    return errors


def validate_known_issues(kis: List[KnownIssue]) -> List[str]:
    errors: List[str] = []
    for idx, ki in enumerate(kis):
        for e in validate_known_issue(ki):
            errors.append(f"KnownIssues[{idx}]: {e}")
    return errors


# ── 7. validate_expected_issue(s) ────────────────────────────────

def validate_expected_issue(ei: ExpectedIssue) -> List[str]:
    errors: List[str] = []

    if not isinstance(ei.rule_id, str) or not ei.rule_id.strip():
        errors.append("ExpectedIssue.rule_id must be non-empty string")

    if not is_valid_severity(ei.severity):
        errors.append(
            f"ExpectedIssue.severity '{ei.severity}' is not in allowed set: {sorted(SEVERITIES)}"
        )

    # fact_id optional — if present, grammar-check it
    if ei.fact_id:
        err = is_valid_fact_id(ei.fact_id)
        if err is not None:
            errors.append(f"ExpectedIssue.fact_id: {err}")

    return errors


def validate_expected_issues(eis: List[ExpectedIssue]) -> List[str]:
    errors: List[str] = []
    for idx, ei in enumerate(eis):
        for e in validate_expected_issue(ei):
            errors.append(f"ExpectedIssues[{idx}]: {e}")
    return errors


# ── 8. validate_case (top-level cross-file integrity + case_level) ─

def validate_case(case: EvaluationCase) -> List[str]:
    """Top-level validator for cross-file consistency + case_level rules.

    Does NOT re-run sub-validators (caller calls those separately).
    Does NOT check inputs/ directory existence — from_dir() enforces that
    at load time and raises FileNotFoundError before object construction.

    Rules:
        T-1  G3.fact_ids ⊆ G2.fact_ids (gold / silver)
        T-2  G2.fact_ids no duplicates (gold / silver / bronze) — see sub-validator
        T-3  G3.fact_ids no duplicates (gold / silver) — see sub-validator
        T-4  gold/silver: G3 non-empty; bronze: G3 == []
        T-5  gold/silver/bronze: G2 non-empty
    """
    errors: List[str] = []

    # ── Extract G2 / G3 IDs ──
    g2_ids = case.ground_truth.fact_list.fact_ids
    g3_ids = [f.fact_id for f in case.ground_truth.facts]

    level = case.meta.case_level

    # ── T-1: G3 ⊆ G2 (gold / silver only) ──
    if level in ("gold", "silver") and g3_ids:
        g2_set = set(g2_ids)
        missing = [fid for fid in g3_ids if fid not in g2_set]
        if missing:
            errors.append(
                f"G2→G3 referential integrity violation ({level}): "
                f"{len(missing)} G3 fact_id(s) not found in G2 fact_ids: "
                f"{missing!r}"
            )

    # ── T-3: G2 no duplicates (already checked by sub-validator, but re-check) ──
    # (sub-validator validate_ground_truth_fact_list handles this; we skip to avoid double-report)

    # ── T-4: G3 no duplicates (already checked by validate_ground_truth_facts) ──

    # ── T-5: case_level ↔ G3 consistency ──
    if level == "bronze":
        if len(case.ground_truth.facts) != 0:
            errors.append(
                "bronze case_level requires G3 facts.json to be empty ([]), "
                f"but found {len(case.ground_truth.facts)} GroundTruthFact entries"
            )
    elif level in ("gold", "silver"):
        if len(case.ground_truth.facts) == 0:
            errors.append(
                f"{level} case_level requires G3 facts.json to be non-empty, "
                "but found 0 entries"
            )

    # ── T-6: G2 must be non-empty for ALL levels ──
    if len(g2_ids) == 0:
        errors.append(
            f"{level} case_level requires G2 fact_list.json to be non-empty, "
            "but fact_ids list is empty"
        )

    return errors
