"""SQL Server metadata and value-conversion helpers (Phase 7).

The TableSpec dataclass is the same contract as mysql_support.py so that
repository base-class logic (row→doc, projection, where-clause builder) can be
shared with minimal adaptation.  The only divergence is in DDL generation
(T-SQL syntax vs MySQL syntax).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
import json
from typing import Any
from uuid import uuid4

# Re-export TableSpec from mysql_support so existing imports keep working.
# The SQL Server repositories use the *same* table spec registry as MySQL —
# schema parity is a Phase 7 contract requirement.
from app.data.mysql_support import (
    TableSpec,
    MYSQL_TABLE_SPECS as _MYSQL_TABLE_SPECS,
    NULL_IF_EMPTY_COLUMNS,
    generate_id,
    normalize_datetime,
    normalize_json_value,
    dumps_json,
    loads_json,
    normalize_scalar_for_storage,
    normalize_document_value,
)

# SQL Server uses the exact same logical table structure; expose the registry
# under the SQL Server module name for clarity in bootstrap/test code.
MSSQL_TABLE_SPECS: dict[str, TableSpec] = _MYSQL_TABLE_SPECS


def mssql_connection_string_for_test(
    server: str,
    database: str | None = None,
    driver: str = "ODBC Driver 17 for SQL Server",
    user: str = "",
    password: str = "",
    timeout: int = 5,
) -> str:
    """Build a pyodbc connection string for test code that overrides settings."""
    parts = [
        f"DRIVER={{{driver}}}",
        f"SERVER={server}",
        f"Connect Timeout={timeout}",
    ]
    if database:
        parts.append(f"DATABASE={database}")
    if user:
        parts.append(f"UID={user}")
        parts.append(f"PWD={password}")
    else:
        parts.append("Trusted_Connection=yes")
    return ";".join(parts)
