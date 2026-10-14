"""Step 7-E Accuracy Validator — shared binding pipeline.

This module implements the binding validation core shared by BOTH:
    1. RenderedSegment.raw_text (prose / 图注 / Table title / note — B4 carrier)
    2. TableCell.raw_text        (Table 单元格 headers / rows — B5 carrier)

Two carriers, one pipeline — see Step_7_E_B5_Design_Check.md §6.
"""
from .data_structures import (
    AnchorDeclaration,
    RenderedSegment,
    TableCell,
    StructuredTable,
    SystemOutput,
    ActualIssue,
    ActualIssueLocation,
)
from .frozen_round import frozen_round
from .tokenizer import (
    NUMERIC_TOKEN_RE,
    IDENTIFIER_TOKEN_RE,
    TokenKind,
    Token,
    tokenize,
)
from cdm.registry import QUANTITY_KINDS  # frozen registry, reused from Step 7-B

from .binding import (
    UNIT_TO_QUANTITY,
    is_span_contained,
    find_covering_declarations,
    has_duplicate_fact_ids,
    WhitelistEntry,
    WhitelistRegistry,
    FactDisplaySpecSnapshot,
    parse_fact_id,
    derive_fact_type,
    NumericBindingResult,
    IdentifierBindingResult,
    bind_and_validate,
    bind_table_cell,
    bind_rendered_segment,
    VALIDATOR_ERROR_CODES,
)

__all__ = [
    # Data structures (§4)
    "AnchorDeclaration",
    "RenderedSegment",
    "TableCell",
    "StructuredTable",
    "SystemOutput",
    "ActualIssue",
    "ActualIssueLocation",
    # frozen_round (§12)
    "frozen_round",
    # Tokenizer (§5)
    "NUMERIC_TOKEN_RE",
    "IDENTIFIER_TOKEN_RE",
    "TokenKind",
    "Token",
    "tokenize",
    # Binding (§8)
    "QUANTITY_KINDS",
    "UNIT_TO_QUANTITY",
    "is_span_contained",
    "find_covering_declarations",
    "has_duplicate_fact_ids",
    "WhitelistEntry",
    "WhitelistRegistry",
    "FactDisplaySpecSnapshot",
    "parse_fact_id",
    "derive_fact_type",
    "NumericBindingResult",
    "IdentifierBindingResult",
    "bind_and_validate",
    "bind_table_cell",
    "bind_rendered_segment",
    "VALIDATOR_ERROR_CODES",
]
