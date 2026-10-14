"""Test types: dataclass construction + JSON roundtrip + KeyError boundaries."""
import json
import pytest
from pathlib import Path

from eval import (
    Meta,
    GroundTruthFact,
    GroundTruthFactList,
    GroundTruthStructure,
    GroundTruthConclusion,
    GroundTruthBundle,
    KnownIssue,
    ExpectedIssue,
    EvaluationCase,
)


# ──────────────────────────────────────────────
# T1–T12: Construction + roundtrip
# ──────────────────────────────────────────────

def test_meta_roundtrip():
    m = Meta(
        case_id="c1",
        case_level="gold",
        report_type="structure_appraisal",
        source_project="prj-1",
        created_at="2026-01-01T00:00:00",
        design_version="05_EVAL_v0.3",
        traps=["precision_check"],
        notes="a note",
    )
    d = m.to_dict()
    m2 = Meta.from_dict(d)
    assert m2.case_id == m.case_id
    assert m2.case_level == m.case_level
    assert m2.design_version == m.design_version
    assert m2.traps == m.traps
    assert m2.notes == m.notes


def test_ground_truth_fact_quantitative_roundtrip():
    f = GroundTruthFact(
        fact_id="fact:component.K001.concrete_strength",
        value=35.6,
        quantity_kind="pressure",
        precision=1,
        unit="MPa",
    )
    d = f.to_dict()
    assert d["fact_id"] == "fact:component.K001.concrete_strength"
    assert d["value"] == 35.6
    assert d["precision"] == 1
    assert d["unit"] == "MPa"
    f2 = GroundTruthFact.from_dict(d)
    assert f2 == f
    # precision is required — confirm it's not optional-default
    assert "precision" in d


def test_ground_truth_fact_qualitative_roundtrip():
    # qualitative fact has no unit (None)
    f = GroundTruthFact(
        fact_id="fact:defect.C001.pattern",
        value="diagonal",
        quantity_kind="qualitative",
        precision=0,
        unit=None,
    )
    d = f.to_dict()
    # unit=None should appear in dict (since it's explicitly set)
    assert d.get("unit") is None
    f2 = GroundTruthFact.from_dict(d)
    assert f2.unit is None
    assert f2.value == "diagonal"


def test_ground_truth_fact_list_roundtrip():
    ftl = GroundTruthFactList(fact_ids=["fact:component.K001.concrete_strength"])
    d = ftl.to_dict()
    ftl2 = GroundTruthFactList.from_dict(d)
    assert ftl2.fact_ids == ftl.fact_ids


def test_ground_truth_structure_roundtrip():
    gs = GroundTruthStructure(
        chapter_paths=["1.", "2."],
        table_count=1,
        table_headers=[["A", "B"]],
        figure_count=0,
        required_elements=["signature_block"],
    )
    d = gs.to_dict()
    gs2 = GroundTruthStructure.from_dict(d)
    assert gs2.table_count == 1
    assert gs2.table_headers == [["A", "B"]]


def test_ground_truth_conclusion_roundtrip():
    gc = GroundTruthConclusion(
        direction="qualified",
        required_evaluation_ids=["evaluation-001", "evaluation-002"],
        notes="all good",
    )
    d = gc.to_dict()
    gc2 = GroundTruthConclusion.from_dict(d)
    assert gc2.direction == "qualified"
    assert gc2.required_evaluation_ids == ["evaluation-001", "evaluation-002"]


def test_known_issue_fact_value_error_roundtrip():
    ki = KnownIssue(
        issue_type="fact_value_error",
        original_value=28.0,
        correct_value=35.6,
        reason="measurement error",
        confirmed_by="engineer_a",
        confirmed_at="2026-05-01T10:00:00",
        fact_id="fact:component.K001.concrete_strength",
    )
    d = ki.to_dict()
    assert d["fact_id"] == "fact:component.K001.concrete_strength"
    ki2 = KnownIssue.from_dict(d)
    assert ki2.fact_id == ki.fact_id


def test_known_issue_conclusion_error_roundtrip():
    # conclusion_error: fact_id is None
    ki = KnownIssue(
        issue_type="conclusion_error",
        original_value="qualified",
        correct_value="unqualified",
        reason="misjudged severity",
        confirmed_by="engineer_b",
        confirmed_at="2026-05-01T11:00:00",
        # fact_id omitted → Python default None
    )
    d = ki.to_dict()
    assert "fact_id" not in d  # None fact_id omitted in to_dict
    ki2 = KnownIssue.from_dict(d)
    assert ki2.fact_id is None
    assert ki2.issue_type == "conclusion_error"


def test_expected_issue_with_fact_id_roundtrip():
    ei = ExpectedIssue(
        rule_id="FACT.MISSING",
        severity="warning",
        fact_id="fact:component.K001.concrete_strength",
        note="omitted in historical report",
    )
    d = ei.to_dict()
    ei2 = ExpectedIssue.from_dict(d)
    assert ei2.fact_id == ei.fact_id


def test_expected_issue_without_fact_id_roundtrip():
    ei = ExpectedIssue(
        rule_id="CONCLUSION.MISMATCH",
        severity="error",
    )
    d = ei.to_dict()
    assert "fact_id" not in d  # None omitted
    ei2 = ExpectedIssue.from_dict(d)
    assert ei2.fact_id is None
    assert ei2.note == ""  # optional-default


# ──────────────────────────────────────────────
# T11–T12: Bundle + Case assembly
# ──────────────────────────────────────────────

def test_ground_truth_bundle_roundtrip():
    facts = [GroundTruthFact(
        fact_id="fact:component.K001.concrete_strength",
        value=40.0, quantity_kind="pressure", precision=1, unit="MPa",
    )]
    ftl = GroundTruthFactList(fact_ids=[f.fact_id for f in facts])
    gs = GroundTruthStructure(
        chapter_paths=["1."], table_count=0, table_headers=[],
        figure_count=0, required_elements=[],
    )
    gc = GroundTruthConclusion(
        direction="qualified",
        required_evaluation_ids=["evaluation-001"],
    )
    bundle = GroundTruthBundle(facts=facts, fact_list=ftl, structure=gs, conclusion=gc)
    d = bundle.to_dict()
    bundle2 = GroundTruthBundle.from_dict(d)
    assert len(bundle2.facts) == 1
    assert bundle2.fact_list.fact_ids == ["fact:component.K001.concrete_strength"]


def test_evaluation_case_full_roundtrip():
    meta = Meta(case_id="c1", case_level="gold", report_type="t",
                source_project="p", created_at="2026-01-01T00:00:00")
    bundle = GroundTruthBundle(
        facts=[GroundTruthFact(
            fact_id="fact:component.K001.concrete_strength",
            value=30.0, quantity_kind="pressure", precision=1, unit="MPa")],
        fact_list=GroundTruthFactList(fact_ids=["fact:component.K001.concrete_strength"]),
        structure=GroundTruthStructure(
            chapter_paths=["1."], table_count=0, table_headers=[],
            figure_count=0, required_elements=[]),
        conclusion=GroundTruthConclusion(
            direction="qualified", required_evaluation_ids=["evaluation-001"]),
    )
    case = EvaluationCase(
        meta=meta, ground_truth=bundle, known_issues=[], expected_issues=[],
        case_dir="C:\\fake\\path",  # runtime-only
    )
    d = case.to_dict()
    assert "case_dir" not in d  # runtime-only excluded
    j = case.to_json()
    assert "case_dir" not in j


# ──────────────────────────────────────────────
# T13: case_dir runtime-only (excluded from JSON)
# ──────────────────────────────────────────────

def test_case_dir_not_in_serialization():
    meta = Meta(case_id="c1", case_level="gold", report_type="t",
                source_project="p", created_at="2026-01-01T00:00:00")
    bundle = GroundTruthBundle(
        facts=[GroundTruthFact(
            fact_id="fact:component.K001.concrete_strength",
            value=30.0, quantity_kind="pressure", precision=1, unit="MPa")],
        fact_list=GroundTruthFactList(fact_ids=["fact:component.K001.concrete_strength"]),
        structure=GroundTruthStructure(
            chapter_paths=["1."], table_count=0, table_headers=[],
            figure_count=0, required_elements=[]),
        conclusion=GroundTruthConclusion(
            direction="qualified", required_evaluation_ids=["evaluation-001"]),
    )
    case = EvaluationCase(meta=meta, ground_truth=bundle, known_issues=[], expected_issues=[],
                         case_dir="/some/fake/path")
    d = case.to_dict()
    j = case.to_json()
    assert "case_dir" not in d
    assert "/some/fake/path" not in j


# ──────────────────────────────────────────────
# T14: from_dict field categories
# ──────────────────────────────────────────────

def test_required_key_missing_raises_keyerror():
    """required field missing → KeyError from from_dict."""
    with pytest.raises(KeyError):
        Meta.from_dict({
            "case_level": "gold",
            "report_type": "t",
            "source_project": "p",
            "created_at": "2026-01-01T00:00:00",
            # case_id missing!
        })


def test_optional_default_fields_missing_use_defaults():
    """optional-default fields missing → Python defaults used."""
    m = Meta.from_dict({
        "case_id": "c1",
        "case_level": "gold",
        "report_type": "t",
        "source_project": "p",
        "created_at": "2026-01-01T00:00:00",
        # design_version / traps / notes omitted
    })
    assert m.design_version is None
    assert m.traps == []
    assert m.notes == ""


def test_precision_required_keyerror_if_missing():
    """precision is required (no default) → KeyError if missing."""
    with pytest.raises(KeyError):
        GroundTruthFact.from_dict({
            "fact_id": "fact:component.K001.concrete_strength",
            "value": 30.0,
            "quantity_kind": "pressure",
            # precision missing!
        })


# ──────────────────────────────────────────────
# T15: bronze — facts empty, fact_list non-empty
# ──────────────────────────────────────────────

def test_bronze_facts_empty_but_fact_list_nonempty():
    bundle = GroundTruthBundle(
        facts=[],  # G3 empty (bronze)
        fact_list=GroundTruthFactList(fact_ids=[
            "fact:component.K001.concrete_strength",
            "fact:building.B01.area",
        ]),
        structure=GroundTruthStructure(
            chapter_paths=["1."], table_count=0, table_headers=[],
            figure_count=0, required_elements=[]),
        conclusion=GroundTruthConclusion(
            direction="unqualified", required_evaluation_ids=["evaluation-001"]),
    )
    assert bundle.facts == []
    assert len(bundle.fact_list.fact_ids) == 2


# ──────────────────────────────────────────────
# to_json / from_dict via json roundtrip
# ──────────────────────────────────────────────

def test_meta_to_json_then_from_dict():
    m = Meta(case_id="c1", case_level="gold", report_type="t",
             source_project="p", created_at="2026-01-01T00:00:00",
             notes="测试")
    j = m.to_json()
    parsed = json.loads(j)
    m2 = Meta.from_dict(parsed)
    assert m2.notes == "测试"
    assert m2 == m
