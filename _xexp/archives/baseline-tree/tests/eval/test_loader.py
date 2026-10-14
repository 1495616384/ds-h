"""Test loader (EvaluationCase.from_dir)."""
import json
import pytest
from pathlib import Path

from eval import EvaluationCase

FIXTURES = Path(__file__).parent / "fixtures"


def _path(name: str) -> Path:
    return FIXTURES / name


# ══════════════════════════════════════════════
# L1–L3: from_dir normal loads
# ══════════════════════════════════════════════

def test_load_gold_case_success():
    case = EvaluationCase.from_dir(str(_path("case_gold_minimal")))
    assert case.meta.case_level == "gold"
    assert len(case.ground_truth.facts) == 3
    assert case.case_dir.endswith("case_gold_minimal")
    assert isinstance(case.case_dir, str)
    assert case.case_dir != ""


def test_load_silver_case_success():
    case = EvaluationCase.from_dir(str(_path("case_silver_minimal")))
    assert case.meta.case_level == "silver"
    assert len(case.ground_truth.facts) == 1
    assert len(case.ground_truth.fact_list.fact_ids) == 3
    assert case.case_dir.endswith("case_silver_minimal")


def test_load_bronze_case_success():
    """bronze: facts.json=[] must parse as empty list, not error."""
    case = EvaluationCase.from_dir(str(_path("case_bronze_minimal")))
    assert case.meta.case_level == "bronze"
    assert case.ground_truth.facts == []  # G3 empty ✓
    assert len(case.ground_truth.fact_list.fact_ids) == 2  # G2 non-empty ✓


# ══════════════════════════════════════════════
# L4–L6: from_dir failure paths
# ══════════════════════════════════════════════

def test_from_dir_raises_on_missing_directory():
    with pytest.raises(FileNotFoundError):
        EvaluationCase.from_dir(str(FIXTURES / "nonexistent_case"))


def test_from_dir_raises_on_missing_required_file(tmp_path):
    """Create a minimal dir without ground_truth/facts.json → FileNotFoundError."""
    bad = tmp_path / "bad_case"
    (bad / "inputs").mkdir(parents=True)      # from_dir requires inputs/ BEFORE anything else
    (bad / "ground_truth").mkdir(parents=True)
    # meta.json exists
    (bad / "meta.json").write_text(json.dumps({
        "case_id": "c", "case_level": "gold", "report_type": "t",
        "source_project": "p", "created_at": "2026-01-01T00:00:00",
    }), encoding="utf-8")
    # ground_truth sub-files are missing → FileNotFoundError
    with pytest.raises(FileNotFoundError):
        EvaluationCase.from_dir(str(bad))


def test_from_dir_raises_keyerror_on_missing_required_key(tmp_path):
    """JSON exists but required key missing → KeyError from from_dict.

    Note: inputs/ must exist (from_dir checks it before JSON parsing).
    """
    bad = tmp_path / "bad_case"
    (bad / "inputs").mkdir(parents=True)       # from_dir requires inputs/
    gt = bad / "ground_truth"
    gt.mkdir(parents=True)
    # meta.json: case_id missing
    (bad / "meta.json").write_text(json.dumps({
        "case_level": "gold", "report_type": "t",
        "source_project": "p", "created_at": "2026-01-01T00:00:00",
        # case_id missing!
    }), encoding="utf-8")
    # Other required ground_truth files (valid)
    (gt / "facts.json").write_text("[]")
    (gt / "fact_list.json").write_text(json.dumps({"fact_ids": []}))
    (gt / "structure.json").write_text(json.dumps({
        "chapter_paths": [], "table_count": 0, "table_headers": [],
        "figure_count": 0, "required_elements": []}))
    (gt / "conclusion.json").write_text(json.dumps({
        "direction": "qualified", "required_evaluation_ids": ["e1"]}))
    with pytest.raises(KeyError):
        EvaluationCase.from_dir(str(bad))


def test_from_dir_raises_on_missing_inputs_dir():
    """from_dir must raise FileNotFoundError when inputs/ is missing.

    v4 Coding Contract: missing required directory → from_dir raises directly.
    No delay to validate_case.
    """
    with pytest.raises(FileNotFoundError, match="inputs"):
        EvaluationCase.from_dir(str(_path("case_missing_inputs_dir")))


# ══════════════════════════════════════════════
# Cross-file validation through from_dir fixtures
# ══════════════════════════════════════════════

def test_case_gold_minimal_validates_cleanly():
    case = EvaluationCase.from_dir(str(_path("case_gold_minimal")))
    errors = case.validate()
    assert errors == [], f"Fixture should pass all validations, got: {errors}"


def test_case_silver_minimal_validates_cleanly():
    case = EvaluationCase.from_dir(str(_path("case_silver_minimal")))
    errors = case.validate()
    assert errors == [], f"Fixture should pass all validations, got: {errors}"


def test_case_bronze_minimal_validates_cleanly():
    case = EvaluationCase.from_dir(str(_path("case_bronze_minimal")))
    errors = case.validate()
    assert errors == [], f"Fixture should pass all validations, got: {errors}"


def test_case_bronze_facts_nonempty_fails_validation():
    case = EvaluationCase.from_dir(str(_path("case_bronze_facts_nonempty")))
    errors = case.validate()
    assert any("bronze" in e.lower() and "empty" in e.lower() for e in errors), errors


def test_case_g3_not_in_g2_fails_validation():
    case = EvaluationCase.from_dir(str(_path("case_g3_not_in_g2")))
    errors = case.validate()
    assert any("G2→G3" in e or "referential" in e.lower() or "not found in G2" in e
               for e in errors), errors


def test_case_g2_g3_duplicate_ids_fails_validation():
    case = EvaluationCase.from_dir(str(_path("case_g2_g3_duplicate_ids")))
    errors = case.validate()
    assert any("duplicate" in e.lower() for e in errors), errors
