"""Step 7-E Accuracy Validator — B5 TABLE-NUMERIC-BINDING + B4 回归测试.

覆盖：
  B5 必须测试（13+ 项）+ B4 回归测试
  + frozen_round 异常行为
  + Unit Registry exact equality
  + ActualIssue build-only 守卫
  + Tokenizer candidate 反例

冻结依据：Step_7_E_Coding_Contract_v10.md + Step_7_E_B5_Design_Check.md

绝对禁止：修改测试来掩盖失败。
"""
from __future__ import annotations

import pytest
from typing import List

from eval.accuracy import (
    AnchorDeclaration,
    RenderedSegment,
    TableCell,
    StructuredTable,
    SystemOutput,
    ActualIssue,
    frozen_round,
    NUMERIC_TOKEN_RE,
    IDENTIFIER_TOKEN_RE,
    tokenize,
    UNIT_TO_QUANTITY,
    QUANTITY_KINDS,
    WhitelistEntry,
    WhitelistRegistry,
    FactDisplaySpecSnapshot,
    bind_and_validate,
    bind_table_cell,
    bind_rendered_segment,
    find_covering_declarations,
    is_span_contained,
    has_duplicate_fact_ids,
    derive_fact_type,
    parse_fact_id,
)
from eval.accuracy.tokenizer import Token, TokenKind
from eval.accuracy.binding import BindingIssue, _full_parse

# Step 7-D G3 / types for test fixtures
from eval.types import GroundTruthFact


# ══════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════

def _make_whitelist(patterns: List[str]) -> WhitelistRegistry:
    entries = [
        WhitelistEntry(
            pattern=p,
            reason="test whitelist",
            scope="global",
            confirmed_by="unit_test",
        )
        for p in patterns
    ]
    return WhitelistRegistry(entries=entries)


def _whitelist_gb_full() -> WhitelistRegistry:
    """Specialized whitelist for GB 50292-2015 — pattern includes trailing whitespace
    because tokenizer regex \s* absorbs trailing spaces into match span."""
    return _make_whitelist([r"GB 50292-2015\s*"])


def _make_g3_by_id(facts: List[GroundTruthFact]) -> dict:
    return {f.fact_id: f for f in facts}


def _make_display_spec(fact_type_decimals: dict) -> dict:
    return {ft: FactDisplaySpecSnapshot(ft, d) for ft, d in fact_type_decimals.items()}


def _has_issue_type(issues: List[BindingIssue], issue_type: str) -> bool:
    return any(i.issue_type == issue_type for i in issues)


def _find_issue_types(issues: List[BindingIssue]) -> set:
    return {i.issue_type for i in issues}


# ══════════════════════════════════════════════════════════════════════
# Frozen constants
# ══════════════════════════════════════════════════════════════════════

P0_RULE_IDS = frozenset({
    "VALUE.CONSISTENCY",
    "TABLE.INTERNAL",
    "LOGIC.CONSISTENCY",
    "ANCHOR.BINDING",
    "CONCLUSION.DIRECTION",
    "CONCLUSION.COVERAGE",
    "EXPECTED.HIT",
})


# ══════════════════════════════════════════════════════════════════════
# frozen_round (§12 —冻结，B2 异常行为)
# ══════════════════════════════════════════════════════════════════════

class TestFrozenRound:
    def test_basic(self):
        assert frozen_round(2.345, 2) == 2.35
        assert frozen_round(2.344, 2) == 2.34
        assert frozen_round(0, 0) == 0.0

    def test_none_raises(self):
        with pytest.raises(ValueError, match="value must not be None"):
            frozen_round(None, 2)

    def test_nan_raises(self):
        with pytest.raises(ValueError, match="must be finite"):
            frozen_round(float("nan"), 2)

    def test_pos_inf_raises(self):
        with pytest.raises(ValueError, match="must be finite"):
            frozen_round(float("inf"), 2)

    def test_neg_inf_raises(self):
        with pytest.raises(ValueError, match="must be finite"):
            frozen_round(float("-inf"), 2)

    def test_decimals_not_int_raises(self):
        with pytest.raises(TypeError, match="decimals must be"):
            frozen_round(1.2, "2")

    def test_decimals_negative_raises(self):
        with pytest.raises(TypeError, match="decimals must be"):
            frozen_round(1.2, -1)

    def test_decimals_zero(self):
        assert frozen_round(2.7, 0) == 3.0
        assert frozen_round(2.4, 0) == 2.0

    def test_no_banker_rounding(self):
        """frozen_round uses ROUND_HALF_UP — Python round() uses banker's."""
        assert frozen_round(2.5, 0) == 3.0  # HALF_UP → 3
        # Python round(2.5) == 2 (banker's) — we MUST NOT match that


# ══════════════════════════════════════════════════════════════════════
# ActualIssue build-only 守卫 (§11 — B3)
# ══════════════════════════════════════════════════════════════════════

class TestActualIssue:
    def test_direct_construction_raises(self):
        """Any ActualIssue(...) direct construction → TypeError."""
        with pytest.raises(TypeError, match="build-only"):
            ActualIssue(
                rule_id="ANCHOR.BINDING",
                severity="error",
                issue_type="unanchored",
                location="loc",
                message="msg",
            )

    def test_build_produces_valid_instance(self):
        ai = ActualIssue.build(
            rule_id="ANCHOR.BINDING",
            severity="error",
            issue_type="unanchored",
            location="rendered_segments[0]:char[0-4]",
            message="test",
            fact_id="fact:component.K001.id",
        )
        assert ai.rule_id == "ANCHOR.BINDING"
        assert ai.issue_type == "unanchored"
        assert ai.identity == ("unanchored", "rendered_segments[0]:char[0-4]",
                               "fact:component.K001.id", None, None, None)
        assert ai.issue_id is not None and len(ai.issue_id) == 64  # SHA-256 hex

    def test_identity_deterministic(self):
        ai1 = ActualIssue.build("R", "e", "t", "l", "m", fact_id="f")
        ai2 = ActualIssue.build("R", "e", "t", "l", "m", fact_id="f")
        assert ai1.issue_id == ai2.issue_id

    def test_identity_change_changes_issue_id(self):
        ai1 = ActualIssue.build("R", "e", "t", "l", "m", fact_id="f1")
        ai2 = ActualIssue.build("R", "e", "t", "l", "m", fact_id="f2")
        assert ai1.issue_id != ai2.issue_id

    def test_identity_six_tuple_order_frozen(self):
        """identity order: issue_type, location, fact_id, evaluation_id, occurrence_id, table_aggregate"""
        ai = ActualIssue.build(
            rule_id="R", severity="e", issue_type="TYPE",
            location="LOC", message="M",
            fact_id="F", evaluation_id="E", occurrence_id="O", table_aggregate="T",
        )
        assert ai.identity[0] == "TYPE"
        assert ai.identity[1] == "LOC"
        assert ai.identity[2] == "F"
        assert ai.identity[3] == "E"
        assert ai.identity[4] == "O"
        assert ai.identity[5] == "T"


# ══════════════════════════════════════════════════════════════════════
# Unit Registry (§3.2 — exact equality, A-4)
# ══════════════════════════════════════════════════════════════════════

class TestUnitRegistry:
    def test_exact_keys_and_values(self):
        """UNIT_TO_QUANTITY frozen dict — A-4 exact equality check baseline."""
        assert UNIT_TO_QUANTITY == {
            "MPa": "pressure", "Pa": "pressure", "kPa": "pressure",
            "GPa": "pressure", "N/mm²": "pressure", "kN/m²": "pressure",
            "m": "length", "mm": "length", "cm": "length", "km": "length",
            "m²": "area", "mm²": "area", "cm²": "area",
            "m³": "volume", "mm³": "volume",
            "kg": "mass", "t": "mass", "g": "mass",
            "N": "force", "kN": "force",
            "Hz": "frequency", "%": "ratio",
        }

    def test_all_quantity_kinds_in_registry(self):
        """Every value in UNIT_TO_QUANTITY must be in QUANTITY_KINDS."""
        for qk in UNIT_TO_QUANTITY.values():
            assert qk in QUANTITY_KINDS, f"UNIT_TO_QUANTITY value '{qk}' not in QUANTITY_KINDS"


# ══════════════════════════════════════════════════════════════════════
# Tokenizer (§5)
# ══════════════════════════════════════════════════════════════════════

class TestTokenizer:
    def test_basic_numeric(self):
        tokens = tokenize("2.3m")
        assert len(tokens) == 1
        assert tokens[0].kind == TokenKind.NUMERIC
        assert tokens[0].text == "2.3m"
        assert tokens[0].unit == "m"
        assert tokens[0].numeric_value == 2.3

    def test_identifier(self):
        tokens = tokenize("K001")
        assert len(tokens) == 1
        assert tokens[0].kind == TokenKind.IDENTIFIER
        assert tokens[0].normalized_identifier == "K001"

    def test_st001(self):
        tokens = tokenize("ST001")
        assert len(tokens) == 1
        assert tokens[0].kind == TokenKind.IDENTIFIER
        assert tokens[0].normalized_identifier == "ST001"

    def test_k001_plus_numeric(self):
        tokens = tokenize("K001：32.4MPa")
        kinds = [t.kind for t in tokens]
        assert TokenKind.IDENTIFIER in kinds
        assert TokenKind.NUMERIC in kinds
        id_tok = next(t for t in tokens if t.kind == TokenKind.IDENTIFIER)
        num_tok = next(t for t in tokens if t.kind == TokenKind.NUMERIC)
        assert id_tok.normalized_identifier == "K001"
        assert num_tok.unit == "MPa"
        assert num_tok.numeric_value == 32.4

    def test_range(self):
        """§8.3 — range '2.0～2.5m' → 2 independent numeric tokens."""
        tokens = tokenize("2.0～2.5m")
        assert len(tokens) == 2
        assert all(t.kind == TokenKind.NUMERIC for t in tokens)

    def test_multi_numeric(self):
        tokens = tokenize("2.3m / 2.5m")
        assert len(tokens) == 2
        assert all(t.kind == TokenKind.NUMERIC for t in tokens)

    def test_unit_capture_complete_b1(self):
        """§5.4 B1 — unit candidate full token boundary, no truncation."""
        t = tokenize("12.5N/mm²")[0]
        assert t.unit == "N/mm²"
        t = tokenize("12.5kN/m²")[0]
        assert t.unit == "kN/m²"
        t = tokenize("32.5%")[0]
        assert t.unit == "%"
        t = tokenize("32.4m3")[0]
        assert t.unit == "m3"         # NOT truncated to "m"
        t = tokenize("32.4N/mm2")[0]
        assert t.unit == "N/mm2"      # NOT truncated to "N/mm"
        t = tokenize("12.5N/mm²x")[0]
        assert t.unit == "N/mm²x"     # NOT truncated to "N/mm²"

    def test_unit_unknown(self):
        """§5.4 U-3 — unknown unit 'psi' → unit captured as 'psi', UNKNOWN_UNIT at Stage D."""
        t = tokenize("32.4psi")[0]
        assert t.unit == "psi"
        assert t.numeric_value == 32.4  # numeric body preserved

    def test_candidate反例_prevents_numeric(self):
        """§5.3 — H2O / A4 / ISO9001 / GB50292: 前置字母阻断 numeric candidate."""
        # These should produce NO numeric token (lookbehind [0-9A-Za-z] fails)
        tokens = tokenize("H2O")
        num_tokens = [t for t in tokens if t.kind == TokenKind.NUMERIC]
        assert len(num_tokens) == 0, f"H2O should produce no numeric token, got {num_tokens}"

        tokens = tokenize("GB50292")
        num_tokens = [t for t in tokens if t.kind == TokenKind.NUMERIC]
        assert len(num_tokens) == 0, f"GB50292 should produce no numeric token, got {num_tokens}"

    def test_gb_with_space_produces_numeric(self):
        """§5.3 — 'GB 50292-2015' (space separated): '50292' has space before → numeric candidate EXISTS."""
        tokens = tokenize("GB 50292-2015")
        num_tokens = [t for t in tokens if t.kind == TokenKind.NUMERIC]
        assert len(num_tokens) >= 1
        # "50292" and possibly "2015" are numeric candidates → whitelist must exempt them

    def test_empty_text(self):
        assert tokenize("") == []


# ══════════════════════════════════════════════════════════════════════
# Whitelist (§8.4 — span containment, partial overlap NOT exempt)
# ══════════════════════════════════════════════════════════════════════

class TestWhitelist:
    def test_full_containment_exempts(self):
        text = "依据 GB 50292-2015 检测"
        wl = _whitelist_gb_full()  # pattern covers trailing whitespace too
        tokens = tokenize(text)
        for tok in tokens:
            assert wl.is_span_whitelisted(tok.char_start, tok.char_end, text), \
                f"token '{tok.text}' [{tok.char_start}-{tok.char_end}] should be exempt by whitelist"

    def test_partial_overlap_not_exempt(self):
        """§8.4 — partial overlap (intersect but NOT contain) → NOT exempt."""
        wl = _make_whitelist([r"GB 50292$"])  # pattern stops before "-2015"
        text = "依据 GB 50292-2015 检测"
        tokens = tokenize(text)
        for tok in tokens:
            if tok.char_start == 6:  # "50292" token at [6-11]
                # whitelist match "GB 50292" is [3-11] exactly containing this token
                # → this one SHOULD be exempt
                pass
            elif tok.char_start == 12:  # "2015 " token at [12-17]
                # whitelist [3-11] does NOT reach [12-17] → no containment → NOT exempt
                assert not wl.is_span_whitelisted(12, 17, text), \
                    "token [12-17] should NOT be exempt (no containment)"


# ══════════════════════════════════════════════════════════════════════
# B5 必须测试 — 全部 13 项
# ══════════════════════════════════════════════════════════════════════

# ── B5 Test 1: 单 token legacy ────────────────────────────────────────

class TestB5SingleTokenLegacy:
    """Case: '2.3m' + cell.fact_id → legacy path activates → enters BIND-8 → §8.2."""

    def test_legacy_activates_when_anchor_decls_empty_and_one_token(self):
        cell = TableCell(raw_text="2.3m", fact_id="fact:component.K001.concrete_strength")
        wl = WhitelistRegistry()
        issues = bind_table_cell(
            cell=cell,
            cell_location="table[table-1][0][1]",
            whitelist=wl,
            tokenize_fn=tokenize,
        )
        # No UNANCHORED — legacy path provided the binding
        assert not _has_issue_type(issues, "unanchored"), \
            f"legacy path should prevent UNANCHORED, got: {_find_issue_types(issues)}"

    def test_legacy_inert_when_anchor_decls_present(self):
        """If explicit declarations exist, legacy fact_id is inert (no double-bind)."""
        cell = TableCell(
            raw_text="2.3m",
            fact_id="fact:component.K001.concrete_strength",
            anchor_declarations=[AnchorDeclaration(
                token="2.3m",
                fact_id="fact:component.K002.concrete_strength",
                char_start=0, char_end=4,
            )],
        )
        wl = WhitelistRegistry()
        issues = bind_table_cell(
            cell=cell,
            cell_location="loc",
            whitelist=wl,
            tokenize_fn=tokenize,
        )
        # Should bind to K002's fact (explicit decl takes precedence)
        assert not _has_issue_type(issues, "unanchored")


# ── B5 Test 2: 单 token explicit ──────────────────────────────────────

class TestB5SingleTokenExplicit:
    """'2.3m' + 1 AnchorDeclaration → PASS."""

    def test_explicit_binding(self):
        g3 = [GroundTruthFact(
            fact_id="fact:component.K001.concrete_strength",
            value=2.3, unit="MPa", quantity_kind="pressure", precision=1,
        )]
        cell = TableCell(
            raw_text="2.3MPa",
            anchor_declarations=[AnchorDeclaration(
                token="2.3MPa", fact_id="fact:component.K001.concrete_strength",
                char_start=0, char_end=6,
            )],
        )
        issues = bind_table_cell(
            cell=cell, cell_location="loc",
            whitelist=WhitelistRegistry(),
            tokenize_fn=tokenize,
            ground_truth_by_id=_make_g3_by_id(g3),
            fact_display_spec=_make_display_spec({"component.concrete_strength": 1}),
        )
        assert issues == [], f"Expected no issues, got {[(i.issue_type, i.message) for i in issues]}"


# ── B5 Test 3: 多 numeric ──────────────────────────────────────────────

class TestB5MultiNumeric:
    """'2.3m / 2.5m' + 2 AnchorDeclaration → 2 tokens bound to different fact_ids."""

    def test_two_declarations_pass(self):
        # Field order: fact_id, value, quantity_kind, precision, unit
        g3 = [
            GroundTruthFact("fact:defect.C001.width", 2.3, "length", 1, "mm"),
            GroundTruthFact("fact:defect.C001.length", 2.5, "length", 1, "m"),
        ]
        # "2.3mm / 2.5m" → tokens [0-5] '2.3mm', [8-12] '2.5m'
        cell = TableCell(
            raw_text="2.3mm / 2.5m",
            anchor_declarations=[
                AnchorDeclaration("2.3mm", "fact:defect.C001.width", 0, 5),
                AnchorDeclaration("2.5m", "fact:defect.C001.length", 8, 12),
            ],
        )
        issues = bind_table_cell(
            cell=cell, cell_location="loc",
            whitelist=WhitelistRegistry(),
            tokenize_fn=tokenize,
            ground_truth_by_id=_make_g3_by_id(g3),
            fact_display_spec=_make_display_spec({
                "defect.width": 1, "defect.length": 1,
            }),
        )
        assert issues == []

    def test_only_cell_fact_id_inert(self):
        """'2.3m / 2.5m' + cell.fact_id → cell.fact_id inert → both UNANCHORED."""
        cell = TableCell(
            raw_text="2.3m / 2.5m",
            fact_id="fact:component.K001.concrete_strength",
        )
        issues = bind_table_cell(
            cell=cell, cell_location="loc",
            whitelist=WhitelistRegistry(),
            tokenize_fn=tokenize,
        )
        # Two tokens → legacy requires exactly 1 → inert → both UNANCHORED
        unanchored = [i for i in issues if i.issue_type == "unanchored"]
        assert len(unanchored) == 2, \
            f"Expected 2 UNANCHORED (legacy inert for multi-token), got {len(unanchored)}"


# ── B5 Test 4: range ──────────────────────────────────────────────────

class TestB5Range:
    """'2.0～2.5m' + 2 AnchorDeclaration → 2 tokens independent binding."""

    def test_range_two_declarations(self):
        g3 = [
            GroundTruthFact("fact:component.K001.min_strength", 2.0, "pressure", 1, "MPa"),
            GroundTruthFact("fact:component.K001.max_strength", 2.5, "pressure", 1, "MPa"),
        ]
        # "2.0～2.5MPa" → tokens [0-3] '2.0', [4-10] '2.5MPa'
        cell = TableCell(
            raw_text="2.0～2.5MPa",
            anchor_declarations=[
                AnchorDeclaration("2.0", "fact:component.K001.min_strength", 0, 3),
                AnchorDeclaration("2.5MPa", "fact:component.K001.max_strength", 4, 10),
            ],
        )
        issues = bind_table_cell(
            cell=cell, cell_location="loc",
            whitelist=WhitelistRegistry(),
            tokenize_fn=tokenize,
            ground_truth_by_id=_make_g3_by_id(g3),
            fact_display_spec=_make_display_spec({
                "component.min_strength": 1, "component.max_strength": 1,
            }),
        )
        assert issues == []


# ── B5 Test 5: identifier + numeric ────────────────────────────────────

class TestB5IdentifierPlusNumeric:
    """'K001：32.4MPa' + K001→.id + 32.4MPa→.concrete_strength → dual binding."""

    def test_dual_binding(self):
        g3 = [
            GroundTruthFact("fact:component.K001.id", "K001", "dimensionless", 0, None),
            GroundTruthFact("fact:component.K001.concrete_strength", 32.4, "pressure", 1, "MPa"),
        ]
        # "K001：32.4MPa" → identifier [0-4] 'K001', numeric [5-12] '32.4MPa'
        cell = TableCell(
            raw_text="K001：32.4MPa",
            anchor_declarations=[
                AnchorDeclaration("K001", "fact:component.K001.id", 0, 4),
                AnchorDeclaration("32.4MPa", "fact:component.K001.concrete_strength", 5, 12),
            ],
        )
        issues = bind_table_cell(
            cell=cell, cell_location="loc",
            whitelist=WhitelistRegistry(),
            tokenize_fn=tokenize,
            ground_truth_by_id=_make_g3_by_id(g3),
            fact_display_spec=_make_display_spec({
                "component.id": 0, "component.concrete_strength": 1,
            }),
        )
        assert issues == [], f"Expected no issues, got {[(i.issue_type, i.message) for i in issues]}"

    def test_only_cell_fact_id_inert(self):
        """'K001：32.4MPa' + cell.fact_id → inert → both UNANCHORED."""
        cell = TableCell(
            raw_text="K001：32.4MPa",
            fact_id="fact:component.K001.concrete_strength",
        )
        issues = bind_table_cell(
            cell=cell, cell_location="loc",
            whitelist=WhitelistRegistry(),
            tokenize_fn=tokenize,
        )
        # identifier + numeric = 2 tokens → legacy requires 1 → inert → both UNANCHORED
        unanchored = [i for i in issues if i.issue_type == "unanchored"]
        assert len(unanchored) == 2


# ── B5 Test 6: multi-token + cell.fact_id → inert ────────────────────

class TestB5MultiTokenWithLegacyInert:
    """'2.3m / 2.5m' + cell.fact_id → fact_id inert → both UNANCHORED."""

    def test_inert(self):
        cell = TableCell(
            raw_text="2.3m / 2.5m",
            fact_id="fact:component.K001.area",
        )
        issues = bind_table_cell(
            cell=cell, cell_location="loc",
            whitelist=WhitelistRegistry(),
            tokenize_fn=tokenize,
        )
        unanchored = [i for i in issues if i.issue_type == "unanchored"]
        assert len(unanchored) == 2


# ── B5 Test 7: identifier + numeric + cell.fact_id → inert ────────────

class TestB5IdPlusNumericWithLegacyInert:
    """'K001：32.4MPa' + cell.fact_id → fact_id inert → both UNANCHORED."""

    def test_inert(self):
        cell = TableCell(
            raw_text="K001：32.4MPa",
            fact_id="fact:component.K001.concrete_strength",
        )
        issues = bind_table_cell(
            cell=cell, cell_location="loc",
            whitelist=WhitelistRegistry(),
            tokenize_fn=tokenize,
        )
        unanchored = [i for i in issues if i.issue_type == "unanchored"]
        assert len(unanchored) == 2


# ── B5 Test 8: whitelist exempts ──────────────────────────────────────

class TestB5WhitelistExempts:
    """'依据 GB 50292-2015 检测' → whitelist span covers numeric → exempt."""

    def test_whitelist_exempt(self):
        cell = TableCell(raw_text="依据 GB 50292-2015 检测")
        wl = _whitelist_gb_full()  # covers trailing whitespace
        issues = bind_table_cell(
            cell=cell, cell_location="loc",
            whitelist=wl,
            tokenize_fn=tokenize,
        )
        # All numeric tokens are whitelisted → no UNANCHORED
        assert not _has_issue_type(issues, "unanchored"), \
            f"Expected no unanchored, got {[(i.issue_type, i.message) for i in issues]}"


# ── B5 Test 9: partial overlap → not covered ───────────────────────────

class TestB5PartialOverlap:
    """Whitelist pattern partially overlaps token → NOT exempt → UNANCHORED."""

    def test_partial_overlap_not_exempt(self):
        cell = TableCell(raw_text="依据 GB 50292-2015 检测")
        wl = _make_whitelist([r"GB 50292$"])  # pattern stops before "-2015"
        issues = bind_table_cell(
            cell=cell, cell_location="loc",
            whitelist=wl,
            tokenize_fn=tokenize,
        )
        # Some tokens may still be UNANCHORED (partial overlap not exempt)
        assert _has_issue_type(issues, "unanchored")


# ── B5 Test 10: duplicate binding ─────────────────────────────────────

class TestB5DuplicateBinding:
    """Same token covered by ≥2 declarations with different fact_ids → DUPLICATE_BINDING."""

    def test_duplicate(self):
        cell = TableCell(
            raw_text="2.3m",
            anchor_declarations=[
                AnchorDeclaration("2.3m", "fact:component.K001.width", 0, 4),
                AnchorDeclaration("2.3m", "fact:defect.C001.width", 0, 4),
            ],
        )
        issues = bind_table_cell(
            cell=cell, cell_location="loc",
            whitelist=WhitelistRegistry(),
            tokenize_fn=tokenize,
        )
        assert _has_issue_type(issues, "duplicate_binding")


# ── B5 Test 11: invalid fact_id ───────────────────────────────────────

class TestB5InvalidFactId:
    """AnchorDeclaration.fact_id fails is_valid_fact_id() → INVALID_FACT_ID."""

    def test_invalid_syntax(self):
        cell = TableCell(
            raw_text="2.3m",
            anchor_declarations=[
                AnchorDeclaration("2.3m", "not-a-valid-fact-id", 0, 4),
            ],
        )
        issues = bind_table_cell(
            cell=cell, cell_location="loc",
            whitelist=WhitelistRegistry(),
            tokenize_fn=tokenize,
        )
        assert _has_issue_type(issues, "invalid_fact_id")


# ── B5 Test 12: value mismatch ────────────────────────────────────────

class TestB5ValueMismatch:
    """Bind valid + fact exists in G3 but value doesn't match → P0-1 VALUE.CONSISTENCY FAIL."""

    def test_value_mismatch(self):
        g3 = [GroundTruthFact(
            fact_id="fact:component.K001.concrete_strength",
            value=32.5, unit="MPa", quantity_kind="pressure", precision=1,
        )]
        cell = TableCell(
            raw_text="32.4MPa",
            anchor_declarations=[AnchorDeclaration(
                token="32.4MPa", fact_id="fact:component.K001.concrete_strength",
                char_start=0, char_end=8,
            )],
        )
        issues = bind_table_cell(
            cell=cell, cell_location="loc",
            whitelist=WhitelistRegistry(),
            tokenize_fn=tokenize,
            ground_truth_by_id=_make_g3_by_id(g3),
            fact_display_spec=_make_display_spec({"component.concrete_strength": 1}),
        )
        assert _has_issue_type(issues, "value_mismatch"), \
            f"Expected value_mismatch, got {_find_issue_types(issues)}"


# ── B5 Test 13: Table headers use same binding mechanism ──────────────

class TestB5TableHeaders:
    """Headers cells = same TableCell type → same binding mechanism."""

    def test_header_with_id(self):
        g3 = [GroundTruthFact(
            fact_id="fact:component.K001.id",
            value="K001", unit=None, quantity_kind="dimensionless", precision=0,
        )]
        table = StructuredTable(
            table_id="table-1",
            headers=[TableCell(
                raw_text="K001",
                anchor_declarations=[AnchorDeclaration(
                    "K001", "fact:component.K001.id", 0, 4,
                )],
            )],
        )
        issues = bind_table_cell(
            cell=table.headers[0],
            cell_location="table[table-1][header][0]",
            whitelist=WhitelistRegistry(),
            tokenize_fn=tokenize,
            ground_truth_by_id=_make_g3_by_id(g3),
            fact_display_spec=_make_display_spec({"component.id": 0}),
        )
        assert issues == []


# ══════════════════════════════════════════════════════════════════════
# B4 回归测试 —— 必须保持全部通过
# ══════════════════════════════════════════════════════════════════════

class TestB4Regression:
    """B4 rendered_segments binding 零回归。

    B5 实现不得改变 B4 行为——两个载体走完全相同的管道。
    """

    def test_rendered_segment_same_pipeline(self):
        """RenderedSegment 走完全相同的 bind_and_validate 管道。"""
        g3 = [
            GroundTruthFact("fact:defect.C001.length", 2.3, "length", 1, "m"),
            GroundTruthFact("fact:defect.C001.width", 0.15, "length", 2, "mm"),
        ]
        # "裂缝长 2.3m，宽 0.15mm" → [4-8] '2.3m', [11-17] '0.15mm'
        seg = RenderedSegment(
            segment_location="prose[section-1]",
            raw_text="裂缝长 2.3m，宽 0.15mm",
            anchor_declarations=[
                AnchorDeclaration("2.3m", "fact:defect.C001.length", 4, 8),
                AnchorDeclaration("0.15mm", "fact:defect.C001.width", 11, 17),
            ],
        )
        issues = bind_rendered_segment(
            segment=seg,
            whitelist=WhitelistRegistry(),
            tokenize_fn=tokenize,
            ground_truth_by_id=_make_g3_by_id(g3),
            fact_display_spec=_make_display_spec({
                "defect.length": 1, "defect.width": 2,
            }),
        )
        assert issues == []

    def test_rendered_segment_unanchored(self):
        seg = RenderedSegment(
            segment_location="prose[0]",
            raw_text="裂缝长 2.3m",
            anchor_declarations=[],  # no decls
        )
        issues = bind_rendered_segment(
            segment=seg,
            whitelist=WhitelistRegistry(),
            tokenize_fn=tokenize,
        )
        assert _has_issue_type(issues, "unanchored")

    def test_rendered_segment_range(self):
        seg = RenderedSegment(
            segment_location="prose[0]",
            raw_text="约 2.0～2.5m",
            anchor_declarations=[
                AnchorDeclaration("2.0", "fact:component.K001.min", 3, 6),
                AnchorDeclaration("2.5m", "fact:component.K001.max", 7, 11),
            ],
        )
        issues = bind_rendered_segment(
            segment=seg,
            whitelist=WhitelistRegistry(),
            tokenize_fn=tokenize,
        )
        assert not _has_issue_type(issues, "unanchored")

    def test_rendered_segment_no_legacy(self):
        """RenderedSegment NEVER uses legacy cell.fact_id (it doesn't have one)."""
        seg = RenderedSegment(
            segment_location="prose[0]",
            raw_text="2.3m",
            anchor_declarations=[],  # no decls — no legacy fallback possible
        )
        issues = bind_rendered_segment(
            segment=seg,
            whitelist=WhitelistRegistry(),
            tokenize_fn=tokenize,
        )
        # Should be UNANCHORED — no legacy path available
        assert _has_issue_type(issues, "unanchored")

    def test_rendered_segment_whitelist(self):
        seg = RenderedSegment(
            segment_location="prose[0]",
            raw_text="依据 GB 50292-2015 检测",
        )
        wl = _whitelist_gb_full()  # covers trailing whitespace
        issues = bind_rendered_segment(
            segment=seg,
            whitelist=wl,
            tokenize_fn=tokenize,
        )
        assert not _has_issue_type(issues, "unanchored"), \
            f"Expected no unanchored, got {[(i.issue_type, i.message) for i in issues]}"

    def test_rendered_segment_unknown_unit(self):
        seg = RenderedSegment(
            segment_location="prose[0]",
            raw_text="强度 32.4psi",
            anchor_declarations=[AnchorDeclaration(
                "32.4psi", "fact:component.K001.concrete_strength", 3, 10,
            )],
        )
        issues = bind_rendered_segment(
            segment=seg,
            whitelist=WhitelistRegistry(),
            tokenize_fn=tokenize,
        )
        assert _has_issue_type(issues, "unknown_unit")

    def test_rendered_segment_unsupported_sign(self):
        seg = RenderedSegment(
            segment_location="prose[0]",
            raw_text="公差 ±3.2MPa",
            anchor_declarations=[AnchorDeclaration(
                "±3.2MPa", "fact:component.K001.tolerance", 3, 11,
            )],
        )
        issues = bind_rendered_segment(
            segment=seg,
            whitelist=WhitelistRegistry(),
            tokenize_fn=tokenize,
        )
        assert _has_issue_type(issues, "unsupported_sign")

    def test_rendered_segment_identifier_binding(self):
        # "构件 K001 强度为 32.4MPa" → identifier [0-7] '构件 K001', numeric [12-19] '32.4MPa'
        seg = RenderedSegment(
            segment_location="prose[0]",
            raw_text="构件 K001 强度为 32.4MPa",
            anchor_declarations=[
                AnchorDeclaration("构件 K001", "fact:component.K001.id", 0, 7),
                AnchorDeclaration("32.4MPa", "fact:component.K001.concrete_strength", 12, 19),
            ],
        )
        issues = bind_rendered_segment(
            segment=seg,
            whitelist=WhitelistRegistry(),
            tokenize_fn=tokenize,
        )
        assert not _has_issue_type(issues, "unanchored")
        assert not _has_issue_type(issues, "identifier_binding_mismatch")

    def test_rendered_segment_identifier_mismatch(self):
        # "构件 K001 强度为 32.4MPa" → identifier [0-7], numeric [12-19]
        seg = RenderedSegment(
            segment_location="prose[0]",
            raw_text="构件 K001 强度为 32.4MPa",
            anchor_declarations=[
                # Wrong: binding K001 to K002.id
                AnchorDeclaration("构件 K001", "fact:component.K002.id", 0, 7),
            ],
        )
        issues = bind_rendered_segment(
            segment=seg,
            whitelist=WhitelistRegistry(),
            tokenize_fn=tokenize,
        )
        assert _has_issue_type(issues, "identifier_binding_mismatch")


# ══════════════════════════════════════════════════════════════════════
# §8.2 comparison chain tests
# ══════════════════════════════════════════════════════════════════════

class TestComparisonChain:
    def test_chain_pass(self):
        g3 = [GroundTruthFact(
            fact_id="fact:component.K001.concrete_strength",
            value=32.4, unit="MPa", quantity_kind="pressure", precision=1,
        )]
        cell = TableCell(
            raw_text="32.4MPa",
            anchor_declarations=[AnchorDeclaration(
                "32.4MPa", "fact:component.K001.concrete_strength", 0, 8,
            )],
        )
        issues = bind_table_cell(
            cell=cell, cell_location="loc",
            whitelist=WhitelistRegistry(),
            tokenize_fn=tokenize,
            ground_truth_by_id=_make_g3_by_id(g3),
            fact_display_spec=_make_display_spec({"component.concrete_strength": 1}),
        )
        assert issues == []

    def test_chain_quantity_kind_mismatch(self):
        g3 = [GroundTruthFact(
            fact_id="fact:component.K001.concrete_strength",
            value=32.4, unit="MPa", quantity_kind="pressure", precision=1,
        )]
        # token unit = "m" (length), G3 quantity_kind = "pressure"
        cell = TableCell(
            raw_text="32.4m",  # unit "m" → length quantity_kind
            anchor_declarations=[AnchorDeclaration(
                "32.4m", "fact:component.K001.concrete_strength", 0, 5,
            )],
        )
        issues = bind_table_cell(
            cell=cell, cell_location="loc",
            whitelist=WhitelistRegistry(),
            tokenize_fn=tokenize,
            ground_truth_by_id=_make_g3_by_id(g3),
            fact_display_spec=_make_display_spec({"component.concrete_strength": 1}),
        )
        assert _has_issue_type(issues, "quantity_kind_mismatch")

    def test_chain_unit_string_mismatch(self):
        g3 = [GroundTruthFact(
            fact_id="fact:defect.C001.width",
            value=0.15, unit="mm", quantity_kind="length", precision=2,
        )]
        # token unit = "cm", G3 unit = "mm" — same quantity_kind "length", different string
        cell = TableCell(
            raw_text="0.15cm",  # unit "cm"
            anchor_declarations=[AnchorDeclaration(
                "0.15cm", "fact:defect.C001.width", 0, 6,
            )],
        )
        issues = bind_table_cell(
            cell=cell, cell_location="loc",
            whitelist=WhitelistRegistry(),
            tokenize_fn=tokenize,
            ground_truth_by_id=_make_g3_by_id(g3),
            fact_display_spec=_make_display_spec({"defect.width": 2}),
        )
        assert _has_issue_type(issues, "unit_mismatch")

    def test_chain_g3_not_found(self):
        g3 = []  # fact_id not in G3
        cell = TableCell(
            raw_text="32.4MPa",
            anchor_declarations=[AnchorDeclaration(
                "32.4MPa", "fact:component.K0099.concrete_strength", 0, 8,
            )],
        )
        issues = bind_table_cell(
            cell=cell, cell_location="loc",
            whitelist=WhitelistRegistry(),
            tokenize_fn=tokenize,
            ground_truth_by_id=_make_g3_by_id(g3),
        )
        assert _has_issue_type(issues, "invalid_fact_id")

    def test_chain_precision_from_snapshot_only(self):
        """INV-19 — P0-1 precision ONLY from snapshot.decimals, NOT from G3.precision."""
        g3 = [GroundTruthFact(
            fact_id="fact:component.K001.concrete_strength",
            value=32.449, unit="MPa", quantity_kind="pressure", precision=0,  # G3 precision irrelevant
        )]
        # snapshot says decimals=0 → 32.449 rounds to 32
        # G3 precision=0 but snapshot says decimals=1 → 32.449 rounds to 32.4
        # We set snapshot decimals=0 to force round to 32 vs G3.value=32.449
        cell = TableCell(
            raw_text="32.4MPa",  # numeric body = 32.4
            anchor_declarations=[AnchorDeclaration(
                "32.4MPa", "fact:component.K001.concrete_strength", 0, 8,
            )],
        )
        issues = bind_table_cell(
            cell=cell, cell_location="loc",
            whitelist=WhitelistRegistry(),
            tokenize_fn=tokenize,
            ground_truth_by_id=_make_g3_by_id(g3),
            fact_display_spec=_make_display_spec({"component.concrete_strength": 0}),  # snapshot decimals=0
        )
        # token 32.4 → frozen_round(32.4, 0) = 32.0
        # G3 32.449 → frozen_round(32.449, 0) = 32.0
        # Both equal (32.0 == 32.0) → PASS
        assert not _has_issue_type(issues, "value_mismatch")


# ══════════════════════════════════════════════════════════════════════
# fact_id parsing helpers
# ══════════════════════════════════════════════════════════════════════

class TestFactIdHelpers:
    def test_parse_fact_id(self):
        scope, instance, attr = parse_fact_id("fact:component.K001.concrete_strength")
        assert scope == "component"
        assert instance == "K001"
        assert attr == "concrete_strength"

    def test_derive_fact_type(self):
        ft = derive_fact_type("fact:component.K001.concrete_strength")
        assert ft == "component.concrete_strength"

    def test_full_parse(self):
        prefix, scope, instance, attr = _full_parse("fact:building.B01.area")
        assert prefix == "fact:"
        assert scope == "building"
        assert instance == "B01"
        assert attr == "area"


# ══════════════════════════════════════════════════════════════════════
# is_span_contained — frozen span rule
# ══════════════════════════════════════════════════════════════════════

class TestSpanContainment:
    def test_full_containment(self):
        assert is_span_contained(10, 20, 5, 25) is True
        assert is_span_contained(0, 10, 0, 10) is True  # exact equal

    def test_partial_overlap_not_contained(self):
        """Partial overlap (intersect but NOT contain) → NOT covered."""
        assert is_span_contained(10, 20, 15, 25) is False
        assert is_span_contained(15, 25, 10, 20) is False

    def test_no_intersection(self):
        assert is_span_contained(10, 15, 20, 30) is False
        assert is_span_contained(20, 30, 10, 15) is False

    def test_has_duplicate_fact_ids(self):
        from eval.accuracy.data_structures import AnchorDeclaration as AD
        # Same token, same fact_id → NOT duplicate
        assert has_duplicate_fact_ids([
            AD("t", "f1", 0, 4),
            AD("t", "f1", 0, 4),
        ]) is False
        # Same token, different fact_ids → duplicate
        assert has_duplicate_fact_ids([
            AD("t", "f1", 0, 4),
            AD("t", "f2", 0, 4),
        ]) is True
        # Empty → NOT duplicate
        assert has_duplicate_fact_ids([]) is False
