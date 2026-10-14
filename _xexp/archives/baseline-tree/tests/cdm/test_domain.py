"""Comprehensive tests for L3 Domain Objects — Step 7-C.

Covers: Project / Structure / Component / Defect / Evidence.

Scope consistency rules (frozen):
    Project                    → fact:project.* only
    Structure(type="building") → fact:building.* only
    Structure(other types)     → fact_ids MUST be empty this phase
    Component                  → fact:component.* only
    Defect                     → fact:defect.* only
    Evidence                   → scope-agnostic (cross-scope is intentional)

Step 7-B tests MUST remain untouched — this file only adds new tests.
"""
from __future__ import annotations

import json

import pytest

from cdm.domain import (
    STRUCTURE_TYPES,
    Project,
    Structure,
    Component,
    Defect,
    Evidence,
)
from cdm.domain_validate import (
    validate_project,
    validate_struct,
    validate_component,
    validate_defect,
    validate_evidence,
)
from cdm.types import SourceRef


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────

@pytest.fixture
def good_sr() -> SourceRef:
    return SourceRef(source_id="photo-034.jpg", location="full-image")


@pytest.fixture
def empty_sr() -> SourceRef:
    return SourceRef(source_id="", location="")


# ══════════════════════════════════════════════
# STRUCTURE_TYPES enum (not a Domain Object test)
# ══════════════════════════════════════════════

class TestStructureTypesEnum:
    def test_all_five_types_present(self):
        assert STRUCTURE_TYPES == frozenset({
            "building", "floor", "axis", "zone", "structure_unit",
        })

    def test_no_structure_scope_class_in_registry(self):
        """fact:structure.* must NEVER be a valid scope — 'structure' is
        NOT in the Step 7-B frozen scope_class enum.

        This test guards against accidentally adding a new scope_class
        just because we have a Domain Object called Structure.
        """
        from cdm.registry import SCOPE_CLASSES
        assert "structure" not in SCOPE_CLASSES


# ══════════════════════════════════════════════
# Project (6 cases)
# ══════════════════════════════════════════════

class TestProject:
    def test_p1_minimal_valid(self):
        """P-1: id + empty fact_ids = valid."""
        p = Project(id="PROJ01", fact_ids=[])
        assert validate_project(p) == []

    def test_p2_empty_id_fails(self):
        """P-2: id='' → invalid."""
        p = Project(id="", fact_ids=[])
        errs = validate_project(p)
        assert any("id" in e and "non-empty" in e for e in errs)

    def test_p3_valid_project_scopes(self):
        """P-3: project fact_ids = valid."""
        p = Project(id="PROJ01", fact_ids=[
            "fact:project.PROJ01.name",
            "fact:project.PROJ01.id",
        ])
        assert validate_project(p) == []

    def test_p4_component_scope_fails(self):
        """P-4: Project carrying component Fact → scope mismatch."""
        p = Project(id="PROJ01", fact_ids=[
            "fact:component.K001.concrete_strength",
        ])
        errs = validate_project(p)
        assert any("scope_class" in e and "component" in e for e in errs), \
            f"Expected scope mismatch error, got: {errs}"

    def test_p5_defect_scope_fails(self):
        """P-5: Project carrying defect Fact → scope mismatch."""
        p = Project(id="PROJ01", fact_ids=[
            "fact:defect.C001.width",
        ])
        errs = validate_project(p)
        assert any("scope_class" in e and "defect" in e for e in errs), \
            f"Expected scope mismatch error, got: {errs}"

    def test_p6_illegal_fact_id_format(self):
        """P-6: fact_ids with broken grammar."""
        p = Project(id="PROJ01", fact_ids=["not_a_valid_id"])
        errs = validate_project(p)
        assert any("format" in e.lower() or "Fact ID" in e for e in errs)


# ══════════════════════════════════════════════
# Structure (11 cases)
# ══════════════════════════════════════════════

class TestStructure:
    # ── structure_type="building" ──

    def test_s1_building_empty_facts(self):
        """S-1: building + fact_ids=[] + project_id → valid."""
        s = Structure(
            id="B01", structure_type="building",
            project_id="PROJ01", parent_id=None, fact_ids=[],
        )
        assert validate_struct(s) == []

    def test_s2_building_with_building_scope(self):
        """S-2: building + fact:building.* → valid."""
        s = Structure(
            id="B01", structure_type="building",
            project_id="PROJ01",
            fact_ids=["fact:building.B01.area", "fact:building.B01.id"],
        )
        assert validate_struct(s) == []

    # ── structure_type="floor" ──

    def test_s3_floor_empty_facts(self):
        """S-3: floor + fact_ids=[] + parent_id → valid."""
        s = Structure(
            id="F1", structure_type="floor",
            project_id="PROJ01", parent_id="B01", fact_ids=[],
        )
        assert validate_struct(s) == []

    def test_s4_floor_carrying_facts_fails(self):
        """S-4 REVISED: floor + any fact_ids → INVALID this phase.

        Floor does not have its own scope_class yet. fact_ids MUST be empty.
        """
        s = Structure(
            id="F1", structure_type="floor",
            project_id="PROJ01", parent_id="B01",
            fact_ids=["fact:building.B01.area"],  # ANY fact_id is wrong
        )
        errs = validate_struct(s)
        assert len(errs) >= 1
        assert any("floor" in e and "scope" in e.lower() or "not allowed" in e.lower()
                   for e in errs) or any(
                       "empty" in e.lower() or "allowed" in e.lower()
                       for e in errs), f"Expected floor fact_ids mismatch error, got: {errs}"

    # ── structure_type validation ──

    def test_s5_empty_structure_type_fails(self):
        """S-5: structure_type='' → invalid (required field)."""
        s = Structure(
            id="B01", structure_type="",  # empty string, not Optional
            project_id="PROJ01",
        )
        errs = validate_struct(s)
        assert any("structure_type" in e and "non-empty" in e for e in errs)

    def test_s6_illegal_structure_type_fails(self):
        """S-6: structure_type='illegal_type' → invalid enum."""
        s = Structure(
            id="B01", structure_type="illegal_type",
            project_id="PROJ01",
        )
        errs = validate_struct(s)
        assert any("structure_type" in e and "not valid" in e for e in errs)

    # ── fact:structure.* is NEVER valid ──

    def test_s7_fact_structure_scope_fails(self):
        """S-7: fact:structure.* → scope_class doesn't exist → grammar fails."""
        s = Structure(
            id="B01", structure_type="building",
            project_id="PROJ01",
            fact_ids=["fact:structure.F1.area"],  # 'structure' not in SCOPE_CLASSES
        )
        errs = validate_struct(s)
        # grammar check fails because "structure" is not a valid scope_class
        assert any("scope_class" in e.lower() or "invalid" in e.lower()
                   for e in errs), \
            f"Expected structure scope_class error, got: {errs}"

    # ── Scope mismatch for building ──

    def test_s8_building_carrying_component_scope_fails(self):
        """S-8: building + fact:component.* → scope mismatch."""
        s = Structure(
            id="B01", structure_type="building",
            project_id="PROJ01",
            fact_ids=["fact:component.K001.id"],
        )
        errs = validate_struct(s)
        assert any("scope_class" in e and "component" in e for e in errs), \
            f"Expected building scope mismatch, got: {errs}"

    # ── project_id required ──

    def test_s9_building_with_project_id_valid(self):
        """S-9: building + non-empty project_id → valid."""
        s = Structure(
            id="B01", structure_type="building",
            project_id="PROJ01",
        )
        assert validate_struct(s) == []

    def test_s10_building_empty_project_id_fails(self):
        """S-10: building + project_id='' → invalid."""
        s = Structure(
            id="B01", structure_type="building",
            project_id="",
        )
        errs = validate_struct(s)
        assert any("project_id" in e and "non-empty" in e for e in errs)

    # ── id empty ──

    def test_s11_empty_id_fails(self):
        s = Structure(
            id="", structure_type="building",
            project_id="PROJ01",
        )
        errs = validate_struct(s)
        assert any("id" in e and "non-empty" in e for e in errs)

    # ── parent_id edge cases ──

    def test_s12_floor_parent_id_none_is_valid(self):
        """floor can be a sub-level with parent_id=None (top-level floor)."""
        s = Structure(
            id="F1", structure_type="floor",
            project_id="PROJ01", parent_id=None, fact_ids=[],
        )
        assert validate_struct(s) == []

    def test_s13_parent_id_empty_string_fails(self):
        """parent_id, if set, must not be whitespace."""
        s = Structure(
            id="F1", structure_type="floor",
            project_id="PROJ01", parent_id="   ", fact_ids=[],
        )
        errs = validate_struct(s)
        assert any("parent_id" in e and "empty" in e.lower() for e in errs)


# ══════════════════════════════════════════════
# Component (10 cases)
# ══════════════════════════════════════════════

class TestComponent:
    def test_c1_empty_defect_ids_is_valid(self):
        """C-1 — KEY: defect_ids=[] MUST be legal (no defects)."""
        c = Component(
            id="K001", parent_structure_id="B01",
            defect_ids=[], fact_ids=[],
        )
        assert validate_component(c) == []

    def test_c2_one_defect_id(self):
        """C-2: defect_ids=['C001'] → valid."""
        c = Component(
            id="K001", parent_structure_id="B01",
            defect_ids=["C001"], fact_ids=[],
        )
        assert validate_component(c) == []

    def test_c3_multiple_defect_ids(self):
        """C-3: defect_ids=['C001', 'C002'] → valid."""
        c = Component(
            id="K001", parent_structure_id="B01",
            defect_ids=["C001", "C002"], fact_ids=[],
        )
        assert validate_component(c) == []

    def test_c4_empty_string_in_defect_ids_fails(self):
        """C-4: defect_ids=[''] → invalid list element."""
        c = Component(
            id="K001", parent_structure_id="B01",
            defect_ids=[""], fact_ids=[],
        )
        errs = validate_component(c)
        assert any("defect_ids" in e and "non-empty" in e for e in errs)

    def test_c5_empty_parent_structure_id_fails(self):
        """C-5: parent_structure_id='' → invalid."""
        c = Component(
            id="K001", parent_structure_id="",
            defect_ids=[], fact_ids=[],
        )
        errs = validate_component(c)
        assert any("parent_structure_id" in e and "non-empty" in e for e in errs)

    def test_c6_component_scope_ok(self):
        """C-7: fact:component.* → valid scope."""
        c = Component(
            id="K001", parent_structure_id="B01",
            defect_ids=[],
            fact_ids=["fact:component.K001.id",
                      "fact:component.K001.concrete_strength"],
        )
        assert validate_component(c) == []

    def test_c7_defect_scope_fails(self):
        """C-8: Component carrying defect Fact → scope mismatch."""
        c = Component(
            id="K001", parent_structure_id="B01",
            defect_ids=[],
            fact_ids=["fact:defect.C001.width"],
        )
        errs = validate_component(c)
        assert any("scope_class" in e and "defect" in e for e in errs)

    def test_c8_project_scope_fails(self):
        """C-9: Component carrying project Fact → scope mismatch."""
        c = Component(
            id="K001", parent_structure_id="B01",
            defect_ids=[],
            fact_ids=["fact:project.PROJ01.name"],
        )
        errs = validate_component(c)
        assert any("scope_class" in e and "project" in e for e in errs)

    def test_c9_empty_id_fails(self):
        """C-10: id='' → invalid."""
        c = Component(
            id="", parent_structure_id="B01",
            defect_ids=[], fact_ids=[],
        )
        errs = validate_component(c)
        assert any("id" in e and "non-empty" in e for e in errs)

    def test_c10_illegal_fact_format(self):
        c = Component(
            id="K001", parent_structure_id="B01",
            defect_ids=[],
            fact_ids=["broken_id"],
        )
        errs = validate_component(c)
        assert any("Fact ID" in e for e in errs)


# ══════════════════════════════════════════════
# Defect (7 cases — weak entity)
# ══════════════════════════════════════════════

class TestDefect:
    def test_d1_minimal_valid(self):
        """D-1: host_component_id + empty fact_ids → valid."""
        d = Defect(id="C001", host_component_id="K001", fact_ids=[])
        assert validate_defect(d) == []

    def test_d2_with_defect_scope_facts(self):
        """D-2: fact:defect.* → valid scope."""
        d = Defect(
            id="C001", host_component_id="K001",
            fact_ids=["fact:defect.C001.width",
                      "fact:defect.C001.pattern"],
        )
        assert validate_defect(d) == []

    def test_d3_empty_host_component_id_fails(self):
        """D-3: host_component_id='' → invalid."""
        d = Defect(id="C001", host_component_id="", fact_ids=[])
        errs = validate_defect(d)
        assert any("host_component_id" in e and "non-empty" in e for e in errs)

    def test_d4_component_scope_fails(self):
        """D-6: Defect carrying component Fact → scope mismatch."""
        d = Defect(
            id="C001", host_component_id="K001",
            fact_ids=["fact:component.K001.id"],
        )
        errs = validate_defect(d)
        assert any("scope_class" in e and "component" in e for e in errs)

    def test_d5_project_scope_fails(self):
        """D-7: Defect carrying project Fact → scope mismatch."""
        d = Defect(
            id="C001", host_component_id="K001",
            fact_ids=["fact:project.PROJ01.name"],
        )
        errs = validate_defect(d)
        assert any("scope_class" in e and "project" in e for e in errs)

    def test_d6_empty_id_fails(self):
        d = Defect(id="", host_component_id="K001", fact_ids=[])
        errs = validate_defect(d)
        assert any("id" in e and "non-empty" in e for e in errs)

    def test_d7_illegal_fact_format(self):
        d = Defect(
            id="C001", host_component_id="K001",
            fact_ids=["bad_id"],
        )
        errs = validate_defect(d)
        assert any("Fact ID" in e for e in errs)


# ══════════════════════════════════════════════
# Evidence (8 cases)
# ══════════════════════════════════════════════

class TestEvidence:
    def test_e1_minimal_valid(self, good_sr):
        """E-1: raw_source_id + source_refs=[SR] + empty related_fact_ids."""
        ev = Evidence(
            id="E001", raw_source_id="photo-034.jpg",
            source_refs=[good_sr], related_fact_ids=[],
        )
        assert validate_evidence(ev) == []

    def test_e2_cross_scope_related_fact_ids_allowed(self, good_sr):
        """E-2: Evidence CAN link across scopes (cross-scope is intentional)."""
        ev = Evidence(
            id="E001", raw_source_id="photo-034.jpg",
            source_refs=[good_sr],
            related_fact_ids=[
                "fact:defect.C001.width",        # defect scope
                "fact:component.K001.concrete_strength",  # component scope
                "fact:project.PROJ01.id",        # project scope
            ],
        )
        assert validate_evidence(ev) == []  # SCOPE NOT CHECKED here

    def test_e3_empty_raw_source_id_fails(self, good_sr):
        """E-4: raw_source_id='' → invalid."""
        ev = Evidence(
            id="E001", raw_source_id="",
            source_refs=[good_sr], related_fact_ids=[],
        )
        errs = validate_evidence(ev)
        assert any("raw_source_id" in e and "non-empty" in e for e in errs)

    def test_e4_illegal_fact_format_in_related(self, good_sr):
        """E-5: related_fact_ids with broken grammar."""
        ev = Evidence(
            id="E001", raw_source_id="photo-034.jpg",
            source_refs=[good_sr],
            related_fact_ids=["not_a_fact_id"],
        )
        errs = validate_evidence(ev)
        assert any("Fact ID" in e for e in errs)

    def test_e5_optional_related_object_ids_defaults_to_empty(self, good_sr):
        """E-6: not passing related_object_ids → defaults to [] → valid."""
        ev = Evidence(
            id="E001", raw_source_id="photo-034.jpg",
            source_refs=[good_sr], related_fact_ids=[],
            # no related_object_ids — default []
        )
        assert validate_evidence(ev) == []

    def test_e6_source_refs_empty_fails(self):
        """E-7: source_refs=[] → invalid (must carry at least one location)."""
        ev = Evidence(
            id="E001", raw_source_id="photo-034.jpg",
            source_refs=[], related_fact_ids=[],
        )
        errs = validate_evidence(ev)
        assert any("source_refs" in e and "non-empty" in e for e in errs)

    def test_e7_source_refs_invalid_content_fails(self, empty_sr):
        """source_refs with empty source_id/location → invalid."""
        ev = Evidence(
            id="E001", raw_source_id="photo-034.jpg",
            source_refs=[empty_sr], related_fact_ids=[],
        )
        errs = validate_evidence(ev)
        assert any("source_refs" in e for e in errs)

    def test_e8_empty_id_fails(self, good_sr):
        ev = Evidence(
            id="", raw_source_id="photo-034.jpg",
            source_refs=[good_sr], related_fact_ids=[],
        )
        errs = validate_evidence(ev)
        assert any("id" in e and "non-empty" in e for e in errs)

    def test_e9_related_object_ids_with_empty_element_fails(self, good_sr):
        """related_object_ids with empty string element."""
        ev = Evidence(
            id="E001", raw_source_id="photo-034.jpg",
            source_refs=[good_sr], related_fact_ids=[],
            related_object_ids=["", "C001"],
        )
        errs = validate_evidence(ev)
        assert any("related_object_ids" in e for e in errs)


# ══════════════════════════════════════════════
# JSON roundtrip (7 cases)
# ══════════════════════════════════════════════

class TestJSONRoundtrip:
    def test_j1_project(self):
        p = Project(id="PROJ01", fact_ids=[
            "fact:project.PROJ01.name", "fact:project.PROJ01.id",
        ], metadata={"client": "ACME"})
        s = p.to_json()
        p2 = Project.from_dict(json.loads(s))
        assert p2.id == "PROJ01"
        assert p2.fact_ids == p.fact_ids
        assert p2.metadata == {"client": "ACME"}

    def test_j2_structure_building_top_level(self):
        s = Structure(
            id="B01", structure_type="building",
            project_id="PROJ01", parent_id=None,
            fact_ids=["fact:building.B01.area"],
        )
        d = s.to_dict()
        assert "parent_id" not in d  # None → stripped
        s2 = Structure.from_dict(json.loads(s.to_json()))
        assert s2.id == "B01"
        assert s2.structure_type == "building"
        assert s2.project_id == "PROJ01"
        assert s2.parent_id is None
        assert s2.fact_ids == ["fact:building.B01.area"]

    def test_j3_structure_floor_with_parent(self):
        s = Structure(
            id="F1", structure_type="floor",
            project_id="PROJ01", parent_id="B01", fact_ids=[],
        )
        s2 = Structure.from_dict(json.loads(s.to_json()))
        assert s2.parent_id == "B01"
        assert s2.fact_ids == []

    def test_j4_component_both_defect_id_variants(self):
        c_empty = Component(
            id="K001", parent_structure_id="B01",
            defect_ids=[], fact_ids=[],
        )
        c_empty2 = Component.from_dict(json.loads(c_empty.to_json()))
        assert c_empty2.defect_ids == []

        c_full = Component(
            id="K001", parent_structure_id="B01",
            defect_ids=["C001"], fact_ids=[
                "fact:component.K001.concrete_strength",
            ],
        )
        c_full2 = Component.from_dict(json.loads(c_full.to_json()))
        assert c_full2.defect_ids == ["C001"]
        assert c_full2.fact_ids == ["fact:component.K001.concrete_strength"]

    def test_j5_defect(self):
        d = Defect(
            id="C001", host_component_id="K001",
            fact_ids=["fact:defect.C001.width", "fact:defect.C001.pattern"],
        )
        d2 = Defect.from_dict(json.loads(d.to_json()))
        assert d2.id == "C001"
        assert d2.host_component_id == "K001"
        assert d2.fact_ids == d.fact_ids

    def test_j6_evidence_nested_source_ref(self, good_sr):
        ev = Evidence(
            id="E001", raw_source_id="photo-034.jpg",
            source_refs=[good_sr],
            related_fact_ids=["fact:defect.C001.width"],
            related_object_ids=["C001"],
        )
        ev2 = Evidence.from_dict(json.loads(ev.to_json()))
        assert ev2.id == "E001"
        assert ev2.raw_source_id == "photo-034.jpg"
        assert len(ev2.source_refs) == 1
        assert ev2.source_refs[0].source_id == "photo-034.jpg"
        assert ev2.source_refs[0].location == "full-image"
        assert ev2.related_fact_ids == ["fact:defect.C001.width"]
        assert ev2.related_object_ids == ["C001"]

    def test_j7_evidence_related_object_ids_omitted_defaults(self, good_sr):
        """When related_object_ids is not in serialized dict,
        from_dict must default it to [] rather than None."""
        ev = Evidence(
            id="E001", raw_source_id="photo-034.jpg",
            source_refs=[good_sr], related_fact_ids=[],
        )
        raw = json.loads(ev.to_json())
        assert "related_object_ids" in raw  # always serialized
        assert raw["related_object_ids"] == []
        ev2 = Evidence.from_dict(raw)
        assert ev2.related_object_ids == []
