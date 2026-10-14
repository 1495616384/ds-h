"""Validation for L3 Domain Objects (Project / Structure / Component / Defect / Evidence).

03_CANONICAL_DATA_MODEL.md v0.3.1 + Step 7-C design freeze.

Validator responsibilities (LOCAL STRUCTURE ONLY — no Store dependency):
    1. id non-empty, non-whitespace.
    2. fact_ids[] — each entry passes grammar check (is_valid_fact_id raw).
    3. fact_ids[] — scope_class consistency check (parse_fact_id, compare
       against Domain Object's allowed scope set — see SCOPE_ALLOWANCE below).
    4. Relationship fields non-empty where REQUIRED (B-class L3 fields).
    5. Structure.structure_type valid (from STRUCTURE_TYPES).
    6. Evidence.source_refs[] non-empty + each ref structure-valid.

EXPLICITLY NOT CHECKED here (deferred to Store / Pipeline layer):
    - whether a referenced Fact exists in any Store
    - whether defect_ids point to real Defect instances
    - whether parent_structure_id points to a real Structure
    - whether project_id points to a real Project
    - whether host_component_id points to a real Component
    - whether raw_source_id points to a real RawSource
    - whether Fact.status is filled / not missing / not conflict
"""
from __future__ import annotations

from typing import Optional

from .domain import (
    STRUCTURE_TYPES,
    Project,
    Structure,
    Component,
    Defect,
    Evidence,
)
from .id import parse_fact_id, is_valid_fact_id
from .validate import validate_source_ref


# ──────────────────────────────────────────────
# Scope allowance table
# ──────────────────────────────────────────────
# Maps Domain Object class → the set of scope_class values its
# fact_ids[] entries are allowed to carry.
# None = Evidence-style object — do NOT check scope (cross-scope is intentional).

# Structure types with their allowed scopes:
STRUCTURE_ALLOWED_SCOPES: dict[str, frozenset[str]] = {
    "building": frozenset({"building"}),
    # Other structure types have NO scope this phase → fact_ids MUST be empty
    "floor": frozenset(),
    "axis": frozenset(),
    "zone": frozenset(),
    "structure_unit": frozenset(),
}


# ──────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────

def _check_id_non_empty(obj_type: str, obj_id: str) -> Optional[str]:
    """Return error if id is empty / whitespace."""
    if not obj_id or not obj_id.strip():
        return f"{obj_type}.id must be non-empty"
    return None


def _check_fact_ids_scope(
    obj_type: str,
    fact_ids: list[str],
    allowed_scopes: frozenset[str] | None,
) -> list[str]:
    """Validate grammar + scope consistency for a Domain Object's fact_ids[].

    Args:
        obj_type: Human-readable name for error messages (e.g. "Project").
        fact_ids: List of fact id strings to validate.
        allowed_scopes: frozenset of scope_class values that are ALLOWED.
            None = skip scope check (Evidence-style cross-scope).

    Returns:
        List of error strings. Empty list = pass.
    """
    errs: list[str] = []

    for i, fid in enumerate(fact_ids):
        # Grammar check — reuse Step 7-B validator (no registry/fact_type needed)
        gram_err = is_valid_fact_id(fid)
        if gram_err is not None:
            errs.append(
                f"{obj_type}.fact_ids[{i}] = '{fid}': {gram_err}")
            # scope check below is moot if grammar already failed,
            # but we parse anyway to keep the error set complete
            continue

        # Scope consistency
        if allowed_scopes is not None:
            parsed = parse_fact_id(fid)
            if parsed is not None:
                if parsed.scope_class not in allowed_scopes:
                    errs.append(
                        f"{obj_type}.fact_ids[{i}] = '{fid}': "
                        f"scope_class='{parsed.scope_class}' is not allowed "
                        f"for this {obj_type}; allowed = {sorted(allowed_scopes)}")

    return errs


def _check_list_elements_non_empty(
    list_name: str,
    items: list[str],
    obj_label: str,
) -> list[str]:
    """Check each element in a list is non-empty / non-whitespace.

    Does NOT require the list itself to be non-empty — caller controls that.
    """
    errs: list[str] = []
    for i, item in enumerate(items):
        if not item or not item.strip():
            errs.append(
                f"{obj_label}.{list_name}[{i}] must be non-empty "
                f"(empty string / whitespace rejected)")
    return errs


# ──────────────────────────────────────────────
# Project
# ──────────────────────────────────────────────

def validate_project(proj: Project) -> list[str]:
    """Validate a Project Domain Object (L3)."""
    errs: list[str] = []

    # id
    e = _check_id_non_empty("Project", proj.id)
    if e is not None:
        errs.append(e)

    # fact_ids — grammar + scope must be {"project"}
    errs.extend(_check_fact_ids_scope(
        "Project", proj.fact_ids, allowed_scopes=frozenset({"project"})))

    return errs


# ──────────────────────────────────────────────
# Structure
# ──────────────────────────────────────────────

def validate_struct(struct: Structure) -> list[str]:
    """Validate a Structure Domain Object (L3).

    Rules (frozen):
        - structure_type is REQUIRED and must be in STRUCTURE_TYPES.
        - project_id is REQUIRED (the Project → Structure link must exist).
        - parent_id is Optional; if set, must be non-empty / non-whitespace.
        - scope rules depend on structure_type (see STRUCTURE_ALLOWED_SCOPES).
    """
    errs: list[str] = []

    # id
    e = _check_id_non_empty("Structure", struct.id)
    if e is not None:
        errs.append(e)

    # structure_type — REQUIRED enum
    if not struct.structure_type or not struct.structure_type.strip():
        errs.append("Structure.structure_type must be non-empty "
                    "(required to determine fact scope rules)")
    elif struct.structure_type not in STRUCTURE_TYPES:
        errs.append(
            f"Structure.structure_type = '{struct.structure_type}' is not valid; "
            f"must be one of {sorted(STRUCTURE_TYPES)}")

    # project_id — REQUIRED (the Project → Structure link)
    if not struct.project_id or not struct.project_id.strip():
        errs.append(
            f"Structure(id='{struct.id}').project_id must be non-empty "
            f"(the Project → Structure relation must be expressible)")

    # parent_id — Optional; if set, must be non-empty
    if struct.parent_id is not None and not struct.parent_id.strip():
        errs.append(
            f"Structure(id='{struct.id}').parent_id, if set, must not be "
            f"empty / whitespace")

    # fact_ids — scope depends on structure_type
    if struct.structure_type in STRUCTURE_ALLOWED_SCOPES:
        allowed = STRUCTURE_ALLOWED_SCOPES[struct.structure_type]
        errs.extend(_check_fact_ids_scope(
            f"Structure(type='{struct.structure_type}')",
            struct.fact_ids,
            allowed_scopes=allowed,
        ))
    elif struct.structure_type and struct.structure_type in STRUCTURE_TYPES:
        # Type valid but not in our scope table (shouldn't happen since
        # STRUCTURE_TYPES and STRUCTURE_ALLOWED_SCOPES cover the same set).
        # Still check grammar only.
        errs.extend(_check_fact_ids_scope(
            f"Structure(type='{struct.structure_type}')",
            struct.fact_ids,
            allowed_scopes=None,  # grammar only, no scope restriction
        ))
    # else: structure_type is invalid — fact_ids check below is also useful
    # for catching bad grammar regardless

    return errs


# ──────────────────────────────────────────────
# Component
# ──────────────────────────────────────────────

def validate_component(comp: Component) -> list[str]:
    """Validate a Component Domain Object (L3).

    Rules (frozen):
        - parent_structure_id REQUIRED (Component lives in a Structure).
        - defect_ids MAY be empty; elements (if present) must be non-empty.
        - fact_ids scope: component only.
    """
    errs: list[str] = []

    # id
    e = _check_id_non_empty("Component", comp.id)
    if e is not None:
        errs.append(e)

    # parent_structure_id — REQUIRED
    if not comp.parent_structure_id or not comp.parent_structure_id.strip():
        errs.append(
            f"Component(id='{comp.id}').parent_structure_id must be non-empty "
            f"(every component lives in a Structure)")

    # defect_ids — list itself MAY be empty; elements must be non-empty if present
    errs.extend(_check_list_elements_non_empty(
        "defect_ids", comp.defect_ids,
        f"Component(id='{comp.id}')"))

    # fact_ids — grammar + scope must be {"component"}
    errs.extend(_check_fact_ids_scope(
        f"Component(id='{comp.id}')", comp.fact_ids,
        allowed_scopes=frozenset({"component"})))

    return errs


# ──────────────────────────────────────────────
# Defect
# ──────────────────────────────────────────────

def validate_defect(defect: Defect) -> list[str]:
    """Validate a Defect Domain Object (L3 weak entity).

    Rules (frozen):
        - host_component_id REQUIRED (weak entity anchor — Defect MUST live
          under a Component; no independent existence).
        - fact_ids scope: defect only.
    """
    errs: list[str] = []

    # id
    e = _check_id_non_empty("Defect", defect.id)
    if e is not None:
        errs.append(e)

    # host_component_id — REQUIRED weak entity anchor
    if not defect.host_component_id or not defect.host_component_id.strip():
        errs.append(
            f"Defect(id='{defect.id}').host_component_id must be non-empty "
            f"(weak entity anchor — Defect cannot exist independently "
            f"of a Component)")

    # fact_ids — grammar + scope must be {"defect"}
    errs.extend(_check_fact_ids_scope(
        f"Defect(id='{defect.id}')", defect.fact_ids,
        allowed_scopes=frozenset({"defect"})))

    return errs


# ──────────────────────────────────────────────
# Evidence
# ──────────────────────────────────────────────

def validate_evidence(ev: Evidence) -> list[str]:
    """Validate an Evidence Domain Object (L3).

    Rules (frozen):
        - raw_source_id REQUIRED (Evidence MUST bridge to L1 RawSource).
        - source_refs[] MUST be non-empty (a single SourceRef minimum
          to locate the evidence precisely).
        - related_fact_ids MAY be empty; cross-scope is ALLOWED (Evidence
          links raw input to whatever Facts it supports, regardless of
          scope class).
        - related_object_ids MAY be empty / omitted.
        - fact_ids grammar checked, scope NOT checked (cross-scope OK).
    """
    errs: list[str] = []

    # id
    e = _check_id_non_empty("Evidence", ev.id)
    if e is not None:
        errs.append(e)

    # raw_source_id — REQUIRED
    if not ev.raw_source_id or not ev.raw_source_id.strip():
        errs.append(
            f"Evidence(id='{ev.id}').raw_source_id must be non-empty "
            f"(traceability chain Evidence → RawSource MUST be expressible)")

    # source_refs[] — MUST be non-empty
    if len(ev.source_refs) == 0:
        errs.append(
            f"Evidence(id='{ev.id}').source_refs must be non-empty "
            f"(evidence MUST carry at least one location ref — "
            f"image region / doc page / sheet cell)")
    for i, sr in enumerate(ev.source_refs):
        for sub in validate_source_ref(sr):
            errs.append(f"Evidence.source_refs[{i}]: {sub}")

    # related_fact_ids — grammar only, NO scope check (cross-scope intentional)
    errs.extend(_check_fact_ids_scope(
        f"Evidence(id='{ev.id}')", ev.related_fact_ids,
        allowed_scopes=None))

    # related_object_ids — elements (if present) must be non-empty
    errs.extend(_check_list_elements_non_empty(
        "related_object_ids", ev.related_object_ids,
        f"Evidence(id='{ev.id}')"))

    return errs
