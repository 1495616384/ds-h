"""Step 7-E Accuracy Validator — Binding core (§8).

Shared by BOTH:
    • RenderedSegment.raw_text (prose / 图注 / Table title / note)
    • TableCell.raw_text (Table 单元格 headers / rows — B5)

Same tokenizer, same span predicate, same whitelist predicate,
same BIND-5/6/7/8, same §8.2 comparison chain.
Only differs in: WHICH anchor_declarations list to look up, and
whether legacy cell.fact_id single-token path applies.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# Reuse Step 7-B (CDM) frozen helpers
from cdm.id import is_valid_fact_id
from cdm.registry import QUANTITY_KINDS

from .data_structures import AnchorDeclaration, TableCell
from .frozen_round import frozen_round
from .tokenizer import Token, TokenKind


# ── §3.2 冻结 Unit Registry (R7 — exact equality) ────────────────

UNIT_TO_QUANTITY: dict[str, str] = {
    # Pressure
    "MPa": "pressure",
    "Pa": "pressure",
    "kPa": "pressure",
    "GPa": "pressure",
    "N/mm²": "pressure",
    "kN/m²": "pressure",
    # Length
    "m": "length",
    "mm": "length",
    "cm": "length",
    "km": "length",
    # Area
    "m²": "area",
    "mm²": "area",
    "cm²": "area",
    # Volume
    "m³": "volume",
    "mm³": "volume",
    # Mass
    "kg": "mass",
    "t": "mass",
    "g": "mass",
    # Force
    "N": "force",
    "kN": "force",
    # Frequency
    "Hz": "frequency",
    # Ratio
    "%": "ratio",
}


# ── Error codes (§8.1 — frozen, no new codes) ──────────────────────

VALIDATOR_ERROR_CODES = {
    "BIND-5": "ANCHOR.INVALID_FACT_ID",
    "BIND-6": "ANCHOR.DUPLICATE_BINDING",
    "BIND-7": "ANCHOR.UNANCHORED",                    # identifier not covered
    "BIND-7-MISMATCH": "ANCHOR.IDENTIFIER_BINDING_MISMATCH",
    "BIND-8": "ANCHOR.UNANCHORED",                    # numeric not covered
    "BIND-8-INVALID": "ANCHOR.INVALID_FACT_ID",
    "BIND-8-DUP": "ANCHOR.DUPLICATE_BINDING",
    "UNKNOWN_UNIT": "ANCHOR.UNKNOWN_UNIT",
    "QUANTITY_KIND_MISMATCH": "ANCHOR.QUANTITY_KIND_MISMATCH",
    "UNIT_MISMATCH": "ANCHOR.UNIT_MISMATCH",
    "UNSUPPORTED_SIGN": "ANCHOR.UNSUPPORTED_SIGN",
    "VALUE_MISMATCH": "VALUE.CONSISTENCY",
}


# ── §5.1 ± prefix detection ────────────────────────────────────────

_PLUS_MINUS_PREFIX_RE = re.compile(r'^±\s*')


# ── §8.2 辅助：fact_id 解析 ────────────────────────────────────────

def parse_fact_id(fact_id: str) -> Tuple[str, str, str]:
    """Parse fact:scope_class.instance_key.attribute → (scope_class, instance_key, attribute).

    Assumes is_valid_fact_id() has already passed (no defensive check here).
    """
    # fact:xxx.yyy.zzz
    body = fact_id[len("fact:"):]
    parts = body.split(".")
    return parts[0], parts[1], parts[2]


def derive_fact_type(fact_id: str) -> str:
    """fact:component.K001.concrete_strength → component.concrete_strength."""
    _, scope_class, instance_key, attribute = _full_parse(fact_id)
    return f"{scope_class}.{attribute}"


def _full_parse(fact_id: str) -> Tuple[str, str, str, str]:
    """Return (prefix, scope_class, instance_key, attribute)."""
    body = fact_id[len("fact:"):]
    parts = body.split(".")
    return ("fact:", parts[0], parts[1], parts[2])


# ── FactDisplaySpecSnapshot (§3.1) ─────────────────────────────────

@dataclass
class FactDisplaySpecSnapshot:
    """§3.1 — Step 7-E only reads decimals from this snapshot."""
    fact_type: str
    decimals: int


# ── Whitelist (§8.4) ────────────────────────────────────────────────

@dataclass
class WhitelistEntry:
    """§8.4 — 登记制白名单条目."""
    pattern: str                         # regex pattern
    reason: str                          # why it's not a fact number
    scope: str = "global"                # global | section | template
    confirmed_by: str = ""

    def __post_init__(self) -> None:
        self._compiled = re.compile(self.pattern)

    def matches(self, text: str) -> List[Tuple[int, int]]:
        """Return list of (char_start, char_end) spans matched by this pattern."""
        return [(m.start(), m.end()) for m in self._compiled.finditer(text)]


@dataclass
class WhitelistRegistry:
    """§8.4 — 登记制白名单集合."""
    entries: List[WhitelistEntry] = field(default_factory=list)

    def is_span_whitelisted(self, char_start: int, char_end: int, text: str) -> bool:
        """§8.4 — token span ⊆ ANY whitelist pattern match span → exempt.

        Partial overlap (intersect but NOT contain) → NOT exempt.
        """
        for entry in self.entries:
            for ws, we in entry.matches(text):
                if char_start >= ws and char_end <= we:
                    return True
        return False


# ── §8.1 / Step 7-E 设计 统一 span 覆盖谓词 ─────────────────────────

def is_span_contained(
    token_start: int, token_end: int,
    decl_start: int, decl_end: int,
) -> bool:
    """冻结 span 规则：token span ⊆ declaration span OR text equality.

    Partial overlap (intersect but NOT contain) → NOT covered.
    """
    return token_start >= decl_start and token_end <= decl_end


def find_covering_declarations(
    token: Token,
    declarations: List[AnchorDeclaration],
) -> List[AnchorDeclaration]:
    """Find all AnchorDeclarations whose span covers token's span.

    Uses frozen span rule (is_span_contained).
    Also covers text-equality edge case: token.text == decl.token.
    """
    covering: List[AnchorDeclaration] = []
    for d in declarations:
        # Primary: span containment
        if is_span_contained(token.char_start, token.char_end, d.char_start, d.char_end):
            covering.append(d)
            continue
        # Secondary: text-equality fallback (when spans might be off)
        if token.text == d.token:
            covering.append(d)
    return covering


def has_duplicate_fact_ids(declarations: List[AnchorDeclaration]) -> bool:
    """§8.1 BIND-6 — same token covered by ≥2 declarations with DIFFERENT fact_ids."""
    fact_ids = {d.fact_id for d in declarations}
    return len(fact_ids) > 1


# ── §8.2 — 比较链结果 ──────────────────────────────────────────────

@dataclass
class BindingIssue:
    """An issue produced during binding + §8.2 validation."""
    severity: str                     # "error" | "warning"
    issue_type: str                   # e.g. "unanchored", "invalid_fact_id", "duplicate_binding", "value_mismatch"
    message: str                      # diagnostic text
    location: str                     # for ActualIssue location field
    fact_id: Optional[str] = None


@dataclass
class NumericBindingResult:
    """Result of binding + §8.2 for a single numeric token."""
    fact_id: Optional[str] = None
    quantity_kind: Optional[str] = None   # from UNIT_TO_QUANTITY
    unit_matched: Optional[str] = None    # from UNIT_TO_QUANTITY (exact key)
    issues: List[BindingIssue] = field(default_factory=list)


@dataclass
class IdentifierBindingResult:
    """Result of BIND-7 for a single identifier token."""
    fact_id: Optional[str] = None
    issues: List[BindingIssue] = field(default_factory=list)


# ── Legacy fact_id 检测 ────────────────────────────────────────────

def _count_anchorable_tokens_after_whitelist(
    raw_text: str,
    whitelist: WhitelistRegistry,
    tokenize_fn,
) -> int:
    """Count non-whitelisted anchorable tokens (numeric + identifier) in text.

    '需要锚定的 token': 未被 whitelist 豁免的 numeric (BIND-8 目标) +
    未被 whitelist 豁免的 identifier (BIND-7 目标).
    """
    tokens = tokenize_fn(raw_text)
    count = 0
    for tok in tokens:
        if whitelist.is_span_whitelisted(tok.char_start, tok.char_end, raw_text):
            continue
        count += 1
    return count


# ── 核心绑定函数 ────────────────────────────────────────────────────

def bind_and_validate(
    *,
    raw_text: str,
    anchor_declarations: List[AnchorDeclaration],
    carrier_label: str,                # e.g. "rendered_segments[2]" or "table[table-1][0][1]"
    whitelist: WhitelistRegistry,
    tokenize_fn,                       # callable: (text) -> List[Token]
    # Legacy support — TableCell.fact_id single-token path
    legacy_fact_id: Optional[str] = None,
    # Ground Truth lookup
    ground_truth_by_id: Optional[dict] = None,   # fact_id -> GroundTruthFact
    fact_display_spec: Optional[dict] = None,     # fact_type -> FactDisplaySpecSnapshot
    unit_registry_map: Optional[dict] = None,     # must match UNIT_TO_QUANTITY exactly
) -> List[BindingIssue]:
    """Execute full binding pipeline on ONE carrier's raw_text.

    Pipeline (shared for RenderedSegment and TableCell):
        raw_text
        → tokenize (Fix 3)
        → whitelist span containment (§8.4)
        → for EACH non-whitelisted token:
            find covering declarations
            (legacy fallback if applicable)
            → BIND-5/6/7/8
            → §8.2 comparison chain (numeric only)

    Parameters:
        raw_text:           The text to validate
        anchor_declarations:  Per-carrier anchor declarations
        carrier_label:       Location string for issue reporting
        whitelist:           Whitelist registry for §8.4
        tokenize_fn:         Tokenizer callable
        legacy_fact_id:      cell.fact_id for single-token legacy path (None if not TableCell)
        ground_truth_by_id:  G3 facts by fact_id for §8.2 chain
        fact_display_spec:   fact_type -> FactDisplaySpecSnapshot for precision
        unit_registry_map:   Must equal UNIT_TO_QUANTITY exactly (A-4)

    Returns:
        List of BindingIssue objects (empty = pass).
    """
    issues: List[BindingIssue] = []
    tokens = tokenize_fn(raw_text)

    for tok in tokens:
        # ── §8.4 whitelist span containment ──────────────────────
        if whitelist.is_span_whitelisted(tok.char_start, tok.char_end, raw_text):
            # Whitelisted → exempt. Still produce DIAGNOSTIC record (not error).
            continue

        # ── Check ± prefix ───────────────────────────────────────
        if tok.kind == TokenKind.NUMERIC and _PLUS_MINUS_PREFIX_RE.match(tok.text):
            issues.append(BindingIssue(
                severity="error",
                issue_type="unsupported_sign",
                message=f"numeric token '{tok.text}' contains ± prefix (unsupported)",
                location=f"{carrier_label}:char[{tok.char_start}-{tok.char_end}]",
            ))
            continue

        # ── Find covering declarations ──────────────────────────
        covering = find_covering_declarations(tok, anchor_declarations)

        # ── Legacy fallback (TableCell.fact_id single-token path) ─
        if not covering and legacy_fact_id is not None and legacy_fact_id != "":
            # Only activate legacy when anchor_declarations is ALSO empty AND
            # there's exactly 1 non-whitelisted anchorable token in the whole cell
            # AND legacy_fact_id != None
            if not anchor_declarations:
                token_count = _count_anchorable_tokens_after_whitelist(
                    raw_text, whitelist, tokenize_fn
                )
                if token_count == 1:
                    # Activate legacy: treat cell.fact_id as covering this token
                    covering = [AnchorDeclaration(
                        token=tok.text,
                        fact_id=legacy_fact_id,
                        char_start=tok.char_start,
                        char_end=tok.char_end,
                    )]

        # ── BIND-6: duplicate binding ────────────────────────────
        if has_duplicate_fact_ids(covering):
            issues.append(BindingIssue(
                severity="error",
                issue_type="duplicate_binding",
                message=(
                    f"token '{tok.text}' at [{tok.char_start}-{tok.char_end}] "
                    f"covered by multiple different fact_ids"
                ),
                location=f"{carrier_label}:char[{tok.char_start}-{tok.char_end}]",
            ))
            continue

        # ── 0 covering → UNANCHORED ──────────────────────────────
        if len(covering) == 0:
            issues.append(BindingIssue(
                severity="error",
                issue_type="unanchored",
                message=(
                    f"{'identifier' if tok.kind == TokenKind.IDENTIFIER else 'numeric'} "
                    f"token '{tok.text}' at [{tok.char_start}-{tok.char_end}] "
                    f"not covered by any AnchorDeclaration"
                ),
                location=f"{carrier_label}:char[{tok.char_start}-{tok.char_end}]",
            ))
            continue

        # ── Unique covering declaration ──────────────────────────
        decl = covering[0]
        fact_id = decl.fact_id

        # ── BIND-5: fact_id syntax ───────────────────────────────
        err = is_valid_fact_id(fact_id)
        if err is not None:
            issues.append(BindingIssue(
                severity="error",
                issue_type="invalid_fact_id",
                message=f"AnchorDeclaration.fact_id '{fact_id}' invalid: {err}",
                location=f"{carrier_label}:char[{tok.char_start}-{tok.char_end}]",
            ))
            continue

        # ── Identifier path: BIND-7 ──────────────────────────────
        if tok.kind == TokenKind.IDENTIFIER:
            result = _validate_identifier_binding(
                tok=tok,
                fact_id=fact_id,
                carrier_label=carrier_label,
            )
            issues.extend(result.issues)

        # ── Numeric path: BIND-8 + §8.2 chain ────────────────────
        elif tok.kind == TokenKind.NUMERIC:
            result = _validate_numeric_binding(
                tok=tok,
                fact_id=fact_id,
                carrier_label=carrier_label,
                ground_truth_by_id=ground_truth_by_id,
                fact_display_spec=fact_display_spec,
            )
            issues.extend(result.issues)

    return issues


# ── BIND-7: identifier binding validation ───────────────────────────

def _validate_identifier_binding(
    *,
    tok: Token,
    fact_id: str,
    carrier_label: str,
) -> IdentifierBindingResult:
    """BIND-7: identifier token → fact_id binding validation.

    Rule: normalized_identifier == parse_fact_id(fact_id).instance_key
    INV-22: No scope_class inference — compare instance_key only.
    """
    result = IdentifierBindingResult(fact_id=fact_id)

    _, _, instance_key, _ = _full_parse(fact_id)
    norm_id = tok.normalized_identifier or tok.text

    if norm_id != instance_key:
        result.issues.append(BindingIssue(
            severity="error",
            issue_type="identifier_binding_mismatch",
            message=(
                f"identifier '{tok.text}' (normalized='{norm_id}') bound to "
                f"fact_id '{fact_id}' but instance_key='{instance_key}' — mismatch"
            ),
            location=f"{carrier_label}:char[{tok.char_start}-{tok.char_end}]",
            fact_id=fact_id,
        ))

    return result


# ── BIND-8 + §8.2: numeric binding + comparison chain ────────────────

def _validate_numeric_binding(
    *,
    tok: Token,
    fact_id: str,
    carrier_label: str,
    ground_truth_by_id: Optional[dict],
    fact_display_spec: Optional[dict],
) -> NumericBindingResult:
    """BIND-8 + §8.2 comparison chain for numeric tokens.

    Chain:
        numeric token
        → fact_id (already validated by caller: BIND-5)
        → G3 lookup (if provided)
        → parse_fact_id → derive_fact_type → fact_display_spec[fact_type]
        → snapshot.decimals
        → frozen_round(token_value, decimals) == G3.value (P0-1)

    Parallel: unit cascade.
    """
    result = NumericBindingResult(fact_id=fact_id)

    numeric_value = tok.numeric_value
    unit_text = tok.unit

    # ── Unit cascade ──────────────────────────────────────────
    quantity_kind: Optional[str] = None
    unit_matched: Optional[str] = None

    if unit_text:
        # Check against UNIT_TO_QUANTITY
        if unit_text in UNIT_TO_QUANTITY:
            quantity_kind = UNIT_TO_QUANTITY[unit_text]
            unit_matched = unit_text
        else:
            result.issues.append(BindingIssue(
                severity="error",
                issue_type="unknown_unit",
                message=(
                    f"numeric token '{tok.text}' has unit '{unit_text}' not in UNIT_TO_QUANTITY"
                ),
                location=f"{carrier_label}:char[{tok.char_start}-{tok.char_end}]",
                fact_id=fact_id,
            ))
            # Unit unknown → still proceed to value comparison (numeric body valid)
            # but unit cascade fails.

    # ── §8.2: G3 lookup ────────────────────────────────────────
    if ground_truth_by_id is None:
        return result  # No ground truth provided — can't run §8.2 chain

    g3 = ground_truth_by_id.get(fact_id)
    if g3 is None:
        result.issues.append(BindingIssue(
            severity="error",
            issue_type="invalid_fact_id",
            message=(
                f"fact_id '{fact_id}' bound by token '{tok.text}' "
                f"not found in this case's GroundTruthFact set"
            ),
            location=f"{carrier_label}:char[{tok.char_start}-{tok.char_end}]",
            fact_id=fact_id,
        ))
        return result

    # ── §8.2: fact_type chain ───────────────────────────────────
    fact_type = derive_fact_type(fact_id)

    if fact_display_spec is None:
        return result  # No display spec — can't do precision check

    spec = fact_display_spec.get(fact_type)
    if spec is None:
        result.issues.append(BindingIssue(
            severity="error",
            issue_type="precondition_error",
            message=(
                f"fact_display_spec missing entry for fact_type '{fact_type}' "
                f"(fact_id='{fact_id}') — missing display spec, cannot run §8.2 chain"
            ),
            location=f"{carrier_label}",
            fact_id=fact_id,
        ))
        return result

    decimals = spec.decimals
    result.quantity_kind = quantity_kind
    result.unit_matched = unit_matched

    # ── Unit cascade continued ────────────────────────────────
    # Priority 2: quantity_kind mismatch
    if quantity_kind is not None and quantity_kind != g3.quantity_kind:
        result.issues.append(BindingIssue(
            severity="error",
            issue_type="quantity_kind_mismatch",
            message=(
                f"token '{tok.text}' quantity_kind '{quantity_kind}' "
                f"!= G3 '{g3.quantity_kind}'"
            ),
            location=f"{carrier_label}:char[{tok.char_start}-{tok.char_end}]",
            fact_id=fact_id,
        ))

    # Priority 3: unit string mismatch (quantity_kind matched but unit string differs)
    elif unit_text is not None and g3.unit is not None and unit_matched != g3.unit:
        result.issues.append(BindingIssue(
            severity="error",
            issue_type="unit_mismatch",
            message=(
                f"token '{tok.text}' unit '{unit_matched}' "
                f"!= G3 unit '{g3.unit}'"
            ),
            location=f"{carrier_label}:char[{tok.char_start}-{tok.char_end}]",
            fact_id=fact_id,
        ))

    # ── §8.2: P0-1 VALUE.CONSISTENCY ────────────────────────────
    try:
        token_value_rounded = frozen_round(numeric_value, decimals)
        g3_value_rounded = frozen_round(g3.value, decimals)
    except (ValueError, TypeError) as e:
        result.issues.append(BindingIssue(
            severity="error",
            issue_type="precondition_error",
            message=f"frozen_round failed: {e}",
            location=f"{carrier_label}",
            fact_id=fact_id,
        ))
        return result

    if token_value_rounded != g3_value_rounded:
        result.issues.append(BindingIssue(
            severity="error",
            issue_type="value_mismatch",
            message=(
                f"frozen_round({numeric_value}, {decimals})={token_value_rounded} "
                f"!= G3.value={g3_value_rounded} "
                f"(frozen_round({g3.value}, {decimals})={g3_value_rounded})"
            ),
            location=f"{carrier_label}:char[{tok.char_start}-{tok.char_end}]",
            fact_id=fact_id,
        ))

    return result


# ── TableCell 便捷入口 ──────────────────────────────────────────────

def bind_table_cell(
    *,
    cell: TableCell,
    cell_location: str,                 # e.g. "table[table-1][row0][col1]"
    whitelist: WhitelistRegistry,
    tokenize_fn,
    ground_truth_by_id: Optional[dict] = None,
    fact_display_spec: Optional[dict] = None,
) -> List[BindingIssue]:
    """Convenience wrapper: execute binding pipeline on a single TableCell.

    Auto-passes cell.fact_id as legacy_fact_id.
    """
    return bind_and_validate(
        raw_text=cell.raw_text,
        anchor_declarations=cell.anchor_declarations,
        carrier_label=cell_location,
        whitelist=whitelist,
        tokenize_fn=tokenize_fn,
        legacy_fact_id=cell.fact_id,
        ground_truth_by_id=ground_truth_by_id,
        fact_display_spec=fact_display_spec,
    )


# ── RenderedSegment 便捷入口 ────────────────────────────────────────

def bind_rendered_segment(
    *,
    segment: "RenderedSegment",
    whitelist: WhitelistRegistry,
    tokenize_fn,
    ground_truth_by_id: Optional[dict] = None,
    fact_display_spec: Optional[dict] = None,
) -> List[BindingIssue]:
    """Convenience wrapper: execute binding pipeline on a RenderedSegment.

    No legacy_fact_id — RenderedSegment does NOT have cell.fact_id semantics.
    """
    return bind_and_validate(
        raw_text=segment.raw_text,
        anchor_declarations=segment.anchor_declarations,
        carrier_label=segment.segment_location,
        whitelist=whitelist,
        tokenize_fn=tokenize_fn,
        legacy_fact_id=None,   # RenderedSegment path never uses legacy
        ground_truth_by_id=ground_truth_by_id,
        fact_display_spec=fact_display_spec,
    )
