"""Controlled vocabularies for Evaluation Case layer.

Step 7-D — Evaluation Case Foundation Layer.
These are hard-coded frozensets for structural validation only.
"""

# Case level (05_EVALUATION.md §4)
CASE_LEVELS: frozenset[str] = frozenset({"gold", "silver", "bronze"})

# Issue severity (05_EVALUATION.md §5.2)
SEVERITIES: frozenset[str] = frozenset({"error", "warning"})

# KnownIssue types (Step 7-D v4 coding contract)
ISSUE_TYPES: frozenset[str] = frozenset({
    "fact_value_error",   # numeric value mistake in historical report
    "conclusion_error",   # conclusion direction mistake in historical report
})


def is_valid_case_level(value: str) -> bool:
    return value in CASE_LEVELS


def is_valid_severity(value: str) -> bool:
    return value in SEVERITIES


def is_valid_issue_type(value: str) -> bool:
    return value in ISSUE_TYPES
