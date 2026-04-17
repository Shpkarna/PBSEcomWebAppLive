"""Utilities for generating formatted, auto-incrementing business IDs."""
from datetime import datetime
from pymongo import ReturnDocument
from app.database import get_collection


def next_formatted_id(prefix: str, *, year: int | None = None, seed: int = 1_000_000) -> str:
    """Generate IDs like PREFIX-YYYY-N using an atomic MongoDB counter.

    Example: SO-2026-1000001
    """
    current_year = year or datetime.utcnow().year
    counter_key = f"{prefix}-{current_year}"
    counters = get_collection("counters")

    doc = counters.find_one_and_update(
        {"_id": counter_key},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )

    # Keep the persisted counter compact and add the business seed in the rendered ID.
    rendered_seq = seed + int(doc["seq"])
    return f"{prefix}-{current_year}-{rendered_seq}"


def next_sales_order_id() -> str:
    """Generate the next sales order identifier."""
    return next_formatted_id("SO")


def next_customer_id() -> str:
    """Generate the next customer identifier."""
    return next_formatted_id("C")
