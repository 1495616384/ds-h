"""Canonical Data Model (CDM) package.

v0.3 implementation of the foundational data structures.

Step 7-B: SourceRef, RawSource, Fact, Conflict.
Step 7-C: Project, Structure, Component, Defect, Evidence (L3 Domain Objects).
"""
from .registry import (
    SCOPE_CLASSES,
    METHODS,
    PROVENANCES,
    FACT_STATUSES,
    REVIEW_STATUSES,
    QUANTITY_KINDS,
    FactTypeRegistry,
    get_default_registry,
)
from .id import FactID, parse_fact_id, build_fact_id, is_valid_fact_id
from .types import (
    SourceRef,
    RawSource,
    Fact,
    Conflict,
    ConflictCandidate,
)
# Step 7-C: L3 Domain Objects (domain MUST come before domain_validate
# because domain_validate imports from domain).
from .domain import (
    STRUCTURE_TYPES,
    Project,
    Structure,
    Component,
    Defect,
    Evidence,
)
from .domain_validate import (
    validate_project,
    validate_struct,
    validate_component,
    validate_defect,
    validate_evidence,
)

__all__ = [
    # Registry (Step 7-B)
    "SCOPE_CLASSES",
    "METHODS",
    "PROVENANCES",
    "FACT_STATUSES",
    "REVIEW_STATUSES",
    "QUANTITY_KINDS",
    "FactTypeRegistry",
    "get_default_registry",
    # ID (Step 7-B)
    "FactID",
    "parse_fact_id",
    "build_fact_id",
    "is_valid_fact_id",
    # Types (Step 7-B)
    "SourceRef",
    "RawSource",
    "Fact",
    "Conflict",
    "ConflictCandidate",
    # Domain Objects (Step 7-C)
    "STRUCTURE_TYPES",
    "Project",
    "Structure",
    "Component",
    "Defect",
    "Evidence",
    # Domain validators (Step 7-C)
    "validate_project",
    "validate_struct",
    "validate_component",
    "validate_defect",
    "validate_evidence",
]
