"""Evaluation Case data structures (Step 7-D).

9 dataclasses frozen at v4 Coding Contract:
    Meta / GroundTruthFact / GroundTruthFactList / GroundTruthStructure /
    GroundTruthConclusion / GroundTruthBundle / KnownIssue /
    ExpectedIssue / EvaluationCase

Field ordering follows Python dataclass rule:
    all fields without defaults → all fields with defaults.

No external frameworks — only standard dataclasses + typing + json.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, fields, is_dataclass
from typing import Any, List, Optional


# ── Helpers ─────────────────────────────────────────────────────────

def _asdict(obj: Any) -> Any:
    """Simple recursive dataclass → dict converter (no runtime_only fields)."""
    if is_dataclass(obj):
        result = {}
        for f in fields(obj):
            # Skip runtime-only fields
            if f.metadata and f.metadata.get("runtime_only"):
                continue
            result[f.name] = _asdict(getattr(obj, f.name))
        return result
    if isinstance(obj, list):
        return [_asdict(x) for x in obj]
    if isinstance(obj, Optional):
        if obj is None:
            return None
    return obj


def _coerce(value: Any) -> Any:
    """Identity converter — dataclass from_dict handles type conversion."""
    return value


# ── 1. Meta (meta.json) ────────────────────────────────────────────

@dataclass
class Meta:
    """05_EVALUATION.md §5.1 — Case metadata.

    Field categories:
        required: case_id, case_level, report_type, source_project, created_at
        optional-default: design_version, traps, notes
    """
    case_id: str                    # required
    case_level: str                 # required — gold | silver | bronze
    report_type: str                # required
    source_project: str             # required
    created_at: str                 # required — ISO 8601

    design_version: Optional[str] = None     # optional-default
    traps: List[str] = field(default_factory=list)  # optional-default
    notes: str = ""                 # optional-default

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "case_level": self.case_level,
            "report_type": self.report_type,
            "source_project": self.source_project,
            "created_at": self.created_at,
            "design_version": self.design_version,
            "traps": list(self.traps),
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Meta":
        return cls(
            case_id=data["case_id"],
            case_level=data["case_level"],
            report_type=data["report_type"],
            source_project=data["source_project"],
            created_at=data["created_at"],
            design_version=data.get("design_version", None),
            traps=data.get("traps", []),
            notes=data.get("notes", ""),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


# ── 2. GroundTruthFact (ground_truth/facts.json items — G3) ────────

@dataclass
class GroundTruthFact:
    """G3 fact value Ground Truth — lightweight answer key, NOT a runtime Fact.

    Reuses Step 7-B: is_valid_fact_id() / QUANTITY_KINDS.
    Does NOT reuse Step 7-B Fact dataclass (different semantics).

    Field categories:
        required: fact_id, value, quantity_kind, precision
        optional-default: unit

    v4: value is NOT allowed to be None (confirmed Ground Truth ≠ CDM missing).
        precision has NO default — must be explicitly provided.

    Field order: all required before optional-default.
    """
    fact_id: str                            # required
    value: Any                              # required — int|float|str|bool, NOT None
    quantity_kind: str                      # required — QUANTITY_KINDS enum
    precision: int                          # required — explicit, no default
    unit: Optional[str] = None              # optional-default

    def to_dict(self) -> dict:
        return {
            "fact_id": self.fact_id,
            "value": self.value,
            "quantity_kind": self.quantity_kind,
            "precision": self.precision,
            "unit": self.unit,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GroundTruthFact":
        return cls(
            fact_id=data["fact_id"],
            value=data["value"],
            quantity_kind=data["quantity_kind"],
            precision=data["precision"],
            unit=data.get("unit", None),
        )


# ── 3. GroundTruthFactList (ground_truth/fact_list.json — G2) ──────

@dataclass
class GroundTruthFactList:
    """G2 fact list — checklist of which facts this report should cover.

    G3.fact_id MUST ⊆ G2.fact_ids (Step 7-D cross-file integrity).
    """
    fact_ids: List[str]                     # required

    def to_dict(self) -> dict:
        return {"fact_ids": list(self.fact_ids)}

    @classmethod
    def from_dict(cls, data: dict) -> "GroundTruthFactList":
        return cls(fact_ids=list(data["fact_ids"]))


# ── 4. GroundTruthStructure (ground_truth/structure.json — G4) ──────

@dataclass
class GroundTruthStructure:
    """G4 report structure — chapters, tables, figures, required elements."""
    chapter_paths: List[str]                # required — allow empty list
    table_count: int                        # required — >= 0
    table_headers: List[List[str]]          # required — allow empty list
    figure_count: int                       # required — >= 0
    required_elements: List[str]            # required — allow empty list

    def to_dict(self) -> dict:
        return {
            "chapter_paths": list(self.chapter_paths),
            "table_count": self.table_count,
            "table_headers": [list(h) for h in self.table_headers],
            "figure_count": self.figure_count,
            "required_elements": list(self.required_elements),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GroundTruthStructure":
        return cls(
            chapter_paths=list(data["chapter_paths"]),
            table_count=data["table_count"],
            table_headers=[list(h) for h in data["table_headers"]],
            figure_count=data["figure_count"],
            required_elements=list(data["required_elements"]),
        )


# ── 5. GroundTruthConclusion (ground_truth/conclusion.json — G4) ───

@dataclass
class GroundTruthConclusion:
    """G4 conclusion — direction + evaluation coverage requirement.

    required_evaluation_ids is an opaque stable identifier list.
    Step 7-D does NOT define Evaluation ID grammar/schema/registry.
    Only checks: non-empty list, each ID non-empty, no duplicates.
    Example: ["evaluation-001", "evaluation-002"]

    direction: business value domain provided by ConclusionRule + report type.
    Step 7-D validator only checks non-empty (no global conclusion enum).
    """
    direction: str                                   # required
    required_evaluation_ids: List[str]               # required — opaque IDs
    notes: str = ""                                  # optional-default

    def to_dict(self) -> dict:
        return {
            "direction": self.direction,
            "required_evaluation_ids": list(self.required_evaluation_ids),
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GroundTruthConclusion":
        return cls(
            direction=data["direction"],
            required_evaluation_ids=list(data["required_evaluation_ids"]),
            notes=data.get("notes", ""),
        )


# ── 6. GroundTruthBundle (container for 4 ground_truth sub-structs) ─

@dataclass
class GroundTruthBundle:
    """Container for four ground_truth sub-structures (G2 / G3 / G4)."""
    facts: List[GroundTruthFact]            # required — G3; bronze ⇒ []
    fact_list: GroundTruthFactList           # required — G2
    structure: GroundTruthStructure          # required — G4
    conclusion: GroundTruthConclusion        # required — G4

    def to_dict(self) -> dict:
        return {
            "facts": [f.to_dict() for f in self.facts],
            "fact_list": self.fact_list.to_dict(),
            "structure": self.structure.to_dict(),
            "conclusion": self.conclusion.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GroundTruthBundle":
        return cls(
            facts=[GroundTruthFact.from_dict(f) for f in data["facts"]],
            fact_list=GroundTruthFactList.from_dict(data["fact_list"]),
            structure=GroundTruthStructure.from_dict(data["structure"]),
            conclusion=GroundTruthConclusion.from_dict(data["conclusion"]),
        )


# ── 7. KnownIssue (known_issues.json) ──────────────────────────────

@dataclass
class KnownIssue:
    """Known errors in the historical report.

    Field categories:
        required: issue_type, original_value, correct_value,
                  reason, confirmed_by, confirmed_at
        conditional-required: fact_id (Python default None,
            validator enforces non-None when issue_type="fact_value_error")

    Field order: all required before optional-default (fact_id).
    """
    issue_type: str                     # required — fact_value_error | conclusion_error
    original_value: Any                 # required
    correct_value: Any                  # required — original != correct
    reason: str                         # required
    confirmed_by: str                   # required
    confirmed_at: str                   # required — ISO 8601
    fact_id: Optional[str] = None       # conditional-required

    def to_dict(self) -> dict:
        d = {
            "issue_type": self.issue_type,
            "original_value": self.original_value,
            "correct_value": self.correct_value,
            "reason": self.reason,
            "confirmed_by": self.confirmed_by,
            "confirmed_at": self.confirmed_at,
        }
        if self.fact_id is not None:
            d["fact_id"] = self.fact_id
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "KnownIssue":
        return cls(
            issue_type=data["issue_type"],
            original_value=data["original_value"],
            correct_value=data["correct_value"],
            reason=data["reason"],
            confirmed_by=data["confirmed_by"],
            confirmed_at=data["confirmed_at"],
            fact_id=data.get("fact_id", None),
        )


# ── 8. ExpectedIssue (expected_issues.json) ────────────────────────

@dataclass
class ExpectedIssue:
    """Formal acceptance object — issues the system SHOULD catch.

    Rule ID registry belongs to Step 7-E Accuracy Validator.
    Step 7-D only checks rule_id non-empty.
    """
    rule_id: str                        # required
    severity: str                        # required — error | warning
    fact_id: Optional[str] = None       # optional-default
    note: str = ""                       # optional-default

    def to_dict(self) -> dict:
        d = {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "note": self.note,
        }
        if self.fact_id is not None:
            d["fact_id"] = self.fact_id
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "ExpectedIssue":
        return cls(
            rule_id=data["rule_id"],
            severity=data["severity"],
            fact_id=data.get("fact_id", None),
            note=data.get("note", ""),
        )


# ── 9. EvaluationCase (top-level shell) ─────────────────────────────

@dataclass
class EvaluationCase:
    """Complete evaluation case representation.

    case_dir is runtime-only — never enters to_dict / to_json / from_dict.
    It is set by from_dir() loader for runtime context.
    """
    # ── Persisted fields ──
    meta: Meta
    ground_truth: GroundTruthBundle
    known_issues: List[KnownIssue]
    expected_issues: List[ExpectedIssue]

    # ── Runtime-only field ──
    case_dir: str = field(
        default="",
        repr=False,
        metadata={"runtime_only": True},
    )

    # ── Serialization (explicitly excludes case_dir) ──
    def to_dict(self) -> dict:
        return {
            "meta": self.meta.to_dict(),
            "ground_truth": self.ground_truth.to_dict(),
            "known_issues": [ki.to_dict() for ki in self.known_issues],
            "expected_issues": [ei.to_dict() for ei in self.expected_issues],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    # ── Loader ──
    @classmethod
    def from_dir(cls, dir_path: str) -> "EvaluationCase":
        """Load an EvaluationCase from a directory.

        Raises clear exceptions for:
            - missing required files (FileNotFoundError)
            - invalid JSON (json.JSONDecodeError)
            - required key missing (KeyError — bubbled from from_dict)
        Does NOT catch KeyError — that belongs to test_types / test_loader.
        """
        import json as _json
        from pathlib import Path

        p = Path(dir_path)
        if not p.is_dir():
            raise FileNotFoundError(f"EvaluationCase directory not found: {dir_path}")

        # Required directory: inputs/ — must exist BEFORE any JSON parsing
        inputs_dir = p / "inputs"
        if not inputs_dir.is_dir():
            raise FileNotFoundError(
                f"Missing required directory: {inputs_dir}. "
                "Every evaluation case must have an inputs/ directory."
            )

        # Required sub-paths (JSON files)
        gt_dir = p / "ground_truth"
        files_required = [
            p / "meta.json",
            gt_dir / "facts.json",
            gt_dir / "fact_list.json",
            gt_dir / "structure.json",
            gt_dir / "conclusion.json",
        ]

        for f in files_required:
            if not f.is_file():
                raise FileNotFoundError(f"Missing required file: {f}")

        # Optional files
        known_path = p / "known_issues.json"
        expected_path = p / "expected_issues.json"

        def _read_json(path: Path) -> dict:
            with open(path, "r", encoding="utf-8") as fh:
                return _json.load(fh)

        # Parse required
        meta = Meta.from_dict(_read_json(files_required[0]))

        gt_data = {
            "facts": _read_json(files_required[1]),
            "fact_list": _read_json(files_required[2]),
            "structure": _read_json(files_required[3]),
            "conclusion": _read_json(files_required[4]),
        }
        bundle = GroundTruthBundle.from_dict(gt_data)

        # Parse optional — default to empty list if file missing
        known: List[KnownIssue] = []
        if known_path.is_file():
            raw = _read_json(known_path)
            known = [KnownIssue.from_dict(d) for d in raw]

        expected: List[ExpectedIssue] = []
        if expected_path.is_file():
            raw = _read_json(expected_path)
            expected = [ExpectedIssue.from_dict(d) for d in raw]

        case = cls(
            meta=meta,
            ground_truth=bundle,
            known_issues=known,
            expected_issues=expected,
            case_dir=str(p),
        )
        return case

    # ── Top-level validator ──
    def validate(self) -> List[str]:
        """Run all validations. Returns list of error messages (empty = pass)."""
        errors: List[str] = []
        errors.extend(validate_meta(self.meta))
        errors.extend(validate_ground_truth_facts(self.ground_truth.facts))
        errors.extend(validate_ground_truth_fact_list(self.ground_truth.fact_list))
        errors.extend(validate_ground_truth_structure(self.ground_truth.structure))
        errors.extend(validate_ground_truth_conclusion(self.ground_truth.conclusion))
        errors.extend(validate_known_issues(self.known_issues))
        errors.extend(validate_expected_issues(self.expected_issues))
        errors.extend(validate_case(self))
        return errors


# ── Lazy import of validators (they depend on enums, not on types) ──
# We import at the bottom to avoid circular dependency.
from .validator import (  # noqa: E402
    validate_meta,
    validate_ground_truth_fact,
    validate_ground_truth_facts,
    validate_ground_truth_fact_list,
    validate_ground_truth_structure,
    validate_ground_truth_conclusion,
    validate_known_issue,
    validate_known_issues,
    validate_expected_issue,
    validate_expected_issues,
    validate_case,
)
