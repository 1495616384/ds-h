"""Test validators: pass / fail paths + cross-file consistency."""
import pytest

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
    validate_meta,
    validate_ground_truth_fact,
    validate_ground_truth_facts,
    validate_ground_truth_fact_list,
    validate_ground_truth_structure,
    validate_ground_truth_conclusion,
    validate_known_issue,
    validate_expected_issue,
    validate_case,
)


# ──────────────────────────────────────────────
# Helper: build valid bronze case (used in multiple tests)
# ──────────────────────────────────────────────

def _make_valid_bronze_case():
    return EvaluationCase(
        meta=Meta(case_id="cb", case_level="bronze", report_type="t",
                  source_project="p", created_at="2026-01-01T00:00:00"),
        ground_truth=GroundTruthBundle(
            facts=[],  # G3 empty ✓
            fact_list=GroundTruthFactList(fact_ids=["fact:component.K001.concrete_strength"]),
            structure=GroundTruthStructure(
                chapter_paths=["1."], table_count=0, table_headers=[],
                figure_count=0, required_elements=[]),
            conclusion=GroundTruthConclusion(
                direction="qualified", required_evaluation_ids=["evaluation-001"]),
        ),
        known_issues=[],
        expected_issues=[],
        case_dir="tests/eval/fixtures/case_bronze_minimal",
    )


def _make_valid_gold_case(case_dir="tests/eval/fixtures/case_gold_minimal"):
    return EvaluationCase(
        meta=Meta(case_id="cg", case_level="gold", report_type="t",
                  source_project="p", created_at="2026-01-01T00:00:00"),
        ground_truth=GroundTruthBundle(
            facts=[GroundTruthFact(
                fact_id="fact:component.K001.concrete_strength",
                value=35.6, quantity_kind="pressure", precision=1, unit="MPa")],
            fact_list=GroundTruthFactList(
                fact_ids=["fact:component.K001.concrete_strength"]),
            structure=GroundTruthStructure(
                chapter_paths=["1."], table_count=0, table_headers=[],
                figure_count=0, required_elements=[]),
            conclusion=GroundTruthConclusion(
                direction="qualified", required_evaluation_ids=["evaluation-001"]),
        ),
        known_issues=[],
        expected_issues=[],
        case_dir=case_dir,
    )


# ══════════════════════════════════════════════
# V-SERIES: Sub-validator PASS paths
# ══════════════════════════════════════════════

class TestValidateMetaPass:
    def test_gold(self):
        errors = validate_meta(Meta(case_id="c", case_level="gold", report_type="t",
                                    source_project="p", created_at="2026-01-01T00:00:00"))
        assert errors == []

    def test_silver(self):
        errors = validate_meta(Meta(case_id="c", case_level="silver", report_type="t",
                                    source_project="p", created_at="2026-01-01T00:00:00"))
        assert errors == []

    def test_bronze(self):
        errors = validate_meta(Meta(case_id="c", case_level="bronze", report_type="t",
                                    source_project="p", created_at="2026-01-01T00:00:00"))
        assert errors == []


class TestValidateGroundTruthFactPass:
    def test_quantitative(self):
        errors = validate_ground_truth_fact(GroundTruthFact(
            fact_id="fact:component.K001.concrete_strength",
            value=35.6, quantity_kind="pressure", precision=1, unit="MPa"))
        assert errors == []

    def test_integer_value(self):
        errors = validate_ground_truth_fact(GroundTruthFact(
            fact_id="fact:building.B01.floor_count",
            value=5, quantity_kind="count", precision=0))
        assert errors == []

    def test_qualitative_string(self):
        errors = validate_ground_truth_fact(GroundTruthFact(
            fact_id="fact:defect.C001.pattern",
            value="diagonal", quantity_kind="qualitative", precision=0))
        assert errors == []


class TestValidateGroundTruthFactListPass:
    def test_single(self):
        errors = validate_ground_truth_fact_list(GroundTruthFactList(
            fact_ids=["fact:component.K001.concrete_strength"]))
        assert errors == []

    def test_multiple_no_duplicates(self):
        errors = validate_ground_truth_fact_list(GroundTruthFactList(
            fact_ids=["fact:component.K001.concrete_strength", "fact:defect.C001.width"]))
        assert errors == []


class TestValidateGroundTruthStructurePass:
    def test_with_tables(self):
        errors = validate_ground_truth_structure(GroundTruthStructure(
            chapter_paths=["1.", "2."], table_count=1,
            table_headers=[["A", "B"]], figure_count=0, required_elements=[]))
        assert errors == []

    def test_minimal(self):
        errors = validate_ground_truth_structure(GroundTruthStructure(
            chapter_paths=["1."], table_count=0, table_headers=[],
            figure_count=0, required_elements=["signature_block"]))
        assert errors == []


class TestValidateGroundTruthConclusionPass:
    def test_with_notes(self):
        errors = validate_ground_truth_conclusion(GroundTruthConclusion(
            direction="qualified",
            required_evaluation_ids=["evaluation-001", "evaluation-002"],
            notes="ok"))
        assert errors == []

    def test_no_notes(self):
        errors = validate_ground_truth_conclusion(GroundTruthConclusion(
            direction="unqualified",
            required_evaluation_ids=["evaluation-001"]))
        assert errors == []


class TestValidateKnownIssuePass:
    def test_fact_value_error(self):
        errors = validate_known_issue(KnownIssue(
            issue_type="fact_value_error",
            original_value=28.0, correct_value=35.6,
            reason="measurement error",
            confirmed_by="eng_a", confirmed_at="2026-05-01T10:00:00",
            fact_id="fact:component.K001.concrete_strength"))
        assert errors == []

    def test_conclusion_error(self):
        errors = validate_known_issue(KnownIssue(
            issue_type="conclusion_error",
            original_value="qualified", correct_value="unqualified",
            reason="misjudged",
            confirmed_by="eng_b", confirmed_at="2026-05-01T11:00:00",
            # fact_id default None — acceptable for conclusion_error
        ))
        assert errors == []


class TestValidateExpectedIssuePass:
    def test_with_fact_id(self):
        errors = validate_expected_issue(ExpectedIssue(
            rule_id="FACT.MISSING", severity="warning",
            fact_id="fact:component.K001.concrete_strength"))
        assert errors == []

    def test_without_fact_id(self):
        errors = validate_expected_issue(ExpectedIssue(
            rule_id="CONCLUSION.MISMATCH", severity="error"))
        assert errors == []


# ══════════════════════════════════════════════
# F-SERIES: Sub-validator FAIL paths
# ══════════════════════════════════════════════

class TestValidateMetaFail:
    def test_invalid_case_level(self):
        errors = validate_meta(Meta(case_id="c", case_level="platinum", report_type="t",
                                    source_project="p", created_at="2026-01-01T00:00:00"))
        assert len(errors) >= 1

    def test_empty_case_id(self):
        errors = validate_meta(Meta(case_id="", case_level="gold", report_type="t",
                                    source_project="p", created_at="2026-01-01T00:00:00"))
        assert len(errors) >= 1

    def test_invalid_created_at(self):
        errors = validate_meta(Meta(case_id="c", case_level="gold", report_type="t",
                                    source_project="p", created_at="not-a-date"))
        assert len(errors) >= 1


class TestValidateGroundTruthFactFail:
    def test_invalid_fact_id_grammar(self):
        errors = validate_ground_truth_fact(GroundTruthFact(
            fact_id="not_a_valid_id",
            value=30.0, quantity_kind="pressure", precision=1))
        assert len(errors) >= 1

    def test_invalid_scope_class(self):
        errors = validate_ground_truth_fact(GroundTruthFact(
            fact_id="fact:unknown.S001.field",
            value=30.0, quantity_kind="pressure", precision=1))
        assert len(errors) >= 1

    def test_invalid_quantity_kind(self):
        errors = validate_ground_truth_fact(GroundTruthFact(
            fact_id="fact:component.K001.concrete_strength",
            value=30.0, quantity_kind="made_up_kind", precision=1))
        assert len(errors) >= 1

    def test_precision_negative(self):
        errors = validate_ground_truth_fact(GroundTruthFact(
            fact_id="fact:component.K001.concrete_strength",
            value=30.0, quantity_kind="pressure", precision=-1))
        assert len(errors) >= 1

    def test_value_none_not_allowed(self):
        """v4: GroundTruthFact.value must not be None."""
        errors = validate_ground_truth_fact(GroundTruthFact(
            fact_id="fact:component.K001.concrete_strength",
            value=None, quantity_kind="pressure", precision=1, unit="MPa"))
        assert any("must not be None" in e for e in errors), errors

    def test_value_list_not_allowed(self):
        """v4: GroundTruthFact.value must be int/float/str/bool."""
        errors = validate_ground_truth_fact(GroundTruthFact(
            fact_id="fact:component.K001.concrete_strength",
            value=[1, 2, 3], quantity_kind="pressure", precision=1, unit="MPa"))
        assert any("int|float|str|bool" in e for e in errors), errors


class TestValidateGroundTruthFactListFail:
    def test_empty_string_in_list(self):
        errors = validate_ground_truth_fact_list(GroundTruthFactList(fact_ids=[""]))
        assert len(errors) >= 1

    def test_duplicate_fact_ids(self):
        errors = validate_ground_truth_fact_list(GroundTruthFactList(
            fact_ids=["fact:component.K001.concrete_strength",
                      "fact:component.K001.concrete_strength"]))
        assert any("duplicate" in e.lower() for e in errors), errors


class TestValidateKnownIssueFail:
    def test_invalid_issue_type(self):
        errors = validate_known_issue(KnownIssue(
            issue_type="other", original_value=1, correct_value=2,
            reason="r", confirmed_by="cb", confirmed_at="2026-05-01T10:00:00"))
        assert len(errors) >= 1

    def test_fact_value_error_without_fact_id(self):
        """conditional-required: fact_value_error MUST have fact_id."""
        errors = validate_known_issue(KnownIssue(
            issue_type="fact_value_error",
            original_value=1, correct_value=2, reason="r",
            confirmed_by="cb", confirmed_at="2026-05-01T10:00:00",
            fact_id=None))
        assert any("conditional-required" in e or "fact_id is required" in e for e in errors), errors

    def test_conclusion_error_allows_none_fact_id(self):
        """conclusion_error SHOULD NOT error when fact_id is None."""
        errors = validate_known_issue(KnownIssue(
            issue_type="conclusion_error",
            original_value="qualified", correct_value="unqualified",
            reason="r", confirmed_by="cb", confirmed_at="2026-05-01T10:00:00",
            fact_id=None))
        # fact_id=None is OK for conclusion_error; only other errors possible
        fact_id_errors = [e for e in errors if "fact_id" in e and "required" in e.lower()]
        assert fact_id_errors == [], f"Unexpected fact_id errors: {fact_id_errors}"

    def test_original_equals_correct(self):
        errors = validate_known_issue(KnownIssue(
            issue_type="fact_value_error", fact_id="fact:component.K001.concrete_strength",
            original_value=42.0, correct_value=42.0, reason="r",
            confirmed_by="cb", confirmed_at="2026-05-01T10:00:00"))
        assert any("differ" in e for e in errors), errors

    def test_invalid_confirmed_at(self):
        errors = validate_known_issue(KnownIssue(
            issue_type="conclusion_error",
            original_value="a", correct_value="b", reason="r",
            confirmed_by="cb", confirmed_at="not-a-date"))
        assert len(errors) >= 1


class TestValidateExpectedIssueFail:
    def test_empty_rule_id(self):
        errors = validate_expected_issue(ExpectedIssue(
            rule_id="", severity="error"))
        assert len(errors) >= 1

    def test_invalid_severity(self):
        errors = validate_expected_issue(ExpectedIssue(
            rule_id="FACT.X", severity="fatal"))
        assert len(errors) >= 1

    def test_invalid_fact_id_grammar(self):
        errors = validate_expected_issue(ExpectedIssue(
            rule_id="FACT.X", severity="error", fact_id="bad_id"))
        assert len(errors) >= 1


class TestValidateGroundTruthConclusionFail:
    def test_empty_direction(self):
        errors = validate_ground_truth_conclusion(GroundTruthConclusion(
            direction="", required_evaluation_ids=["e1"]))
        assert len(errors) >= 1

    def test_empty_evaluation_ids(self):
        errors = validate_ground_truth_conclusion(GroundTruthConclusion(
            direction="qualified", required_evaluation_ids=[]))
        assert len(errors) >= 1

    def test_duplicate_evaluation_ids(self):
        errors = validate_ground_truth_conclusion(GroundTruthConclusion(
            direction="qualified",
            required_evaluation_ids=["evaluation-001", "evaluation-001"]))
        assert any("duplicate" in e.lower() for e in errors), errors


# ══════════════════════════════════════════════
# C-SERIES: validate_case (cross-file consistency)
# ══════════════════════════════════════════════

class TestValidateCase:
    def test_valid_bronze_case(self):
        """Bronze: facts=[], fact_list non-empty, structure+conclusion OK."""
        case = _make_valid_bronze_case()
        errors = validate_case(case)
        assert errors == [], f"Unexpected errors: {errors}"

    def test_valid_gold_case(self):
        """Gold: facts non-empty, G3 ⊆ G2, structure+conclusion OK."""
        case = _make_valid_gold_case()
        errors = validate_case(case)
        assert errors == [], f"Unexpected errors: {errors}"

    def test_bronze_rejects_nonempty_facts(self):
        """bronze + non-empty facts → error."""
        case = _make_valid_bronze_case()
        case.ground_truth.facts = [GroundTruthFact(
            fact_id="fact:component.K001.concrete_strength",
            value=30.0, quantity_kind="pressure", precision=1)]
        errors = validate_case(case)
        assert any("bronze" in e and "empty" in e.lower() for e in errors), errors

    def test_gold_rejects_empty_facts(self):
        """gold + facts=[] → error."""
        case = _make_valid_gold_case()
        case.ground_truth.facts = []
        errors = validate_case(case)
        assert any("gold" in e and "non-empty" in e.lower() for e in errors), errors

    def test_silver_rejects_empty_facts(self):
        """silver + facts=[] → error (silver must also have non-empty G3)."""
        case = _make_valid_gold_case()
        case.meta.case_level = "silver"
        case.ground_truth.facts = []
        errors = validate_case(case)
        assert any("silver" in e and "non-empty" in e.lower() for e in errors), errors

    def test_g3_fact_not_in_g2(self):
        """G3 has a fact_id that G2 does not declare → error."""
        case = _make_valid_gold_case()
        case.ground_truth.facts = [
            GroundTruthFact(
                fact_id="fact:component.K001.concrete_strength",
                value=30.0, quantity_kind="pressure", precision=1),
            GroundTruthFact(
                fact_id="fact:defect.C001.width",  # NOT in G2
                value=2.5, quantity_kind="length", precision=1, unit="mm"),
        ]
        # G2 only declares the first one
        case.ground_truth.fact_list = GroundTruthFactList(
            fact_ids=["fact:component.K001.concrete_strength"])
        errors = validate_case(case)
        assert any("not found in G2" in e or "referential integrity" in e
                   for e in errors), errors

    def test_duplicate_g2_fact_ids(self):
        """G2 has duplicate fact_ids → error (caught by sub-validator AND validate_case)."""
        case = _make_valid_gold_case()
        case.ground_truth.fact_list = GroundTruthFactList(
            fact_ids=["fact:component.K001.concrete_strength",
                      "fact:component.K001.concrete_strength"])
        # Use the sub-validator since validate_case delegates that check
        errors = validate_ground_truth_fact_list(case.ground_truth.fact_list)
        assert any("duplicate" in e.lower() for e in errors), errors

    def test_duplicate_g3_fact_ids(self):
        """G3 has duplicate fact_ids → error (caught by sub-validator)."""
        case = _make_valid_gold_case()
        case.ground_truth.facts = [
            GroundTruthFact(
                fact_id="fact:component.K001.concrete_strength",
                value=30.0, quantity_kind="pressure", precision=1),
            GroundTruthFact(
                fact_id="fact:component.K001.concrete_strength",
                value=31.0, quantity_kind="pressure", precision=1),
        ]
        case.ground_truth.fact_list = GroundTruthFactList(
            fact_ids=["fact:component.K001.concrete_strength"])
        errors = validate_ground_truth_facts(case.ground_truth.facts)
        assert any("duplicate" in e.lower() for e in errors), errors

    def test_gold_rejects_empty_fact_list(self):
        """gold + fact_list fact_ids=[] → error."""
        case = _make_valid_gold_case()
        case.ground_truth.fact_list = GroundTruthFactList(fact_ids=[])
        errors = validate_case(case)
        assert any("fact_list" in e.lower() or "non-empty" in e.lower() for e in errors), errors

    def test_bronze_rejects_empty_fact_list(self):
        """bronze + fact_list fact_ids=[] → error (bronze still needs G2)."""
        case = _make_valid_bronze_case()
        case.ground_truth.fact_list = GroundTruthFactList(fact_ids=[])
        errors = validate_case(case)
        assert any("fact_list" in e.lower() or "non-empty" in e.lower() for e in errors), errors
