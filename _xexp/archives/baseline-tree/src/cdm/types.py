"""Core data structures for Canonical Data Model.

03_CANONICAL_DATA_MODEL.md v0.3:
    SourceRef, RawSource, Fact, Conflict.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, fields, asdict
from typing import Any, Optional, Union


# ──────────────────────────────────────────────
# SourceRef (L1 → L2 anchor)
# ──────────────────────────────────────────────

@dataclass
class SourceRef:
    """A reference from a Fact back to its source location.

    03_CDM v0.3 §5 / §11.
    Examples:
        { "source_id": "inspection.xlsx", "location": "Sheet1!F23" }
        { "source_id": "project-info.pdf", "location": "page:12" }
        { "source_id": "photo-034.jpg", "location": "full-image" }
    """
    source_id: str
    location: str

    def to_dict(self) -> dict:
        return {"source_id": self.source_id, "location": self.location}

    @classmethod
    def from_dict(cls, data: dict) -> "SourceRef":
        return cls(
            source_id=data["source_id"],
            location=data["location"],
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


# ──────────────────────────────────────────────
# RawSource (L1)
# ──────────────────────────────────────────────

@dataclass
class RawSource:
    """Raw input document record. L1 — read-only, never modified.

    03_CDM v0.3 §3-4.
    """
    source_id: str
    source_type: str     # from RAW_SOURCE_TYPES
    location: Optional[str] = None
    original_path: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        # strip None values for clean JSON
        return {k: v for k, v in d.items() if v is not None}

    @classmethod
    def from_dict(cls, data: dict) -> "RawSource":
        return cls(
            source_id=data["source_id"],
            source_type=data["source_type"],
            location=data.get("location"),
            original_path=data.get("original_path"),
            metadata=data.get("metadata", {}),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


# ──────────────────────────────────────────────
# ConflictCandidate (helper for Conflict)
# ──────────────────────────────────────────────

@dataclass
class ConflictCandidate:
    """One side of a multi-source conflict.

    03_CDM v0.3 §34-35.
    """
    value: Any
    unit: Optional[str]
    quantity_kind: str
    source_ref: SourceRef
    method: str
    provenance: str

    def to_dict(self) -> dict:
        d = asdict(self)
        d["source_ref"] = self.source_ref.to_dict()
        return {k: v for k, v in d.items() if v is not None}

    @classmethod
    def from_dict(cls, data: dict) -> "ConflictCandidate":
        return cls(
            value=data["value"],
            unit=data.get("unit"),
            quantity_kind=data["quantity_kind"],
            source_ref=SourceRef.from_dict(data["source_ref"]),
            method=data["method"],
            provenance=data["provenance"],
        )


# ──────────────────────────────────────────────
# Conflict
# ──────────────────────────────────────────────

@dataclass
class Conflict:
    """Multiple inconsistent candidate values for the same Fact.

    03_CDM v0.3 §33-36.
    First phase: resolution_policy MUST be "manual".
    "Last writer wins" is FORBIDDEN.
    """
    fact_id: str
    candidates: list[ConflictCandidate]
    resolution_policy: str = "manual"
    resolved_by: Optional[str] = None
    resolution: Optional[str] = None

    def to_dict(self) -> dict:
        d: dict[str, Any] = {
            "fact_id": self.fact_id,
            "candidates": [c.to_dict() for c in self.candidates],
            "resolution_policy": self.resolution_policy,
        }
        if self.resolved_by is not None:
            d["resolved_by"] = self.resolved_by
        if self.resolution is not None:
            d["resolution"] = self.resolution
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "Conflict":
        return cls(
            fact_id=data["fact_id"],
            candidates=[ConflictCandidate.from_dict(c)
                        for c in data["candidates"]],
            resolution_policy=data.get("resolution_policy", "manual"),
            resolved_by=data.get("resolved_by"),
            resolution=data.get("resolution"),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


# ──────────────────────────────────────────────
# Fact (L2 — THE core data structure)
# ──────────────────────────────────────────────

class _FactFields:
    """Field name constants — avoids typos in validate.py."""
    ID = "id"
    REVISION = "revision"
    FACT_TYPE = "fact_type"
    VALUE = "value"
    UNIT = "unit"
    QUANTITY_KIND = "quantity_kind"
    SOURCE_REFS = "source_refs"
    METHOD = "method"
    PROVENANCE = "provenance"
    CONFIDENCE = "confidence"
    REVIEW_STATUS = "review_status"
    STATUS = "status"
    SUPERSEDES = "supersedes"
    VALUE_DOMAIN = "value_domain"


# Union type for the polymorphic `value` field
FactValue = Union[float, int, str, bool, None]


@dataclass
class Fact:
    """L2 Fact — the smallest assertion unit.

    03_CANONICAL_DATA_MODEL.md v0.3.1 (v0.3 + D-027).

    Key principles:
    - Fact only describes "what is", NOT "how to write".
    - Value storage: raw value + raw unit + quantity_kind (v0.2 — no SI base).
    - status ∈ {filled, missing, conflict, rejected, superseded}.
    - confidence is DIAGNOSTIC ONLY (v0.2) — NOT a gate.
    - review_status is the HUMAN gate: pending / confirmed / rejected.
    - supersedes (v0.3): NEW fact points to OLD fact_ids it corrects.
    - revision (v0.3.1): version counter OUTSIDE the ID.
        revision=1 is default (initial). revision>1 REQUIRES supersedes.
        Same logical Fact identity: (id, revision).
    """

    # ── Mandatory fields (no defaults) ──────────────────────
    id: str                           # three-segment, frozen grammar
    fact_type: str                    # controlled registry
    value: FactValue                  # polymorphic; None when missing
    unit: Optional[str]               # None for qualitative facts
    quantity_kind: str                # controlled

    # ── v0.3.1: revision (default 1 — must follow all no-default fields) ──
    revision: int = 1                 # version counter OUTSIDE the ID

    # ── Traceability ───────────────────────────────────────
    source_refs: list[SourceRef] = field(default_factory=list)

    # ── Provenance & method ────────────────────────────────
    method: str = "quoted"
    provenance: str = "program"
    confidence: Optional[float] = None      # 0~1, diagnostic only
    review_status: str = "pending"          # human gate

    # ── Lifecycle ──────────────────────────────────────────
    status: str = "filled"

    # ── v0.3: correction semantics ────────────────────────
    supersedes: Optional[list[str]] = None  # NEW fact → OLD ids
    value_domain: Optional[list[str]] = None  # qualitative controlled values

    # ── Serialization ───────────────────────────────────────

    def to_dict(self) -> dict:
        """Convert to dict suitable for JSON serialization."""
        d: dict[str, Any] = {
            "id": self.id,
            "revision": self.revision,
            "fact_type": self.fact_type,
            "value": self.value,
            "unit": self.unit,
            "quantity_kind": self.quantity_kind,
            "source_refs": [sr.to_dict() for sr in self.source_refs],
            "method": self.method,
            "provenance": self.provenance,
            "review_status": self.review_status,
            "status": self.status,
        }
        if self.confidence is not None:
            d["confidence"] = self.confidence
        if self.supersedes is not None:
            d["supersedes"] = list(self.supersedes)
        if self.value_domain is not None:
            d["value_domain"] = list(self.value_domain)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "Fact":
        source_refs = [SourceRef.from_dict(sr)
                       for sr in data.get("source_refs", [])]
        return cls(
            id=data["id"],
            revision=data.get("revision", 1),
            fact_type=data["fact_type"],
            value=data.get("value"),
            unit=data.get("unit"),
            quantity_kind=data.get("quantity_kind"),
            source_refs=source_refs,
            method=data.get("method", "quoted"),
            provenance=data.get("provenance", "program"),
            confidence=data.get("confidence"),
            review_status=data.get("review_status", "pending"),
            status=data.get("status", "filled"),
            supersedes=data.get("supersedes"),
            value_domain=data.get("value_domain"),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)
