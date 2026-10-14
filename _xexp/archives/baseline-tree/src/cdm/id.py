"""Three-segment Fact ID parsing, building and validation.

03_CANONICAL_DATA_MODEL.md v0.3.1 (v0.3 + D-027):
    fact:<scope_class>.<instance_key>.<attribute>

Grammar rules (frozen v0.3.1):
- Exactly 3 segments, prefix "fact:"
- No segment may contain '.'
- scope_class from SCOPE_CLASSES enum
- attribute must match the registered fact_type's attribute field
- fact_type first segment MUST equal ID's scope_class (invariant)

Examples:
    fact:component.K001.concrete_strength
    fact:defect.C001.width
    fact:building.B01.area
"""
from __future__ import annotations

from typing import Optional

from .registry import (
    SCOPE_CLASSES,
    is_valid_scope_class,
    FactTypeRegistry,
    get_default_registry,
)

FACT_ID_PREFIX = "fact:"


class FactID:
    """Parsed three-segment Fact ID.

    v0.3.1: renamed attribute_path → attribute (no longer a path,
    a single controlled attribute name from the registry).
    """

    __slots__ = ("scope_class", "instance_key", "attribute", "raw")

    def __init__(self, scope_class: str, instance_key: str,
                 attribute: str, raw: str):
        self.scope_class = scope_class
        self.instance_key = instance_key
        self.attribute = attribute
        self.raw = raw

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, FactID):
            return NotImplemented
        return self.raw == other.raw

    def __hash__(self) -> int:
        return hash(self.raw)

    def __repr__(self) -> str:
        return f"FactID({self.raw})"

    def __str__(self) -> str:
        return self.raw


def parse_fact_id(raw: str) -> Optional[FactID]:
    """Parse a raw Fact ID string. Returns None if malformed.

    v0.3.1 strict parsing:
        strip prefix "fact:" → split on '.' → MUST have exactly 3 parts.
        ANY segment containing '.' would produce >3 parts → rejected.
        All 3 segments must be non-empty.
    """
    if not isinstance(raw, str) or not raw.startswith(FACT_ID_PREFIX):
        return None

    body = raw[len(FACT_ID_PREFIX):]
    if not body:
        return None

    # v0.3.1: strict split — exactly 3 parts, no more, no less.
    # Previously used split(".", 2) which allowed dots in the third part.
    parts = body.split(".")
    if len(parts) != 3:
        return None

    scope_class, instance_key, attribute = parts

    if not scope_class or not instance_key or not attribute:
        return None

    return FactID(
        scope_class=scope_class,
        instance_key=instance_key,
        attribute=attribute,
        raw=raw,
    )


def build_fact_id(scope_class: str, instance_key: str,
                  attribute: str) -> str:
    """Construct a Fact ID string from three segments.

    v0.3.1: renamed attribute_path → attribute. No version suffix support.
    """
    return f"{FACT_ID_PREFIX}{scope_class}.{instance_key}.{attribute}"


def is_valid_fact_id(
    raw: str,
    registry: Optional[FactTypeRegistry] = None,
    fact_type: Optional[str] = None,
) -> Optional[str]:
    """Full validation of a Fact ID.

    Returns None if valid, or an error message string if invalid.

    Checks performed (v0.3.1):
    1. Format: must start with "fact:" and have EXACTLY 3 segments.
       No segment may contain '.' (attribute is a single controlled name).
    2. scope_class: must be in SCOPE_CLASSES.
    3. If registry + fact_type provided:
       a. fact_type first segment MUST equal parsed scope_class (invariant).
       b. attribute must match registered fact_type's attribute field.

    v0.3.1 changes from v0.3:
    - No longer accepts '.vN' version suffix (revision is now a
      separate Fact field, not part of the ID).
    - Explicitly validates fact_type prefix invariant.
    """
    fid = parse_fact_id(raw)
    if fid is None:
        return (
            f"invalid Fact ID format: '{raw}'. "
            f"Expected 'fact:<scope_class>.<instance_key>.<attribute>' "
            f"(exactly 3 segments, no dots inside any segment)"
        )

    if not is_valid_scope_class(fid.scope_class):
        return (
            f"invalid scope_class '{fid.scope_class}' in Fact ID '{raw}': "
            f"must be one of {sorted(SCOPE_CLASSES)}"
        )

    # Validate instance_key — non-empty, no leading/trailing whitespace
    if fid.instance_key != fid.instance_key.strip():
        return f"instance_key in Fact ID '{raw}' has whitespace"

    # Validate attribute — must not be empty or purely whitespace
    if not fid.attribute.strip():
        return f"attribute in Fact ID '{raw}' is empty"

    # v0.3.1 invariant: fact_type first segment MUST equal scope_class.
    if fact_type is not None:
        reg = registry or get_default_registry()

        # a) fact_type prefix invariant
        ft_parts = fact_type.split(".")
        if len(ft_parts) != 2 or ft_parts[0] != fid.scope_class:
            return (
                f"fact_type '{fact_type}' prefix mismatch: "
                f"fact_type first segment must be '{fid.scope_class}' "
                f"(scope_class from ID '{raw}'), "
                f"but got '{ft_parts[0] if ft_parts else 'empty'}'"
            )

        # b) attribute must match registered fact_type
        err = reg.validate_id_against_fact_type(fid.attribute, fact_type)
        if err is not None:
            return err

    return None
