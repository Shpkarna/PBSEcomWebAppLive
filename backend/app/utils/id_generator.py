"""Utilities for generating formatted, auto-incrementing business IDs.

Phase 4: Delegates to ``UtilityRepository.next_counter_id()`` via the
driver registry instead of using ``pymongo.ReturnDocument`` directly.
"""
from datetime import datetime
from app.data.repository_providers import get_utility_repository


def next_formatted_id(prefix: str, *, year: int | None = None, seed: int = 1_000_000) -> str:
    """Generate IDs like PREFIX-YYYY-N using an atomic counter.

    Example: SO-2026-1000001
    """
    current_year = year or datetime.utcnow().year
    counter_key = f"{prefix}-{current_year}"
    seq = get_utility_repository().next_counter_id(counter_key)
    rendered_seq = seed + seq
    return f"{prefix}-{current_year}-{rendered_seq}"


def next_sales_order_id() -> str:
    """Generate the next sales order identifier."""
    return next_formatted_id("SO")


def next_customer_id() -> str:
    """Generate the next customer identifier."""
    return next_formatted_id("C")
