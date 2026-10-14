"""Comprehensive tests for Canonical Data Model — all normal and failure paths.

03_CANONICAL_DATA_MODEL.md v0.3.
"""
from __future__ import annotations

import json

import pytest

from cdm.registry import (
    SCOPE_CLASSES,
    METHODS,
    PROVENANCES,
    FACT_STATUSES,
    REVIEW_STATUSES,
    QUANTITY_KINDS,
    FactTypeRegistry,
    get_default_registry,
)
from cdm.id import (
    FactID,
    parse_fact_id,
    build_fact_id,
    is_valid_fact_id,
)
from cdm.types import (
    SourceRef,
    RawSource,
    Fact,
    Conflict,
    ConflictCandidate,
)
from cdm.validate import (
    validate_source_ref,
    validate_raw_source,
    validate_fact,
    validate_conflict,
)


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────

@pytest.fixture
def reg() -> FactTypeRegistry:
    return get_default_registry()


@pytest.fixture
def good_source_ref() -> SourceRef:
    return SourceRef(source_id="inspection.xlsx", location="Sheet1!F23")


@pytest.fixture
def good_raw_source() -> RawSource:
    return RawSource(
        source_id="inspection.xlsx",
        source_type="xlsx",
        location="Sheet1",
        original_path="data/inspection.xlsx",
    )


# ══════════════════════════════════════════════
# Registry tests
# ══════════════════════════════════════════════

class TestRegistry:
    def test_fixed_enums_not_empty(self):
        assert len(SCOPE_CLASSES) >= 6
        assert len(METHODS) == 5
        assert len(PROVENANCES) == 3
        assert len(FACT_STATUSES) == 5
        assert len(REVIEW_STATUSES) == 3
        assert len(QUANTITY_KINDS) >= 10

    def test_registry_has_minimum_types(self, reg):
        assert len(reg.all()) >= 10

    def test_known_type_registered(self, reg):
        assert reg.has("component.concrete_strength")
        assert reg.has("building.area")
        assert reg.has("project.name")

    def test_unknown_type_not_registered(self, reg):
        assert not reg.has("component.whatever")
        assert not reg.has("my_invented.type")

    def test_register_rejects_duplicate(self, reg):
        with pytest.raises(ValueError, match="already registered"):
            reg.register("component.concrete_strength", "component",
                         "concrete_strength", "pressure")

    def test_register_rejects_invalid_scope_class(self, reg):
        with pytest.raises(ValueError, match="invalid scope_class"):
            reg.register("xxx.field", "not_a_scope", "field", "count")

    def test_register_rejects_invalid_quantity_kind(self, reg):
        with pytest.raises(ValueError, match="invalid quantity_kind"):
            reg.register("component.foobar", "component", "foobar", "nonsense")


# ══════════════════════════════════════════════
# Fact ID tests
# ══════════════════════════════════════════════

class TestFactID:
    # ── Parse ──
    def test_parse_standard(self):
        fid = parse_fact_id("fact:component.K001.concrete_strength")
        assert fid is not None
        assert fid.scope_class == "component"
        assert fid.instance_key == "K001"
        assert fid.attribute == "concrete_strength"

    def test_parse_attribute_with_dots_REJECTED(self):
        """v0.3.1: attribute MUST be a single controlled name —
        dots inside any segment (including attribute) → parse failure."""
        assert parse_fact_id("fact:component.K001.crack.width") is None

    def test_parse_four_segments_REJECTED(self):
        """v0.3.1: exactly 3 segments — 4 → parse failure."""
        assert parse_fact_id("fact:component.K001.foo.bar") is None

    def test_parse_no_prefix(self):
        assert parse_fact_id("component.K001.area") is None

    def test_parse_too_few_segments(self):
        assert parse_fact_id("fact:component.K001") is None
        assert parse_fact_id("fact:component") is None

    def test_parse_empty(self):
        assert parse_fact_id("") is None

    def test_parse_not_string(self):
        assert parse_fact_id(None) is None
        assert parse_fact_id(123) is None

    # ── Build ──
    def test_build_roundtrip(self):
        raw = build_fact_id("component", "K001", "concrete_strength")
        assert raw == "fact:component.K001.concrete_strength"
        fid = parse_fact_id(raw)
        assert fid.scope_class == "component"
        assert fid.instance_key == "K001"
        assert fid.attribute == "concrete_strength"

    # ── Validate ──
    def test_valid_id(self, reg):
        assert is_valid_fact_id("fact:component.K001.concrete_strength") is None

    def test_defect_scope_class_accepted(self, reg):
        """v0.3.1: defect is a new valid scope_class."""
        assert is_valid_fact_id(
            "fact:defect.C001.width", fact_type="defect.width",
            registry=reg,
        ) is None

    def test_v2_suffix_REJECTED(self, reg):
        """v0.3.1: .vN version suffix is OUT — revision is a Fact field,
        not part of the ID."""
        err = is_valid_fact_id(
            "fact:component.K001.concrete_strength.v2",
            fact_type="component.concrete_strength",
            registry=reg,
        )
        assert err is not None

    def test_invalid_scope_class(self):
        err = is_valid_fact_id("fact:unknown.K001.field")
        assert err is not None
        assert "scope_class" in err

    def test_invalid_format(self):
        err = is_valid_fact_id("fact:only.two")
        assert err is not None

    def test_fact_type_prefix_mismatch_REJECTED(self, reg):
        """v0.3.1 invariant: fact_type first segment MUST equal ID's scope_class."""
        err = is_valid_fact_id(
            "fact:component.K001.concrete_strength",
            fact_type="measurement.average",  # prefix "measurement" ≠ "component"
            registry=reg,
        )
        assert err is not None
        assert "prefix mismatch" in err or "scope_class" in err

    def test_attribute_mismatches_fact_type(self, reg):
        err = is_valid_fact_id(
            "fact:component.K001.crack_width",
            registry=reg,
            fact_type="component.concrete_strength",
        )
        assert err is not None
        assert "attribute" in err.lower()


# ══════════════════════════════════════════════
# SourceRef tests
# ══════════════════════════════════════════════

class TestSourceRef:
    def test_normal(self, good_source_ref):
        errs = validate_source_ref(good_source_ref)
        assert errs == []

    def test_empty_source_id(self):
        sr = SourceRef(source_id="", location="Sheet1!A1")
        errs = validate_source_ref(sr)
        assert len(errs) >= 1

    def test_empty_location(self):
        sr = SourceRef(source_id="xlsx.xlsx", location="")
        errs = validate_source_ref(sr)
        assert len(errs) >= 1

    def test_whitespace_only(self):
        sr = SourceRef(source_id="   ", location="Sheet1!A1")
        errs = validate_source_ref(sr)
        assert len(errs) >= 1

    def test_json_roundtrip(self, good_source_ref):
        s = good_source_ref.to_json()
        assert "inspection.xlsx" in s
        sr2 = SourceRef.from_dict(json.loads(s))
        assert sr2.source_id == good_source_ref.source_id
        assert sr2.location == good_source_ref.location


# ══════════════════════════════════════════════
# RawSource tests
# ══════════════════════════════════════════════

class TestRawSource:
    def test_normal(self, good_raw_source):
        errs = validate_raw_source(good_raw_source)
        assert errs == []

    def test_empty_source_id(self):
        rs = RawSource(source_id="", source_type="xlsx")
        errs = validate_raw_source(rs)
        assert len(errs) >= 1

    def test_invalid_source_type(self):
        rs = RawSource(source_id="test", source_type="not_a_type")
        errs = validate_raw_source(rs)
        assert len(errs) >= 1
        assert "source_type" in errs[0]

    def test_json_roundtrip(self, good_raw_source):
        s = good_raw_source.to_json()
        d = json.loads(s)
        rs2 = RawSource.from_dict(d)
        assert rs2.source_id == good_raw_source.source_id
        assert rs2.source_type == good_raw_source.source_type


# ══════════════════════════════════════════════
# Fact — filled quantitative
# ══════════════════════════════════════════════

class TestFactFilledQuantitative:
    def test_measured_concrete_strength(self, reg, good_source_ref):
        f = Fact(
            id="fact:component.K001.concrete_strength",
            fact_type="component.concrete_strength",
            value=32.4,
            unit="MPa",
            quantity_kind="pressure",
            source_refs=[good_source_ref],
            method="measured",
            provenance="program",
            review_status="confirmed",
            status="filled",
        )
        errs = validate_fact(f, reg)
        assert errs == []

    def test_quoted_building_area(self, reg, good_source_ref):
        f = Fact(
            id="fact:building.B01.area",
            fact_type="building.area",
            value=1250.30,
            unit="m²",
            quantity_kind="area",
            source_refs=[good_source_ref],
            method="quoted",
            provenance="program",
            review_status="pending",
            status="filled",
        )
        errs = validate_fact(f, reg)
        assert errs == []

    def test_computed_average_REMOVED(self):
        """point.average no longer exists in v0.3.1 registry.

        Computation fact_types should be registered as named,
        non-computed-looking fact_types whose attribute is clear
        (e.g. component.concrete_strength is a measured attribute,
        component.concrete_strength_avg would be a computed one —
        NOT in the minimum first-phase set).
        """
        pass  # removed — see registry for current minimum set


# ══════════════════════════════════════════════
# Fact — filled qualitative
# ══════════════════════════════════════════════

class TestFactFilledQualitative:
    # component.id is already in default registry (registered with
    # scope_class="component", attribute_path="id", quantity_kind="qualitative")
    # — no re-registration needed.

    def test_component_id_string(self, reg):
        sr = SourceRef(source_id="drawings.pdf", location="page:5")
        f = Fact(
            id="fact:component.K001.id",
            fact_type="component.id",
            value="K001",
            unit=None,
            quantity_kind="qualitative",
            source_refs=[sr],
            method="quoted",
            provenance="human",
            review_status="confirmed",
            status="filled",
            value_domain=["K001", "K002", "K003"],
        )
        errs = validate_fact(f, reg)
        assert errs == []

    def test_qualitative_with_unit_fails(self, reg):
        """qualitative fact MUST have unit=None."""
        sr = SourceRef(source_id="x.pdf", location="page:1")
        f = Fact(
            id="fact:component.K001.id",
            fact_type="component.id",
            value="K001",
            unit="some_unit",  # wrong!
            quantity_kind="qualitative",
            source_refs=[sr],
            status="filled",
        )
        errs = validate_fact(f, reg)
        assert any("qualitative" in e and "unit" in e for e in errs)


# ══════════════════════════════════════════════
# Fact — missing status (§15.2 critical path)
# ══════════════════════════════════════════════

class TestFactMissing:
    def test_missing_without_value(self, reg):
        """missing + value=None is the ONLY correct way to represent missing."""
        f = Fact(
            id="fact:component.K001.concrete_strength",
            fact_type="component.concrete_strength",
            value=None,
            unit=None,
            quantity_kind="pressure",
            source_refs=[],   # missing fact has no source
            status="missing",
            review_status="pending",
            method="quoted",
            provenance="program",
        )
        errs = validate_fact(f, reg)
        assert errs == []

    def test_missing_with_value_fails(self, reg):
        """§15.2: missing + non-None value → HARD FAIL.
        No silent placeholder filling."""
        f = Fact(
            id="fact:component.K001.concrete_strength",
            fact_type="component.concrete_strength",
            value=0,          # wrong! cannot default to 0
            unit="MPa",
            quantity_kind="pressure",
            source_refs=[],
            status="missing",
            review_status="pending",
            method="quoted",
            provenance="program",
        )
        errs = validate_fact(f, reg)
        assert any("missing" in e and "value=None" in e for e in errs), \
            f"Expected missing+value!=None error, got: {errs}"

    def test_missing_with_empty_string_fails(self, reg):
        """Cannot silently fill missing with empty string either."""
        f = Fact(
            id="fact:building.B01.area",
            fact_type="building.area",
            value="",
            unit="",
            quantity_kind="area",
            source_refs=[],
            status="missing",
            review_status="pending",
        )
        errs = validate_fact(f, reg)
        assert any("missing" in e for e in errs)


# ══════════════════════════════════════════════
# Fact — supersedes / superseded (v0.3 §15.5)
# ══════════════════════════════════════════════

class TestFactSupersedes:
    def test_new_fact_revision_2_valid(self, reg, good_source_ref):
        """v0.3.1: NEW correction fact — SAME id + revision=2 + supersedes."""
        f = Fact(
            id="fact:component.K001.concrete_strength",
            fact_type="component.concrete_strength",
            revision=2,
            value=34.1,
            unit="MPa",
            quantity_kind="pressure",
            source_refs=[good_source_ref],
            supersedes=["fact:component.K001.concrete_strength"],
            status="filled",
            review_status="confirmed",
        )
        errs = validate_fact(f, reg)
        assert errs == []

    def test_old_fact_is_superseded(self, reg, good_source_ref):
        """OLD fact gets status=superseded — NO supersedes field."""
        f = Fact(
            id="fact:component.K001.concrete_strength",
            fact_type="component.concrete_strength",
            revision=1,
            value=32.4,
            unit="MPa",
            quantity_kind="pressure",
            source_refs=[good_source_ref],
            status="superseded",
            review_status="confirmed",
        )
        errs = validate_fact(f, reg)
        assert errs == []

    def test_superseded_with_supersedes_fails(self, reg, good_source_ref):
        """Direction violation: OLD fact pointing to what replaced it."""
        f = Fact(
            id="fact:component.K001.concrete_strength",
            fact_type="component.concrete_strength",
            revision=2,
            value=34.1,
            unit="MPa",
            quantity_kind="pressure",
            source_refs=[good_source_ref],
            supersedes=["fact:component.K001.concrete_strength"],
            status="superseded",  # WRONG
            review_status="confirmed",
        )
        errs = validate_fact(f, reg)
        assert any(
            "superseded" in e.lower() and "supersedes" in e.lower()
            for e in errs
        ), f"Expected superseded+supersedes error, got: {errs}"

    def test_supersedes_different_identity_fails(self, reg, good_source_ref):
        """v0.3.1: supersedes MUST point to SAME fact identity."""
        f = Fact(
            id="fact:component.K001.concrete_strength",
            fact_type="component.concrete_strength",
            revision=2,
            value=34.1,
            unit="MPa",
            quantity_kind="pressure",
            source_refs=[good_source_ref],
            supersedes=["fact:component.K002.concrete_strength"],  # DIFFERENT identity
            status="filled",
            review_status="confirmed",
        )
        errs = validate_fact(f, reg)
        assert any("does not match fact.id" in e for e in errs), \
            f"Expected cross-identity supersedes error, got: {errs}"


# ══════════════════════════════════════════════
# Fact — status invalid
# ══════════════════════════════════════════════

class TestFactStatusInvalid:
    def test_illegal_status(self, reg, good_source_ref):
        f = Fact(
            id="fact:component.K001.concrete_strength",
            fact_type="component.concrete_strength",
            value=32.4,
            unit="MPa",
            quantity_kind="pressure",
            source_refs=[good_source_ref],
            status="invented_status",
        )
        errs = validate_fact(f, reg)
        assert any("status" in e and "not valid" in e.lower() for e in errs)

    def test_filled_value_none_fails(self, reg, good_source_ref):
        f = Fact(
            id="fact:component.K001.concrete_strength",
            fact_type="component.concrete_strength",
            value=None,
            unit="MPa",
            quantity_kind="pressure",
            source_refs=[good_source_ref],
            status="filled",
        )
        errs = validate_fact(f, reg)
        assert any("filled" in e and "non-None" in e for e in errs)

    def test_conflict_value_not_none_fails(self, reg, good_source_ref):
        f = Fact(
            id="fact:component.K001.concrete_strength",
            fact_type="component.concrete_strength",
            value=32.4,  # should be None when status=conflict
            unit="MPa",
            quantity_kind="pressure",
            source_refs=[good_source_ref],
            status="conflict",
        )
        errs = validate_fact(f, reg)
        assert any("conflict" in e and "value" in e for e in errs)


# ══════════════════════════════════════════════
# Fact — illegal method / provenance / review_status
# ══════════════════════════════════════════════

class TestFactMethodProvenance:
    def test_illegal_method(self, reg, good_source_ref):
        f = Fact(
            id="fact:component.K001.concrete_strength",
            fact_type="component.concrete_strength",
            value=32.4,
            unit="MPa",
            quantity_kind="pressure",
            source_refs=[good_source_ref],
            method="guessed",  # not in METHODS
        )
        errs = validate_fact(f, reg)
        assert any("method" in e and "not valid" in e.lower() for e in errs)

    def test_illegal_provenance(self, reg, good_source_ref):
        f = Fact(
            id="fact:component.K001.concrete_strength",
            fact_type="component.concrete_strength",
            value=32.4,
            unit="MPa",
            quantity_kind="pressure",
            source_refs=[good_source_ref],
            provenance="database",  # not in PROVENANCES
        )
        errs = validate_fact(f, reg)
        assert any("provenance" in e for e in errs)

    def test_illegal_review_status(self, reg, good_source_ref):
        f = Fact(
            id="fact:component.K001.concrete_strength",
            fact_type="component.concrete_strength",
            value=32.4,
            unit="MPa",
            quantity_kind="pressure",
            source_refs=[good_source_ref],
            review_status="approved",  # not in REVIEW_STATUSES
        )
        errs = validate_fact(f, reg)
        assert any("review_status" in e for e in errs)


# ══════════════════════════════════════════════
# Fact — confidence bounds
# ══════════════════════════════════════════════

class TestFactConfidence:
    def test_confidence_at_zero(self, reg, good_source_ref):
        f = Fact(
            id="fact:component.K001.concrete_strength",
            fact_type="component.concrete_strength",
            value=32.4,
            unit="MPa",
            quantity_kind="pressure",
            source_refs=[good_source_ref],
            provenance="ai",
            confidence=0.0,
        )
        assert validate_fact(f, reg) == []

    def test_confidence_at_one(self, reg, good_source_ref):
        f = Fact(
            id="fact:component.K001.concrete_strength",
            fact_type="component.concrete_strength",
            value=32.4,
            unit="MPa",
            quantity_kind="pressure",
            source_refs=[good_source_ref],
            provenance="ai",
            confidence=1.0,
        )
        assert validate_fact(f, reg) == []

    def test_confidence_negative_fails(self, reg, good_source_ref):
        f = Fact(
            id="fact:component.K001.concrete_strength",
            fact_type="component.concrete_strength",
            value=32.4,
            unit="MPa",
            quantity_kind="pressure",
            source_refs=[good_source_ref],
            confidence=-0.1,
        )
        errs = validate_fact(f, reg)
        assert any("confidence" in e for e in errs)

    def test_confidence_gt_one_fails(self, reg, good_source_ref):
        f = Fact(
            id="fact:component.K001.concrete_strength",
            fact_type="component.concrete_strength",
            value=32.4,
            unit="MPa",
            quantity_kind="pressure",
            source_refs=[good_source_ref],
            confidence=1.5,
        )
        errs = validate_fact(f, reg)
        assert any("confidence" in e for e in errs)


# ══════════════════════════════════════════════
# Fact — ID / fact_type / quantity_kind failures
# ══════════════════════════════════════════════

class TestFactTypeFailures:
    def test_illegal_fact_type_not_registered(self, reg, good_source_ref):
        f = Fact(
            id="fact:component.K001.concrete_strength",
            fact_type="component.not_registered",
            value=32.4,
            unit="MPa",
            quantity_kind="pressure",
            source_refs=[good_source_ref],
        )
        errs = validate_fact(f, reg)
        assert any("not registered" in e.lower() or "fact_type" in e.lower()
                   for e in errs)

    def test_illegal_quantity_kind(self, reg, good_source_ref):
        f = Fact(
            id="fact:component.K001.concrete_strength",
            fact_type="component.concrete_strength",
            value=32.4,
            unit="MPa",
            quantity_kind="made_up",  # not in QUANTITY_KINDS
            source_refs=[good_source_ref],
        )
        errs = validate_fact(f, reg)
        assert any("quantity_kind" in e for e in errs)

    def test_illegal_fact_id_format(self, reg, good_source_ref):
        f = Fact(
            id="not_a_valid_id",
            fact_type="component.concrete_strength",
            value=32.4,
            unit="MPa",
            quantity_kind="pressure",
            source_refs=[good_source_ref],
        )
        errs = validate_fact(f, reg)
        assert any("id" in e.lower() for e in errs)

    def test_id_attr_path_mismatches_fact_type(self, reg, good_source_ref):
        """id's attribute_path must match registered fact_type."""
        f = Fact(
            id="fact:component.K001.crack_width",  # wrong attr path
            fact_type="component.concrete_strength",  # this means attr = concrete_strength
            value=32.4,
            unit="MPa",
            quantity_kind="pressure",
            source_refs=[good_source_ref],
        )
        errs = validate_fact(f, reg)
        assert any("mismatch" in e.lower() or "attribute_path" in e.lower()
                   for e in errs), f"Expected attr path mismatch, got: {errs}"


# ══════════════════════════════════════════════
# Fact — JSON roundtrip
# ══════════════════════════════════════════════

class TestFactJSON:
    def test_measured_roundtrip(self, reg):
        sr = SourceRef(source_id="inspection.xlsx", location="Sheet1!F23")
        f = Fact(
            id="fact:component.K001.concrete_strength",
            fact_type="component.concrete_strength",
            value=32.4,
            unit="MPa",
            quantity_kind="pressure",
            source_refs=[sr],
            method="measured",
            provenance="program",
            review_status="confirmed",
            status="filled",
        )
        s = f.to_json()
        d = json.loads(s)
        f2 = Fact.from_dict(d)
        assert f2.id == f.id
        assert f2.value == f.value
        assert f2.unit == f.unit
        assert f2.status == f.status
        assert f2.source_refs[0].source_id == "inspection.xlsx"

    def test_missing_roundtrip(self, reg):
        f = Fact(
            id="fact:component.K001.concrete_strength",
            fact_type="component.concrete_strength",
            value=None,
            unit=None,
            quantity_kind="pressure",
            source_refs=[],
            status="missing",
        )
        s = f.to_json()
        d = json.loads(s)
        assert d["value"] is None
        assert d["status"] == "missing"
        f2 = Fact.from_dict(d)
        assert f2.value is None

    def test_supersedes_roundtrip(self, reg, good_source_ref):
        f = Fact(
            id="fact:component.K001.concrete_strength",
            fact_type="component.concrete_strength",
            revision=2,
            value=34.1,
            unit="MPa",
            quantity_kind="pressure",
            source_refs=[good_source_ref],
            supersedes=["fact:component.K001.concrete_strength"],
            status="filled",
        )
        s = f.to_json()
        d = json.loads(s)
        assert d["revision"] == 2
        assert "supersedes" in d
        f2 = Fact.from_dict(d)
        assert f2.revision == 2
        assert f2.supersedes == ["fact:component.K001.concrete_strength"]


# ══════════════════════════════════════════════
# Conflict — happy path (2+ candidates)
# ══════════════════════════════════════════════

class TestConflictValid:
    def setup_method(self):
        self.sr1 = SourceRef(source_id="design.pdf", location="page:8")
        self.sr2 = SourceRef(source_id="inspection.xlsx", location="Sheet1!F23")

    def test_two_candidates(self):
        c1 = ConflictCandidate(
            value=1250.30, unit="m²", quantity_kind="area",
            source_ref=self.sr1, method="quoted", provenance="program",
        )
        c2 = ConflictCandidate(
            value=1280.00, unit="m²", quantity_kind="area",
            source_ref=self.sr2, method="quoted", provenance="program",
        )
        conf = Conflict(
            fact_id="fact:building.B01.area",
            candidates=[c1, c2],
            resolution_policy="manual",
        )
        errs = validate_conflict(conf)
        assert errs == []

    def test_three_candidates(self):
        c1 = ConflictCandidate(
            value=100, unit="x", quantity_kind="count",
            source_ref=self.sr1, method="quoted", provenance="program",
        )
        c2 = ConflictCandidate(
            value=105, unit="x", quantity_kind="count",
            source_ref=self.sr2, method="quoted", provenance="program",
        )
        c3 = ConflictCandidate(
            value=98, unit="x", quantity_kind="count",
            source_ref=self.sr1, method="quoted", provenance="human",
        )
        conf = Conflict(
            fact_id="fact:building.B01.floor_count",
            candidates=[c1, c2, c3],
        )
        assert validate_conflict(conf) == []


# ══════════════════════════════════════════════
# Conflict — failure paths
# ══════════════════════════════════════════════

class TestConflictInvalid:
    def setup_method(self):
        self.sr = SourceRef(source_id="design.pdf", location="page:1")
        self.cc = ConflictCandidate(
            value=1250.0, unit="m²", quantity_kind="area",
            source_ref=self.sr, method="quoted", provenance="program",
        )

    def test_single_candidate_fails(self):
        """Conflict requires multi-source inconsistency —
        only 1 candidate is NOT a conflict."""
        conf = Conflict(
            fact_id="fact:building.B01.area",
            candidates=[self.cc],
        )
        errs = validate_conflict(conf)
        assert any("at least 2" in e or "candidates" in e for e in errs), \
            f"Expected candidate count error, got: {errs}"

    def test_empty_candidates_fails(self):
        conf = Conflict(
            fact_id="fact:building.B01.area",
            candidates=[],
        )
        errs = validate_conflict(conf)
        assert len(errs) >= 1

    def test_non_manual_resolution_policy_fails(self):
        """First phase: resolution_policy MUST be 'manual'."""
        cc2 = ConflictCandidate(
            value=1300.0, unit="m²", quantity_kind="area",
            source_ref=self.sr, method="quoted", provenance="program",
        )
        conf = Conflict(
            fact_id="fact:building.B01.area",
            candidates=[self.cc, cc2],
            resolution_policy="source_priority",  # FORBIDDEN in phase 1
        )
        errs = validate_conflict(conf)
        assert any("manual" in e.lower() for e in errs), \
            f"Expected non-manual policy error, got: {errs}"

    def test_invalid_resolution_policy_fails(self):
        cc2 = ConflictCandidate(
            value=1300.0, unit="m²", quantity_kind="area",
            source_ref=self.sr, method="quoted", provenance="program",
        )
        conf = Conflict(
            fact_id="fact:building.B01.area",
            candidates=[self.cc, cc2],
            resolution_policy="not_a_policy",
        )
        errs = validate_conflict(conf)
        assert any("resolution_policy" in e for e in errs)

    def test_empty_fact_id_fails(self):
        cc2 = ConflictCandidate(
            value=1300.0, unit="m²", quantity_kind="area",
            source_ref=self.sr, method="quoted", provenance="program",
        )
        conf = Conflict(
            fact_id="",
            candidates=[self.cc, cc2],
        )
        errs = validate_conflict(conf)
        assert any("fact_id" in e for e in errs)


# ══════════════════════════════════════════════
# Conflict — JSON roundtrip
# ══════════════════════════════════════════════

class TestConflictJSON:
    def test_roundtrip(self):
        sr1 = SourceRef(source_id="a.pdf", location="page:1")
        sr2 = SourceRef(source_id="b.xlsx", location="Sheet1!A1")
        c1 = ConflictCandidate(
            value=1.0, unit="m", quantity_kind="length",
            source_ref=sr1, method="measured", provenance="program",
        )
        c2 = ConflictCandidate(
            value=1.1, unit="m", quantity_kind="length",
            source_ref=sr2, method="measured", provenance="ai",
        )
        conf = Conflict(
            fact_id="fact:component.K001.crack_width",
            candidates=[c1, c2],
            resolution_policy="manual",
        )
        s = conf.to_json()
        d = json.loads(s)
        conf2 = Conflict.from_dict(d)
        assert conf2.fact_id == conf.fact_id
        assert len(conf2.candidates) == 2
        assert conf2.candidates[0].value == 1.0
        assert conf2.candidates[1].source_ref.source_id == "b.xlsx"


# ══════════════════════════════════════════════
# Defect Facts (v0.3.1 new scope_class)
# ══════════════════════════════════════════════

class TestDefectFacts:
    def test_defect_width_quantitative(self, reg):
        sr = SourceRef(source_id="inspection.xlsx", location="Sheet2!C15")
        f = Fact(
            id="fact:defect.C001.width",
            fact_type="defect.width",
            value=0.15,
            unit="mm",
            quantity_kind="length",
            source_refs=[sr],
            method="measured",
            provenance="program",
            status="filled",
        )
        assert validate_fact(f, reg) == []

    def test_defect_length_quantitative(self, reg):
        sr = SourceRef(source_id="inspection.xlsx", location="Sheet2!B15")
        f = Fact(
            id="fact:defect.C001.length",
            fact_type="defect.length",
            value=2.3,
            unit="m",
            quantity_kind="length",
            source_refs=[sr],
            method="measured",
            provenance="program",
            status="filled",
        )
        assert validate_fact(f, reg) == []

    def test_defect_pattern_qualitative(self, reg):
        sr = SourceRef(source_id="photo-034.jpg", location="full-image")
        f = Fact(
            id="fact:defect.C001.pattern",
            fact_type="defect.pattern",
            value="diagonal",
            unit=None,
            quantity_kind="qualitative",
            source_refs=[sr],
            method="observed",
            provenance="ai",
            status="filled",
            value_domain=["transverse", "longitudinal", "diagonal", "random"],
        )
        errs = validate_fact(f, reg)
        assert errs == []

    def test_defect_judgement_qualitative(self, reg):
        sr = SourceRef(source_id="onsite-record.docx", location="page:4")
        f = Fact(
            id="fact:defect.C001.judgement",
            fact_type="defect.judgement",
            value="load_induced",
            unit=None,
            quantity_kind="qualitative",
            source_refs=[sr],
            method="inferred",
            provenance="human",
            status="filled",
            value_domain=["load_induced", "temperature", "shrinkage",
                           "settlement", "unknown"],
        )
        assert validate_fact(f, reg) == []

    def test_defect_present_boolean(self, reg):
        sr = SourceRef(source_id="photo-034.jpg", location="full-image")
        f = Fact(
            id="fact:defect.C001.present",
            fact_type="defect.present",
            value=True,
            unit="",  # dimensionless → empty string allowed
            quantity_kind="dimensionless",
            source_refs=[sr],
            method="observed",
            provenance="ai",
            status="filled",
        )
        assert validate_fact(f, reg) == []

    def test_defect_invalid_attribute_fails(self, reg):
        f = Fact(
            id="fact:defect.C001.unknown_attr",
            fact_type="defect.unknown_attr",
            value=1.0,
            unit="mm",
            quantity_kind="length",
            source_refs=[SourceRef("x.xlsx", "A1")],
        )
        errs = validate_fact(f, reg)
        assert any("not registered" in e.lower() for e in errs)
