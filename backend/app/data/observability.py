"""Observability module — Phase 9 criterion 9.3.

Provides a process-level, thread-safe metrics store that tracks:
- Per-repository query latency (rolling window, last 1 000 samples per key)
- Per-repository query failure counts
- Per-engine transaction failure counts

Usage (inside adapters or client helpers)::

    from app.data.observability import metrics

    t0 = time.perf_counter()
    try:
        result = _execute_query(...)
        metrics.record_query(engine="mongodb", repo="product", operation="find_by_id",
                             duration_ms=(time.perf_counter() - t0) * 1000, success=True)
    except Exception:
        metrics.record_query(engine="mongodb", repo="product", operation="find_by_id",
                             duration_ms=(time.perf_counter() - t0) * 1000, success=False)
        raise

    # For transactions:
    metrics.record_transaction(engine="mysql", success=False, duration_ms=12.4)

    # Expose via /api/metrics endpoint:
    summary = metrics.get_summary()
"""

from __future__ import annotations

import threading
from collections import defaultdict, deque
from typing import Any, Dict, List


_LATENCY_WINDOW = 1_000  # rolling samples kept per (engine, repo, operation) key


class RepositoryMetrics:
    """Thread-safe, in-process metrics store.

    All public methods are safe to call from multiple threads concurrently.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # latency samples: key → deque of float (ms)
        self._query_latencies: Dict[str, deque] = defaultdict(lambda: deque(maxlen=_LATENCY_WINDOW))
        # failure counts per (engine, repo, operation) key
        self._query_failures: Dict[str, int] = defaultdict(int)
        # total query counts per key (success + failure)
        self._query_totals: Dict[str, int] = defaultdict(int)
        # transaction latency samples: engine → deque of float (ms)
        self._txn_latencies: Dict[str, deque] = defaultdict(lambda: deque(maxlen=_LATENCY_WINDOW))
        # transaction failure counts per engine
        self._txn_failures: Dict[str, int] = defaultdict(int)
        # transaction totals per engine
        self._txn_totals: Dict[str, int] = defaultdict(int)

    # ------------------------------------------------------------------
    # Recording helpers
    # ------------------------------------------------------------------

    def record_query(
        self,
        engine: str,
        repo: str,
        operation: str,
        duration_ms: float,
        success: bool,
    ) -> None:
        """Record a single repository operation.

        Parameters
        ----------
        engine:
            Database engine identifier (``"mongodb"``, ``"mysql"``, ``"sqlserver"``).
        repo:
            Short repository name, e.g. ``"product"``, ``"auth"``, ``"order_cart"``.
        operation:
            Method/operation name, e.g. ``"find_by_id"``, ``"insert_product"``.
        duration_ms:
            Wall-clock elapsed time in milliseconds.
        success:
            ``True`` if the operation completed without raising.
        """
        key = f"{engine}.{repo}.{operation}"
        with self._lock:
            self._query_latencies[key].append(duration_ms)
            self._query_totals[key] += 1
            if not success:
                self._query_failures[key] += 1

    def record_transaction(
        self,
        engine: str,
        success: bool,
        duration_ms: float,
    ) -> None:
        """Record a database transaction outcome.

        Parameters
        ----------
        engine:
            Database engine identifier.
        success:
            ``True`` if the transaction committed successfully.
        duration_ms:
            Wall-clock elapsed time in milliseconds for the whole transaction.
        """
        with self._lock:
            self._txn_latencies[engine].append(duration_ms)
            self._txn_totals[engine] += 1
            if not success:
                self._txn_failures[engine] += 1

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def get_summary(self) -> Dict[str, Any]:
        """Return a serialisable summary of all recorded metrics.

        Structure::

            {
                "queries": {
                    "<engine>.<repo>.<operation>": {
                        "total": int,
                        "failures": int,
                        "error_rate": float,        # 0.0–1.0
                        "latency_ms": {
                            "p50": float,
                            "p95": float,
                            "p99": float,
                            "min": float,
                            "max": float,
                            "samples": int
                        }
                    },
                    ...
                },
                "transactions": {
                    "<engine>": {
                        "total": int,
                        "failures": int,
                        "error_rate": float,
                        "latency_ms": {
                            "p50": float,
                            "p95": float,
                            "p99": float,
                            "min": float,
                            "max": float,
                            "samples": int
                        }
                    },
                    ...
                }
            }
        """
        with self._lock:
            query_keys = list(self._query_latencies.keys()) + [
                k for k in self._query_totals if k not in self._query_latencies
            ]
            txn_keys = list(self._txn_latencies.keys()) + [
                k for k in self._txn_totals if k not in self._txn_latencies
            ]

            queries: Dict[str, Any] = {}
            for key in set(query_keys):
                total = self._query_totals[key]
                failures = self._query_failures[key]
                samples = list(self._query_latencies[key])
                queries[key] = {
                    "total": total,
                    "failures": failures,
                    "error_rate": round(failures / total, 4) if total else 0.0,
                    "latency_ms": _percentiles(samples),
                }

            transactions: Dict[str, Any] = {}
            for engine in set(txn_keys):
                total = self._txn_totals[engine]
                failures = self._txn_failures[engine]
                samples = list(self._txn_latencies[engine])
                transactions[engine] = {
                    "total": total,
                    "failures": failures,
                    "error_rate": round(failures / total, 4) if total else 0.0,
                    "latency_ms": _percentiles(samples),
                }

        return {"queries": queries, "transactions": transactions}

    def reset(self) -> None:
        """Clear all metrics.  Intended for use in test teardown only."""
        with self._lock:
            self._query_latencies.clear()
            self._query_failures.clear()
            self._query_totals.clear()
            self._txn_latencies.clear()
            self._txn_failures.clear()
            self._txn_totals.clear()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _percentiles(samples: List[float]) -> Dict[str, Any]:
    """Compute latency percentiles from a list of millisecond measurements."""
    if not samples:
        return {"p50": None, "p95": None, "p99": None, "min": None, "max": None, "samples": 0}

    sorted_s = sorted(samples)
    n = len(sorted_s)

    def _pct(p: float) -> float:
        idx = max(0, min(int(p * n / 100 + 0.5) - 1, n - 1))
        return round(sorted_s[idx], 3)

    return {
        "p50": _pct(50),
        "p95": _pct(95),
        "p99": _pct(99),
        "min": round(sorted_s[0], 3),
        "max": round(sorted_s[-1], 3),
        "samples": n,
    }


# ---------------------------------------------------------------------------
# Module-level singleton — import and use directly
# ---------------------------------------------------------------------------

#: Process-level singleton.  Import and call ``metrics.record_query(...)`` directly.
metrics: RepositoryMetrics = RepositoryMetrics()
