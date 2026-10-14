"""Validation functions for Canonical Data Model types.

All validation logic corresponds to 03_CANONICAL_DATA_MODEL.md v0.3.

Each Validate() returns a list of error strings. Empty list = valid.
"""
from __future__ import annotations

from typing import Optional

from .registry import (
    METHODS,
    PROVENANCES,
    FACT_STATUSES,
    REVIEW_STATUSES,
    QUANTITY_KINDS,
    is_valid_method,
    is_valid_provenance,
    is_valid_fact_status,
    is_valid_review_status,
    is_valid_quantity_kind,
    is_valid_raw_source_type,
    is_valid_resolution_policy,
    FactTypeRegistry,
    get_default_registry,
)
from .id import is_valid_fact_id, parse_fact_id
from .types import (
    SourceRef,
    RawSource,
    Fact,
    Conflict,
    ConflictCandidate,
)


# ──────────────────────────────────────────────
# SourceRef
# ──────────────────────────────────────────────

def validate_source_ref(sr: SourceRef) -> list[str]:
    errs: list[str] = []
    if not sr.source_id or not sr.source_id.strip():
        errs.append("SourceRef.source_id must be non-empty")
    if not sr.location or not sr.location.strip():
        errs.append("SourceRef.location must be non-empty")
    return errs


# ──────────────────────────────────────────────
# RawSource
# ──────────────────────────────────────────────

def validate_raw_source(rs: RawSource) -> list[str]:
    errs: list[str] = []
    if not rs.source_id or not rs.source_id.strip():
        errs.append("RawSource.source_id must be non-empty")
    if not rs.source_type:
        errs.append("RawSource.source_type must be non-empty")
    elif not is_valid_raw_source_type(rs.source_type):
        errs.append(
            f"RawSource.source_type '{rs.source_type}' is not in "
            f"RAW_SOURCE_TYPES")
    if rs.location is not None and not rs.location.strip():
        errs.append("RawSource.location, if set, must not be empty string")
    return errs


# ──────────────────────────────────────────────
# ConflictCandidate
# ──────────────────────────────────────────────

def validate_conflict_candidate(cc: ConflictCandidate) -> list[str]:
    errs: list[str] = []
    if cc.value is None:
        errs.append("ConflictCandidate.value must not be None")
    if not is_valid_quantity_kind(cc.quantity_kind):
        errs.append(
            f"ConflictCandidate.quantity_kind '{cc.quantity_kind}' is "
            f"not valid")
    errs.extend(validate_source_ref(cc.source_ref))
    if not is_valid_method(cc.method):
        errs.append(
            f"ConflictCandidate.method '{cc.method}' is not valid")
    if not is_valid_provenance(cc.provenance):
        errs.append(
            f"ConflictCandidate.provenance '{cc.provenance}' is not valid")
    return errs


# ──────────────────────────────────────────────
# Conflict
# ──────────────────────────────────────────────

def validate_conflict(conf: Conflict) -> list[str]:
    errs: list[str] = []

    # fact_id must be non-empty and parseable
    if not conf.fact_id or not conf.fact_id.strip():
        errs.append("Conflict.fact_id must be non-empty")
    else:
        fid_err = is_valid_fact_id(conf.fact_id)
        if fid_err is not None:
            errs.append(f"Conflict.fact_id: {fid_err}")

    # must have at least 2 candidates to be a real conflict
    if len(conf.candidates) < 2:
        errs.append(
            "Conflict.candidates must have at least 2 entries "
            "(multi-source inconsistency is required for a conflict)")

    for i, c in enumerate(conf.candidates):
        sub = validate_conflict_candidate(c)
        for e in sub:
            errs.append(f"Conflict.candidates[{i}]: {e}")

    # resolution_policy — first phase only "manual" allowed
    if not is_valid_resolution_policy(conf.resolution_policy):
        errs.append(
            f"Conflict.resolution_policy '{conf.resolution_policy}' "
            f"is not valid")
    elif conf.resolution_policy != "manual":
        errs.append(
            f"Conflict.resolution_policy must be 'manual' in first phase; "
            f"'{conf.resolution_policy}' is reserved for future phases")

    # resolved_by / resolution: if one is set, both should be set
    if conf.resolved_by is not None and not conf.resolution:
        errs.append(
            "Conflict.resolved_by is set but resolution is empty "
            "(both must be set together)")
    if conf.resolution is not None and not conf.resolved_by:
        errs.append(
            "Conflict.resolution is set but resolved_by is empty "
            "(both must be set together)")

    return errs


# ──────────────────────────────────────────────
# Fact — THE big one
# ──────────────────────────────────────────────

def validate_fact(
    fact: Fact,
    registry: Optional[FactTypeRegistry] = None,
) -> list[str]:
    """Full Fact validation against v0.3 rules.

    Args:
        fact: The Fact to validate.
        registry: Optional FactTypeRegistry. If None, uses default.
    """
    errs: list[str] = []
    reg = registry or get_default_registry()

    # ── 1. ID (v0.3.1 strict three-segment + fact_type invariant) ──
    fid_err = is_valid_fact_id(fact.id, fact_type=fact.fact_type,
                               registry=reg)
    if fid_err is not None:
        errs.append(f"Fact.id: {fid_err}")

    # ── 2. revision (v0.3.1 §15.5) ──────────────────────────
    if not isinstance(fact.revision, int) or isinstance(fact.revision, bool):
        # bool is subclass of int — explicitly reject
        errs.append(
            f"Fact.revision must be a positive int, got "
            f"{type(fact.revision).__name__} = {fact.revision!r}")
    elif fact.revision < 1:
        errs.append(
            f"Fact.revision must be >= 1, got {fact.revision}")
    elif fact.revision > 1 and fact.supersedes is None:
        errs.append(
            f"Fact.revision={fact.revision} > 1 requires supersedes "
            f"to be non-empty (correction chain rule v0.3.1)")

    # ── 3. fact_type ───────────────────────────────────────
    if not fact.fact_type or not fact.fact_type.strip():
        errs.append("Fact.fact_type must be non-empty")
    else:
        ft_err = reg.validate_fact_type(fact.fact_type)
        if ft_err is not None:
            errs.append(f"Fact.fact_type: {ft_err}")

    # ── 4. status ──────────────────────────────────────────
    if not is_valid_fact_status(fact.status):
        errs.append(
            f"Fact.status '{fact.status}' is not valid; "
            f"must be one of {sorted(FACT_STATUSES)}")

    # ── 4. value / status consistency ──────────────────────
    errs.extend(_validate_value_status_consistency(fact))

    # ── 5. quantity_kind ────────────────────────────────────
    if not is_valid_quantity_kind(fact.quantity_kind):
        errs.append(
            f"Fact.quantity_kind '{fact.quantity_kind}' is not valid; "
            f"must be one of {sorted(QUANTITY_KINDS)}")

    # ── 6. unit ────────────────────────────────────────────
    if fact.quantity_kind == "qualitative":
        if fact.unit is not None and fact.unit != "":
            errs.append(
                f"Fact with quantity_kind='qualitative' must have "
                f"unit=None, got '{fact.unit}'")
    else:
        if fact.unit is None and fact.status != "missing":
            errs.append(
                f"Fact with quantity_kind='{fact.quantity_kind}' must "
                f"have non-None unit (may be empty string only if "
                f"dimensionless)")

    # ── 7. source_refs ──────────────────────────────────────
    if fact.status in ("filled", "conflict", "rejected", "superseded"):
        if len(fact.source_refs) == 0:
            errs.append(
                f"Fact with status='{fact.status}' must have at least "
                f"one source_ref")

    for i, sr in enumerate(fact.source_refs):
        sub = validate_source_ref(sr)
        for e in sub:
            errs.append(f"Fact.source_refs[{i}]: {e}")

    # ── 8. method ──────────────────────────────────────────
    if not is_valid_method(fact.method):
        errs.append(
            f"Fact.method '{fact.method}' is not valid; "
            f"must be one of {sorted(METHODS)}")

    # ── 9. provenance ───────────────────────────────────────
    if not is_valid_provenance(fact.provenance):
        errs.append(
            f"Fact.provenance '{fact.provenance}' is not valid; "
            f"must be one of {sorted(PROVENANCES)}")

    # ── 10. confidence ──────────────────────────────────────
    if fact.confidence is not None:
        if not isinstance(fact.confidence, (int, float)):
            errs.append(
                f"Fact.confidence must be numeric, got "
                f"{type(fact.confidence).__name__}")
        elif fact.confidence < 0 or fact.confidence > 1:
            errs.append(
                f"Fact.confidence {fact.confidence} must be in "
                f"[0, 1]")

    # ── 11. review_status ────────────────────────────────────
    if not is_valid_review_status(fact.review_status):
        errs.append(
            f"Fact.review_status '{fact.review_status}' is not valid; "
            f"must be one of {sorted(REVIEW_STATUSES)}")

    # ── 12. supersedes semantics (v0.3 §15.5) ───────────────
    errs.extend(_validate_supersedes(fact))

    # ── 13. value_domain for qualitative facts ──────────────
    if fact.quantity_kind == "qualitative":
        if fact.value is not None and fact.value_domain is None:
            errs.append(
                "Fact with quantity_kind='qualitative' should have "
                "value_domain declaring controlled values")

    # ── 14. status=conflict consistency ────────────────────
    if fact.status == "conflict" and fact.value is not None:
        errs.append(
            "Fact.status='conflict' means value is unresolved; "
            "value must be None (use Conflict object for candidates)")

    return errs


# ──────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────

def _validate_value_status_consistency(fact: Fact) -> list[str]:
    """03_CDM v0.3 §15.2: missing → value MUST be None.

    No auto-filling 0, empty string, or any placeholder is allowed.
    """
    errs: list[str] = []

    if fact.status == "missing":
        if fact.value is not None:
            errs.append(
                f"Fact.status='missing' must have value=None, "
                f"got value={fact.value!r}")
        if fact.unit is not None and fact.unit != "":
            errs.append(
                f"Fact.status='missing' must have unit=None, "
                f"got unit={fact.unit!r}")

    elif fact.status == "rejected":
        # rejected fact also shouldn't carry its original value
        if fact.value is not None:
            errs.append(
                f"Fact.status='rejected' should have value=None "
                f"(original value discarded on rejection), "
                f"got value={fact.value!r}")

    elif fact.status == "superseded":
        # superseded old fact keeps its old value for audit trail —
        # value is allowed here. But we check supersedes direction
        # separately in _validate_supersedes.
        pass

    elif fact.status == "filled":
        if fact.value is None:
            errs.append(
                "Fact.status='filled' must have non-None value")

    # conflict handled separately in validate_fact (value must be None)

    return errs


def _validate_supersedes(fact: Fact) -> list[str]:
    """v0.3.1 revision + supersedes semantics (§15.5).

    Rules:
    - superseded fact MUST NOT carry supersedes (direction: NEW→OLD only).
    - revision>1 MUST carry supersedes (checked in validate_fact step 2).
    - supersedes entries must all be valid three-segment fact IDs.
    - v0.3.1: supersedes entries must point to the SAME fact identity
      (same id as fact.id). You cannot use supersedes to point from one
      fact identity to another — that is a Conflict, not a correction.

    Cross-revision chain completeness (revision=N supersedes revision=N-1,
    no skipping) is DEFERRED to the Store layer — the Validator here only
    checks structural correctness. See 03_CDM v0.3.1 §15.5.
    """
    errs: list[str] = []

    if fact.status == "superseded":
        if fact.supersedes is not None:
            errs.append(
                "Fact with status='superseded' must NOT carry "
                "supersedes field — correction direction is "
                "NEW(supersedes) → OLD(superseded). The OLD fact "
                "is the one being replaced; it cannot point back "
                "to its replacer.")

    if fact.supersedes is not None:
        if len(fact.supersedes) == 0:
            errs.append(
                "Fact.supersedes, if set, must be a non-empty list "
                "(empty list is semantically meaningless)")
        for i, old_id in enumerate(fact.supersedes):
            if not old_id or not old_id.strip():
                errs.append(
                    f"Fact.supersedes[{i}] must be non-empty fact_id string")
            else:
                # a) valid three-segment
                err = is_valid_fact_id(old_id)
                if err is not None:
                    errs.append(
                        f"Fact.supersedes[{i}] = '{old_id}': {err}")
                # b) must be the same identity (v0.3.1)
                elif old_id != fact.id:
                    errs.append(
                        f"Fact.supersedes[{i}] = '{old_id}' does not match "
                        f"fact.id = '{fact.id}'. supersedes can only point "
                        f"to previous revisions of the SAME fact identity; "
                        f"pointing to a different fact identity is not a "
                        f"correction (that would be a Conflict).")

    return errs
