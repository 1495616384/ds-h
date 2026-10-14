"""Controlled vocabularies and FactTypeRegistry.

All value domains defined in 03_CANONICAL_DATA_MODEL.md v0.3 §8-§16.
These are hard-coded constants — no dynamic modification allowed.
"""
from __future__ import annotations

from typing import Optional


# ──────────────────────────────────────────────
# Fixed enums — defined in 03_CDM v0.3 §8-§16
# ──────────────────────────────────────────────

# §8.1 — fact:<scope_class>.<instance_key>.<attribute_path>
SCOPE_CLASSES: frozenset[str] = frozenset({
    "project",
    "building",
    "component",
    "defect",
    "point",
    "sample",
    "material",
})

# §12 — how was this fact obtained
METHODS: frozenset[str] = frozenset({
    "measured",   # instrument measurement
    "observed",   # on-site / image recognition
    "computed",   # program calculation
    "quoted",     # direct quote from source
    "inferred",   # derived from other info
})

# §13 — where did this fact come from
PROVENANCES: frozenset[str] = frozenset({
    "program",
    "ai",
    "human",
})

# §15 — fact lifecycle state
FACT_STATUSES: frozenset[str] = frozenset({
    "filled",
    "missing",
    "conflict",
    "rejected",
    "superseded",
})

# §8 — human review gate
REVIEW_STATUSES: frozenset[str] = frozenset({
    "pending",
    "confirmed",
    "rejected",
})

# §10 — dimension / quantity_kind (for dimensional consistency check)
# v0.2: must coexist with raw value + raw unit (no SI base storage).
QUANTITY_KINDS: frozenset[str] = frozenset({
    # Core dimensional kinds
    "length",
    "area",
    "volume",
    "mass",
    "force",
    "pressure",
    "displacement",
    "velocity",
    "frequency",
    "time",
    "temperature",
    "strain",
    "stress",
    # Non-dimensional
    "ratio",         # percentage, ratio
    "count",         # integer count
    "dimensionless", # pure number with no dimension
    # Qualitative
    "qualitative",   # non-numeric controlled value (v0.2)
})


def is_valid_scope_class(value: str) -> bool:
    return value in SCOPE_CLASSES


def is_valid_method(value: str) -> bool:
    return value in METHODS


def is_valid_provenance(value: str) -> bool:
    return value in PROVENANCES


def is_valid_fact_status(value: str) -> bool:
    return value in FACT_STATUSES


def is_valid_review_status(value: str) -> bool:
    return value in REVIEW_STATUSES


def is_valid_quantity_kind(value: str) -> bool:
    return value in QUANTITY_KINDS


# ──────────────────────────────────────────────
# RawSource source_type enum
# ──────────────────────────────────────────────

RAW_SOURCE_TYPES: frozenset[str] = frozenset({
    "xlsx",
    "csv",
    "docx",
    "pdf",
    "txt",
    "image",
    "spec",       # 标准规范
    "template",   # Word 报告模板
    "historical", # 历史报告
    "manual",     # 人工输入
})


def is_valid_raw_source_type(value: str) -> bool:
    return value in RAW_SOURCE_TYPES


# ──────────────────────────────────────────────
# Conflict resolution_policy (§36)
# ──────────────────────────────────────────────

RESOLUTION_POLICIES: frozenset[str] = frozenset({
    "manual",           # 第一阶段唯一允许值
    "source_priority",  # 预留钩子，不实现
    "date_latest",      # 预留钩子，不实现
})


def is_valid_resolution_policy(value: str) -> bool:
    return value in RESOLUTION_POLICIES


# ──────────────────────────────────────────────
# FactTypeRegistry
# ──────────────────────────────────────────────

# Registry entry describes a single registered fact_type.
# fact_type string format: "<scope_class>.<attribute_path>"
# e.g. "component.concrete_strength"
class FactTypeEntry:
    """A single registered fact_type entry."""

    __slots__ = ("fact_type", "scope_class", "attribute_path",
                 "quantity_kind", "description")

    def __init__(self, fact_type: str, scope_class: str, attribute_path: str,
                 quantity_kind: str, description: str = ""):
        self.fact_type = fact_type
        self.scope_class = scope_class
        self.attribute_path = attribute_path
        self.quantity_kind = quantity_kind
        self.description = description


class FactTypeRegistry:
    """Controlled registry of fact_type strings.

    03_CDM v0.3 §8.1: attribute_path MUST come from the controlled registry,
    must not be freely invented at extraction time.
    """

    def __init__(self) -> None:
        self._entries: dict[str, FactTypeEntry] = {}

    # ── register ────────────────────────────────────────────

    def register(self, fact_type: str, scope_class: str,
                 attribute_path: str, quantity_kind: str,
                 description: str = "") -> FactTypeEntry:
        """Register a new fact_type. Fails if already registered or
        if scope_class / quantity_kind is invalid.
        """
        if not fact_type:
            raise ValueError("fact_type must be non-empty")
        if fact_type in self._entries:
            raise ValueError(f"fact_type already registered: {fact_type}")
        if not is_valid_scope_class(scope_class):
            raise ValueError(
                f"invalid scope_class '{scope_class}' for fact_type '{fact_type}'")
        if not is_valid_quantity_kind(quantity_kind):
            raise ValueError(
                f"invalid quantity_kind '{quantity_kind}' for fact_type '{fact_type}'")
        if not attribute_path:
            raise ValueError("attribute_path must be non-empty")

        entry = FactTypeEntry(
            fact_type=fact_type,
            scope_class=scope_class,
            attribute_path=attribute_path,
            quantity_kind=quantity_kind,
            description=description,
        )
        self._entries[fact_type] = entry
        return entry

    # ── query ───────────────────────────────────────────────

    def get(self, fact_type: str) -> Optional[FactTypeEntry]:
        return self._entries.get(fact_type)

    def has(self, fact_type: str) -> bool:
        return fact_type in self._entries

    def all(self) -> dict[str, FactTypeEntry]:
        return dict(self._entries)

    # ── validate ────────────────────────────────────────────

    def validate_fact_type(self, fact_type: str) -> Optional[str]:
        """Return error message if fact_type is not registered, else None."""
        if not fact_type:
            return "fact_type must be non-empty"
        if fact_type not in self._entries:
            return f"fact_type '{fact_type}' is not registered"
        return None

    def validate_id_against_fact_type(
        self, fact_id_attr_path: str, fact_type: str
    ) -> Optional[str]:
        """Check that the attribute_path portion of a Fact ID is
        derivable from the registered fact_type.

        03_CDM v0.3 §8.1:
        fact_type "component.concrete_strength" ↔ attribute_path "concrete_strength"
        in id "fact:component.K001.concrete_strength"
        """
        entry = self._entries.get(fact_type)
        if entry is None:
            return f"fact_type '{fact_type}' is not registered"
        if entry.attribute_path != fact_id_attr_path:
            return (
                f"attribute_path mismatch: Fact ID segment '{fact_id_attr_path}' "
                f"does not match fact_type '{fact_type}' → attribute_path "
                f"'{entry.attribute_path}'"
            )
        return None


# ──────────────────────────────────────────────
# Default registry (populated with minimum first-phase types)
# ──────────────────────────────────────────────

def _build_default_registry() -> FactTypeRegistry:
    """Minimum fact_type set needed for first-phase CDM validation."""
    reg = FactTypeRegistry()

    # project-level
    reg.register("project.name", "project", "name", "qualitative",
                 "project name (string)")
    reg.register("project.id", "project", "id", "qualitative",
                 "project identifier (string)")

    # building-level
    reg.register("building.area", "building", "area", "area",
                 "floor area (㎡)")
    reg.register("building.floor_count", "building", "floor_count", "count",
                 "number of floors")
    reg.register("building.year", "building", "year", "time",
                 "construction year")
    reg.register("building.id", "building", "id", "qualitative",
                 "building identifier")

    # component-level (primary first-phase usage)
    reg.register("component.id", "component", "id", "qualitative",
                 "component identifier e.g. K001")
    reg.register("component.concrete_strength", "component",
                 "concrete_strength", "pressure",
                 "measured concrete cube strength (MPa)")

    # defect-level (v0.3.1: new scope_class replacing standalone crack)
    reg.register("defect.id", "defect", "id", "qualitative",
                 "defect identifier e.g. C001")
    reg.register("defect.width", "defect", "width", "length",
                 "maximum defect width (mm)")
    reg.register("defect.length", "defect", "length", "length",
                 "defect length (m)")
    reg.register("defect.pattern", "defect", "pattern", "qualitative",
                 "defect orientation pattern (diagonal, transverse, ...)")
    reg.register("defect.judgement", "defect", "judgement", "qualitative",
                 "engineering judgement of defect cause")
    reg.register("defect.present", "defect", "present", "dimensionless",
                 "boolean presence of defect")

    # point-level
    reg.register("point.id", "point", "id", "qualitative",
                 "measurement point identifier")

    # sample-level
    reg.register("sample.id", "sample", "id", "qualitative",
                 "sample identifier")

    return reg


_default_registry: Optional[FactTypeRegistry] = None


def get_default_registry() -> FactTypeRegistry:
    """Return the singleton default FactTypeRegistry."""
    global _default_registry
    if _default_registry is None:
        _default_registry = _build_default_registry()
    return _default_registry
