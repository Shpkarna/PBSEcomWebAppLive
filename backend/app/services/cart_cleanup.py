"""Background task that purges orphaned cart items and checkout locks.

A cart (identified by its cart_quote_id) is considered orphaned when its
owning user session has expired — either because the session's ``expires_at``
is in the past **or** because the session's ``last_activity`` exceeds the
configured inactivity timeout.

The task runs on a fixed interval (default 60 s) and:
1.  Finds all distinct session_ids referenced by cart items.
2.  Identifies which of those sessions are dead (missing or expired).
3.  For each dead session, collects the associated cart_quote_ids,
    removes the checkout locks and cart items, and writes an audit log.
"""

import asyncio
from datetime import datetime, timedelta

from app.config import settings
from app.data.repository_providers import get_order_cart_repository, get_utility_repository
from app.utils.logger import log_event

CLEANUP_INTERVAL_SECONDS = 60  # how often the sweep runs


def _is_session_expired(session: dict | None, now: datetime) -> bool:
    """Return True when the session is missing, hard-expired, or idle-expired."""
    if session is None:
        return True
    if session.get("expires_at") and session["expires_at"] < now:
        return True
    inactivity_limit = timedelta(minutes=settings.session_inactivity_minutes)
    last_activity = session.get("last_activity", session.get("created_at", now))
    if now - last_activity > inactivity_limit:
        return True
    return False


def run_cart_cleanup() -> dict:
    """Single synchronous sweep — returns a summary dict for testing / manual calls."""
    cart_repo = get_order_cart_repository()
    utility_repo = get_utility_repository()
    now = datetime.utcnow()

    # 1. Distinct session_ids currently in the cart collection
    session_ids_in_cart = cart_repo.distinct_cart_session_ids()
    if not session_ids_in_cart:
        return {"expired_sessions": 0, "cart_items_removed": 0, "locks_removed": 0}

    # 2. Determine which sessions are dead
    dead_session_ids = []
    for sid in session_ids_in_cart:
        session = utility_repo.find_session_by_id(sid)
        if _is_session_expired(session, now):
            dead_session_ids.append(sid)

    if not dead_session_ids:
        return {"expired_sessions": 0, "cart_items_removed": 0, "locks_removed": 0}

    # 3. Collect affected cart_quote_ids and purge
    total_cart_items_removed = 0
    total_locks_removed = 0

    for sid in dead_session_ids:
        # All cart items belonging to this dead session
        orphaned_items = cart_repo.list_cart_items_by_session(sid)
        if not orphaned_items:
            continue

        # Unique cart_quote_ids in this session's cart
        quote_ids = list({
            item["cart_quote_id"]
            for item in orphaned_items
            if item.get("cart_quote_id")
        })

        # Determine the username from the first cart item for the log
        user_id = orphaned_items[0].get("user_id", "unknown")

        # Remove checkout locks for these quote ids
        locks_removed_count = 0
        if quote_ids:
            locks_removed_count = cart_repo.delete_checkout_locks_by_quote_ids(quote_ids)
            total_locks_removed += locks_removed_count

        # Remove the cart items
        items_removed_count = cart_repo.delete_cart_items_by_session(sid)
        total_cart_items_removed += items_removed_count

        # Audit log per expired session
        log_event(
            action="cart_cleanup_expired_session",
            user="system",
            details={
                "session_id": sid,
                "user_id": user_id,
                "cart_quote_ids": quote_ids,
                "cart_items_removed": items_removed_count,
                "locks_removed": locks_removed_count,
                "cleaned_at": now.isoformat(),
            },
            path="/background/cart_cleanup",
        )

    summary = {
        "expired_sessions": len(dead_session_ids),
        "cart_items_removed": total_cart_items_removed,
        "locks_removed": total_locks_removed,
    }

    # Write a single summary log when anything was cleaned
    log_event(
        action="cart_cleanup_sweep_completed",
        user="system",
        details=summary,
        path="/background/cart_cleanup",
    )

    return summary


async def _cart_cleanup_loop() -> None:
    """Async loop that calls the synchronous cleanup on a fixed interval."""
    while True:
        try:
            run_cart_cleanup()
        except Exception as exc:
            # Log but never crash the background loop
            try:
                log_event(
                    action="cart_cleanup_error",
                    user="system",
                    details={"error": str(exc)},
                    path="/background/cart_cleanup",
                )
            except Exception:
                pass
        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)


def start_cart_cleanup_task() -> asyncio.Task:
    """Schedule the periodic cleanup loop — call once from the app startup event."""
    return asyncio.create_task(_cart_cleanup_loop())
