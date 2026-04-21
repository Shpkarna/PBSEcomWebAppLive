#!/usr/bin/env python3
"""Cross-engine CI matrix runner — Phase 9 criterion 9.1.

Runs the unit-level (offline, no live DB required) test stages for each
supported database engine mode and prints a pass/fail matrix.

Live-DB stages (MySQL commerce flows, MSSQL commerce flows, etc.) are
attempted only when the corresponding service is reachable; otherwise they
are marked as SKIPPED rather than FAILED, so the matrix remains informative
even in environments where only one engine is available.

Usage
-----
    python backend/ci_matrix.py

Exit codes
----------
0 — all attempted stages passed (skipped stages do not affect exit code)
1 — one or more stages failed
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
from typing import Dict, List, NamedTuple, Optional

# ---------------------------------------------------------------------------
# Root paths
# ---------------------------------------------------------------------------

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_SCRIPT_DIR)
_TEST_SUIT = os.path.join(_REPO_ROOT, "test_suit")
_BACKEND_TESTS = os.path.join(_TEST_SUIT, "backend")

# ---------------------------------------------------------------------------
# Colour helpers (ANSI — fall back silently on non-TTY)
# ---------------------------------------------------------------------------

_USE_COLOUR = sys.stdout.isatty()


def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _USE_COLOUR else text


GREEN = lambda t: _c("92", t)   # noqa: E731
RED = lambda t: _c("91", t)     # noqa: E731
YELLOW = lambda t: _c("93", t)  # noqa: E731
CYAN = lambda t: _c("96", t)    # noqa: E731
BOLD = lambda t: _c("1", t)     # noqa: E731


# ---------------------------------------------------------------------------
# Stage definitions
# ---------------------------------------------------------------------------

class Stage(NamedTuple):
    label: str
    engine: str          # "mongodb" | "mysql" | "sqlserver" | "any"
    script: str          # relative to _BACKEND_TESTS
    live_db: bool        # True → skip if DB service unreachable
    check_host: Optional[str] = None
    check_port: Optional[int] = None


# Stages ordered: offline unit tests first, then live-DB tests.
STAGES: List[Stage] = [
    # ---- engine-agnostic (domain / registry / observability) ----------------
    Stage("Domain Phase 1 (unit)",           "any",       "test_domain_phase1.py",           False),
    Stage("Driver Registry (unit)",           "any",       "test_driver_registry.py",          False),
    Stage("Phase 5 Setup (unit)",             "any",       "test_phase5_setup_db_engine.py",   False),
    Stage("Observability Phase 9 (unit)",     "any",       "test_observability_phase9.py",     False),
    # ---- MongoDB (no live-DB test: Mongo runs inside the app process) -------
    Stage("Mongo Analytics (unit)",           "mongodb",   "test_analytics_phase8.py",         False),
    # ---- MySQL offline + live -----------------------------------------------
    Stage("MySQL Bootstrap (unit)",           "mysql",     "test_mysql_bootstrap.py",          False),
    Stage("MySQL Order/Cart Repo (unit)",     "mysql",     "test_mysql_order_cart_repository.py", False),
    Stage("MySQL Commerce Flows (live DB)",   "mysql",     "test_mysql_commerce_flows.py",     True,  "localhost", 3306),
    Stage("MySQL Parity (live DB)",           "mysql",     "test_mysql_parity.py",             True,  "localhost", 3306),
    # ---- SQL Server offline + live ------------------------------------------
    Stage("MSSQL Bootstrap (unit)",           "sqlserver", "test_mssql_bootstrap.py",          False),
    Stage("MSSQL Commerce Flows (live DB)",   "sqlserver", "test_mssql_commerce_flows.py",     True,  "localhost", 1433),
    Stage("MSSQL Parity (live DB)",           "sqlserver", "test_mssql_parity.py",             True,  "localhost", 1433),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_reachable(host: str, port: int, timeout: float = 2.0) -> bool:
    """Return True if *host*:*port* accepts a TCP connection."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except OSError:
        return False


def _run_stage(script_path: str, timeout: int = 120) -> bool:
    """Run a test script and return True on exit-code 0."""
    result = subprocess.run(
        [sys.executable, script_path],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
        errors="replace",
    )
    return result.returncode == 0


# ---------------------------------------------------------------------------
# Matrix execution
# ---------------------------------------------------------------------------

_STATUS_PASS = "PASS   "
_STATUS_FAIL = "FAIL   "
_STATUS_SKIP = "SKIP   "


def run_matrix() -> int:
    """Execute the CI matrix and return process exit code."""
    print()
    print(BOLD("=" * 70))
    print(BOLD("  Cross-Engine CI Matrix — Phase 9 criterion 9.1"))
    print(BOLD("=" * 70))
    print()

    # Group stages by engine for display
    engine_order = ["any", "mongodb", "mysql", "sqlserver"]
    engine_label = {
        "any":       "Engine-Agnostic",
        "mongodb":   "MongoDB",
        "mysql":     "MySQL",
        "sqlserver": "SQL Server",
    }

    # Collect results: label → ("PASS"|"FAIL"|"SKIP")
    matrix: Dict[str, str] = {}
    any_failed = False

    for engine in engine_order:
        stages = [s for s in STAGES if s.engine == engine]
        if not stages:
            continue

        print(BOLD(f"  [{engine_label[engine]}]"))
        print()

        for stage in stages:
            script_path = os.path.join(_BACKEND_TESTS, stage.script)

            # Check if the script even exists
            if not os.path.isfile(script_path):
                status = _STATUS_SKIP
                detail = "(script not found)"
                matrix[stage.label] = "SKIP"
                print(f"    {YELLOW(status)} {stage.label:<50} {detail}")
                continue

            # Skip live-DB stages when service unreachable
            if stage.live_db and stage.check_host and stage.check_port:
                if not _is_reachable(stage.check_host, stage.check_port):
                    status = _STATUS_SKIP
                    detail = f"({stage.check_host}:{stage.check_port} unreachable)"
                    matrix[stage.label] = "SKIP"
                    print(f"    {YELLOW(status)} {stage.label:<50} {detail}")
                    continue

            # Run the stage
            try:
                passed = _run_stage(script_path)
            except subprocess.TimeoutExpired:
                passed = False

            if passed:
                status = _STATUS_PASS
                detail = ""
                matrix[stage.label] = "PASS"
                print(f"    {GREEN(status)} {stage.label:<50} {detail}")
            else:
                status = _STATUS_FAIL
                detail = ""
                matrix[stage.label] = "FAIL"
                any_failed = True
                print(f"    {RED(status)} {stage.label:<50} {detail}")

        print()

    # ------------------------------------------------------------------
    # Summary table
    # ------------------------------------------------------------------
    print(BOLD("=" * 70))
    print(BOLD("  Matrix Summary"))
    print(BOLD("=" * 70))
    print()

    col_w = 52
    print(f"  {'Stage':<{col_w}} {'Result'}")
    print(f"  {'-' * col_w} {'------'}")
    for label, result in matrix.items():
        if result == "PASS":
            coloured = GREEN(result)
        elif result == "FAIL":
            coloured = RED(result)
        else:
            coloured = YELLOW(result)
        print(f"  {label:<{col_w}} {coloured}")

    totals = {"PASS": 0, "FAIL": 0, "SKIP": 0}
    for r in matrix.values():
        totals[r] += 1

    print()
    print(
        f"  Totals: {GREEN(str(totals['PASS']) + ' PASS')}  "
        f"{RED(str(totals['FAIL']) + ' FAIL')}  "
        f"{YELLOW(str(totals['SKIP']) + ' SKIP')}"
    )
    print()

    if any_failed:
        print(RED("  MATRIX RESULT: FAIL — one or more stages did not pass.\n"))
        return 1
    print(GREEN("  MATRIX RESULT: PASS — all attempted stages passed.\n"))
    return 0


if __name__ == "__main__":
    sys.exit(run_matrix())
