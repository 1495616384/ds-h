"""L3 Domain Objects — engineering semantic entities built from Facts.

03_CANONICAL_DATA_MODEL.md §17-28 (v0.3.1).

Five objects this phase:
    Project   — top-level container
    Structure — unified Building / Floor / Axis / Zone / StructureUnit
    Component — engineering component (beam, column, slab, wall)
    Defect    — weak entity, MUST carry host_component_id (crack is a Defect instance)
    Evidence  — traceable link to RawSource + related Facts

Key rules (frozen design):
    - Domain Objects do NOT carry fact values — values are read from L2 Fact layer.
    - Domain Objects do NOT carry status / review_status — both live on Fact.
    - Fact IDs reference Facts via three-segment grammar: fact:<scope>.<instance>.<attr>.
    - Relations are explicit L3 fields (B-class), NOT Facts.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Optional

from .types import SourceRef


# ──────────────────────────────────────────────
# STRUCTURE_TYPES — controlled enum for Structure.structure_type
# 03_CDM §20 — all building/floor/axis/zone/structure_unit are
# Structure instances distinguished by structure_type.
# ──────────────────────────────────────────────

STRUCTURE_TYPES: frozenset[str] = frozenset({
    "building",
    "floor",
    "axis",
    "zone",
    "structure_unit",
})


# ──────────────────────────────────────────────
# Project (§18)
# ──────────────────────────────────────────────

@dataclass
class Project:
    """Top-level engineering project container.

    Allowed scope in fact_ids[]: project only.
    Does NOT store a reverse structure_ids[] — Projects are discovered
    by back-referencing Structure.project_id.
    """
    id: str
    fact_ids: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    # ── Serialization ──

    def to_dict(self) -> dict:
        d: dict[str, Any] = {
            "id": self.id,
            "fact_ids": list(self.fact_ids),
        }
        if self.metadata:
            d["metadata"] = dict(self.metadata)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "Project":
        return cls(
            id=data["id"],
            fact_ids=list(data.get("fact_ids", [])),
            metadata=dict(data.get("metadata", {})),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


# ──────────────────────────────────────────────
# Structure (§20 — unified, not Building)
# ──────────────────────────────────────────────

@dataclass
class Structure:
    """Unified structure hierarchy node — replaces separate Building class.

    structure_type is REQUIRED (not Optional) so validator can determine
    which fact scope is allowed for this instance.

    Scope rules (from design freeze):
        structure_type="building"          → fact_ids may carry fact:building.*
        structure_type=floor/axis/zone/structure_unit → fact_ids MUST be empty

    project_id is REQUIRED — the Project → Structure relation must be
    expressible; Project does NOT carry reverse structure_ids[].
    parent_id is Optional — enables Structure → Structure hierarchy.
    """
    id: str
    structure_type: str
    project_id: str
    parent_id: Optional[str] = None
    fact_ids: list[str] = field(default_factory=list)

    # ── Serialization ──

    def to_dict(self) -> dict:
        d: dict[str, Any] = {
            "id": self.id,
            "structure_type": self.structure_type,
            "project_id": self.project_id,
            "fact_ids": list(self.fact_ids),
        }
        if self.parent_id is not None:
            d["parent_id"] = self.parent_id
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "Structure":
        return cls(
            id=data["id"],
            structure_type=data["structure_type"],
            project_id=data["project_id"],
            parent_id=data.get("parent_id"),
            fact_ids=list(data.get("fact_ids", [])),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


# ──────────────────────────────────────────────
# Component (§21)
# ──────────────────────────────────────────────

@dataclass
class Component:
    """Engineering component (beam, column, slab, wall, etc.).

    defect_ids[] MAY be empty — components without defects are normal.
    parent_structure_id is REQUIRED — every component lives in a Structure.

    Allowed scope in fact_ids[]: component only.
    """
    id: str
    parent_structure_id: str
    defect_ids: list[str] = field(default_factory=list)
    fact_ids: list[str] = field(default_factory=list)

    # ── Serialization ──

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "parent_structure_id": self.parent_structure_id,
            "defect_ids": list(self.defect_ids),
            "fact_ids": list(self.fact_ids),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Component":
        return cls(
            id=data["id"],
            parent_structure_id=data["parent_structure_id"],
            defect_ids=list(data.get("defect_ids", [])),
            fact_ids=list(data.get("fact_ids", [])),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


# ──────────────────────────────────────────────
# Defect (§17 v0.3.1 — weak entity)
# ──────────────────────────────────────────────

@dataclass
class Defect:
    """Weak entity — MUST carry host_component_id.

    crack / corrosion / spall / settlement / etc. are all Defect instances
    distinguished by fact_ids (e.g. fact:defect.C001.pattern = "diagonal"),
    NOT by separate classes.

    Allowed scope in fact_ids[]: defect only.
    """
    id: str
    host_component_id: str
    fact_ids: list[str] = field(default_factory=list)

    # ── Serialization ──

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "host_component_id": self.host_component_id,
            "fact_ids": list(self.fact_ids),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Defect":
        return cls(
            id=data["id"],
            host_component_id=data["host_component_id"],
            fact_ids=list(data.get("fact_ids", [])),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


# ──────────────────────────────────────────────
# Evidence (§28)
# ──────────────────────────────────────────────

@dataclass
class Evidence:
    """Evidence object — bridges L1 RawSource and L2 Facts.

    Carries a mandatory raw_source_id and non-empty source_refs[] list
    for precise locating (image region / doc page / sheet cell).

    related_fact_ids[] MAY cross scopes — Evidence's job is to link a
    raw piece of evidence to whatever Facts it supports, regardless of
    which scope class those Facts belong to.

    related_object_ids[] is Optional — direct Domain Object back-link
    (e.g. a Defect's photo pointing directly to the Defect id).
    """
    id: str
    raw_source_id: str
    source_refs: list[SourceRef] = field(default_factory=list)
    related_fact_ids: list[str] = field(default_factory=list)
    related_object_ids: list[str] = field(default_factory=list)

    # ── Serialization ──

    def to_dict(self) -> dict:
        d: dict[str, Any] = {
            "id": self.id,
            "raw_source_id": self.raw_source_id,
            "source_refs": [sr.to_dict() for sr in self.source_refs],
            "related_fact_ids": list(self.related_fact_ids),
            "related_object_ids": list(self.related_object_ids),
        }
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "Evidence":
        return cls(
            id=data["id"],
            raw_source_id=data["raw_source_id"],
            source_refs=[SourceRef.from_dict(sr)
                         for sr in data.get("source_refs", [])],
            related_fact_ids=list(data.get("related_fact_ids", [])),
            related_object_ids=list(data.get("related_object_ids", [])),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)
