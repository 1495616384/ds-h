"""Step 7-E Accuracy Validator — Tokenizer (§5).

冻结正则 + overlap 消解 + unit-start/cont 文法 (B1).
Validator tokenizes RenderedSegment.raw_text AND TableCell.raw_text with
EXACTLY the same functions — Fix 3 invariant.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple


# ── §5.1 冻结的正则表达式 ──────────────────────────────────────────

# 数值 token：捕获可选 ± 前缀、可选 ± 号、数字主体、可选科学计数法、可选单位后缀
# 单位组 (B1 修复)：完整 token 边界 —— unit candidate = [A-Za-zμ%][A-Za-z0-9μ²³%/]*
# (unit-start 起始 + unit-cont 延续的极大连续 run)
NUMERIC_TOKEN_RE = re.compile(
    r'(?<![0-9A-Za-z])'               # lookbehind: NOT preceded by digit or letter
    r'(±\s*)?'                         # optional ± prefix (full token)
    r'([+-])?'                          # optional ± sign
    r'(\d+(?:\.\d+)?)'                 # number body (required)
    r'\s*'
    r'(×10[⁰¹²³⁴⁵⁶⁷⁸⁹]+|×10\^-?\d+|[eE][+-]?\d+)?'   # optional scientific
    r'\s*'
    r'([A-Za-zμ%][A-Za-z0-9μ²³%/]*)?'  # optional unit suffix (B1: full unit candidate)
)

# 标识 token：构件/测点/样品编号 —— ST 首置；K/C/M/P/S/B/D 前缀
IDENTIFIER_TOKEN_RE = re.compile(
    r'(?<![A-Za-z0-9])'               # lookbehind: NOT preceded by alphanumeric
    r'((?:构件|测点|样品|检测点|裂缝|强度|检验点)?\s*)'   # optional chinese prefix
    r'(ST|[KCMPSBD])'                 # controlled letter prefix
    r'(-?\d{1,5})'                    # digits, optional leading dash
    r'(-\d{1,3})?'                    # optional segment suffix
    r'(?![A-Za-z0-9])'                # lookahead: NOT followed by alphanumeric
)


class TokenKind(str, Enum):
    NUMERIC = "numeric"
    IDENTIFIER = "identifier"


@dataclass
class Token:
    """A token extracted from text, with char span relative to carrier raw_text."""
    kind: TokenKind
    text: str                       # full matched text including unit suffix (if numeric)
    char_start: int                 # inclusive
    char_end: int                   # exclusive

    # Parsed sub-components (numeric only)
    numeric_value: Optional[float] = None   # parsed number body
    unit: Optional[str] = None               # full unit candidate string
    # Parsed sub-components (identifier only)
    normalized_identifier: Optional[str] = None  # e.g. "K001", "ST001"


# ── §5.2 Overlap 消解 ──────────────────────────────────────────────

def _extract_numeric_tokens(text: str) -> List[Token]:
    """Run NUMERIC_TOKEN_RE over text, parse each match."""
    results: List[Token] = []
    for m in NUMERIC_TOKEN_RE.finditer(text):
        full = m.group(0)
        sign = m.group(2) or "+"
        number_body = m.group(3)
        scientific = m.group(4)
        unit_suffix = m.group(5)

        # parse numeric value
        try:
            val = float(number_body)
        except ValueError:
            continue  # should never happen — regex guarantees \d+

        # ± sign handling (§8.1 BIND-2: we capture it but parent must reject)
        if sign == "-":
            val = -val

        # scientific notation — handle ×10ⁿ variants
        if scientific:
            sci = scientific
            if sci.startswith("×10"):
                # extract exponent
                exp_str = sci.replace("×10", "").replace("^", "")
                # handle unicode superscript digits
                sup_map = {
                    "⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4",
                    "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9",
                }
                for sup, digit in sup_map.items():
                    exp_str = exp_str.replace(sup, digit)
                try:
                    exponent = int(exp_str)
                    val *= (10 ** exponent)
                except ValueError:
                    pass
            elif sci.lower().startswith("e"):
                try:
                    val *= (10 ** int(sci[1:]))
                except ValueError:
                    pass

        tok = Token(
            kind=TokenKind.NUMERIC,
            text=full,
            char_start=m.start(),
            char_end=m.end(),
            numeric_value=val,
            unit=unit_suffix,
        )
        results.append(tok)
    return results


def _extract_identifier_tokens(text: str) -> List[Token]:
    """Run IDENTIFIER_TOKEN_RE over text, parse each match."""
    results: List[Token] = []
    for m in IDENTIFIER_TOKEN_RE.finditer(text):
        full = m.group(0)
        letter_prefix = m.group(2)       # ST or single char from [KCMPSBD]
        digits = m.group(3)               # -?\d{1,5}
        seg = m.group(4)                  # optional -\d{1,3}

        normalized = f"{letter_prefix}{digits}"
        if seg:
            normalized += seg

        tok = Token(
            kind=TokenKind.IDENTIFIER,
            text=full,
            char_start=m.start(),
            char_end=m.end(),
            normalized_identifier=normalized,
        )
        results.append(tok)
    return results


def _sort_key(tok: Token) -> Tuple[int, int, int]:
    """§5.2 — overlap resolution sort key.

    (char_start, -span_length, 0 if identifier else 1)
    → identifier before numeric when same char_start
    → longer span before shorter within same kind
    → earlier start before later
    """
    span_len = tok.char_end - tok.char_start
    kind_priority = 0 if tok.kind == TokenKind.IDENTIFIER else 1
    return (tok.char_start, -span_len, kind_priority)


def tokenize(text: str) -> List[Token]:
    """§5 — extract all tokens from text, with overlap resolution.

    Returns deduplicated sorted list.
    """
    if not text:
        return []

    numeric = _extract_numeric_tokens(text)
    identifiers = _extract_identifier_tokens(text)

    all_tokens = numeric + identifiers
    all_tokens.sort(key=_sort_key)

    # Resolve overlaps: greedily keep first (highest priority per sort key)
    result: List[Token] = []
    last_end = -1
    for tok in all_tokens:
        # Skip if this token overlaps an already-kept token
        if tok.char_start < last_end:
            continue
        result.append(tok)
        last_end = tok.char_end

    return result
