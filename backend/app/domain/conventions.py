"""Canonical conventions for the domain model layer.

Phase 1 — Step 4 Artifact
These rules are invariant across all phase transitions and all database drivers.
Any new entity, adapter, or service introduced in Phases 4–9 MUST comply.
"""
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP


# ── ID convention ─────────────────────────────────────────────────────────────
# All entity IDs are `str` at the domain layer.
#
#   MongoDB:    str(ObjectId)  — adapter converts ObjectId ↔ str on each boundary.
#   MySQL:      str(int PK)    — adapter converts int ↔ str on each boundary.
#   SQL Server: str(int PK) or GUID string — adapter responsibility.
#
# Rationale: API consumers and domain logic must never depend on storage ID types.
ID_CONVENTION = "str"


# ── Datetime convention ───────────────────────────────────────────────────────
# All datetimes are UTC and timezone-naive within the domain and storage layers.
# Convert to timezone-aware (UTC) only at the API response surface when required.
#
#   Use `conventions.utcnow()` as the single authoritative source for timestamps,
#   rather than calling `datetime.utcnow()` directly, to make future changes easy.
DATETIME_CONVENTION = "UTC_naive"


def utcnow() -> datetime:
    """Canonical source for all created_at / updated_at timestamps in the domain."""
    return datetime.utcnow()


# ── Numeric precision rules ───────────────────────────────────────────────────
# Monetary values (prices, totals, discounts, taxes):
#   - Rounded to exactly 2 decimal places (ROUND_HALF_UP) before storage.
#   - Stored as float in MongoDB (Phase 3).
#   - Stored as DECIMAL(10, 2) column type in MySQL / SQL Server (Phase 6 / 7).
#
# GST rates:
#   - Stored as decimal fraction: 0.18 = 18%, 0.05 = 5%.
#   - Never stored as percentage (18.0) in the domain layer.
#
# Quantities (stock, cart, order lines):
#   - Always integer; no fractional quantities.
MONEY_DECIMAL_PLACES = 2
GST_RATE_FORMAT = "decimal_fraction"  # e.g., 0.18 means 18%


def round_money(value: float) -> float:
    """Round a monetary value to the canonical 2 decimal places (ROUND_HALF_UP).

    Use before any storage write for prices, totals, discounts, tax amounts.

    Examples:
        round_money(10.005) → 10.01
        round_money(10.004) → 10.00
        round_money(1234.5678) → 1234.57
    """
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def round_gst_rate(rate: float) -> float:
    """Round a GST rate to 4 decimal places (adequate for 0.0001 = 0.01% precision).

    Example: 0.18 (18%), 0.05 (5%), 0.125 (12.5%).
    """
    return float(Decimal(str(rate)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))


# ── String field conventions ──────────────────────────────────────────────────
# Empty string ("") is preferred over None for optional text fields when the
# storage layer does not support nullable strings efficiently (e.g., Mongo).
# Domain entities explicitly default optional text fields to "" or None as
# declared in entities.py; adapters must not change these defaults.
STRING_NONE_POLICY = "explicit_per_entity"


# ── Summary ───────────────────────────────────────────────────────────────────
CONVENTIONS_SUMMARY = {
    "id_type": ID_CONVENTION,
    "datetime_timezone": DATETIME_CONVENTION,
    "money_decimal_places": MONEY_DECIMAL_PLACES,
    "gst_rate_format": GST_RATE_FORMAT,
    "string_none_policy": STRING_NONE_POLICY,
}
