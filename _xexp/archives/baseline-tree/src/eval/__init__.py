"""Evaluation Case Foundation Layer (Step 7-D v4).

Programmatic data structures and basic validation for evaluation case fixtures.

Reuses from Step 7-B (CDM):
    is_valid_fact_id — fact:<scope_class>.<instance_key>.<attribute> grammar
    QUANTITY_KINDS   — controlled vocabulary for GroundTruthFact.quantity_kind

Does NOT reuse Step 7-B Fact dataclass (semantic difference: answer key vs runtime fact).
"""
from .enums import (
    CASE_LEVELS,
    ISSUE_TYPES,
    SEVERITIES,
    is_valid_case_level,
    is_valid_issue_type,
    is_valid_severity,
)
from .types import (
    EvaluationCase,
    GroundTruthBundle,
    GroundTruthConclusion,
    GroundTruthFact,
    GroundTruthFactList,
    GroundTruthStructure,
    KnownIssue,
    Meta,
    ExpectedIssue,
)
from .validator import (
    validate_case,
    validate_expected_issue,
    validate_expected_issues,
    validate_ground_truth_conclusion,
    validate_ground_truth_fact,
    validate_ground_truth_facts,
    validate_ground_truth_fact_list,
    validate_ground_truth_structure,
    validate_known_issue,
    validate_known_issues,
    validate_meta,
)

__all__ = [
    # Enums
    "CASE_LEVELS",
    "ISSUE_TYPES",
    "SEVERITIES",
    "is_valid_case_level",
    "is_valid_issue_type",
    "is_valid_severity",
    # Types
    "Meta",
    "GroundTruthFact",
    "GroundTruthFactList",
    "GroundTruthStructure",
    "GroundTruthConclusion",
    "GroundTruthBundle",
    "KnownIssue",
    "ExpectedIssue",
    "EvaluationCase",
    # Validators
    "validate_meta",
    "validate_ground_truth_fact",
    "validate_ground_truth_facts",
    "validate_ground_truth_fact_list",
    "validate_ground_truth_structure",
    "validate_ground_truth_conclusion",
    "validate_known_issue",
    "validate_known_issues",
    "validate_expected_issue",
    "validate_expected_issues",
    "validate_case",
]
