"""SQL Server connection and transaction helpers (Phase 7).

Uses pyodbc with the ODBC Driver 17 for SQL Server.
Supports both Windows Integrated Security (Trusted_Connection=yes, the default
when mssql_user is empty) and SQL Server Authentication when mssql_user and
mssql_password are set.

Connection pattern mirrors mysql_client.py:
- Each operation gets a short-lived autocommit connection unless called within
  a ``mssql_transaction()`` block, which pins the connection to a thread-local
  ContextVar for correct nested call behaviour.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator

from app.config import settings

try:
    import pyodbc
except ImportError:  # pragma: no cover
    pyodbc = None


_transaction_connection: ContextVar[object | None] = ContextVar(
    "mssql_transaction_connection", default=None
)


def _require_driver() -> None:
    if pyodbc is None:
        raise RuntimeError(
            "pyodbc is not installed. Run 'pip install pyodbc' before using the SQL Server engine."
        )


def _connection_string(database: str | None = None, use_config_database: bool = True) -> str:
    _require_driver()
    parts = [
        f"DRIVER={{{settings.mssql_driver}}}",
        f"SERVER={settings.mssql_server}",
        f"Connect Timeout={settings.mssql_connect_timeout}",
    ]
    db = database if database is not None else (settings.mssql_database if use_config_database else None)
    if db:
        parts.append(f"DATABASE={db}")
    if settings.mssql_user:
        parts.append(f"UID={settings.mssql_user}")
        parts.append(f"PWD={settings.mssql_password}")
    else:
        parts.append("Trusted_Connection=yes")
    return ";".join(parts)


def _connect(*, autocommit: bool, database: str | None = None, use_config_database: bool = True):
    conn = pyodbc.connect(_connection_string(database=database, use_config_database=use_config_database))
    conn.autocommit = autocommit
    return conn


def current_mssql_transaction_connection():
    """Return the active transaction connection if inside a mssql_transaction() block."""
    return _transaction_connection.get()


@contextmanager
def mssql_connection() -> Iterator[object]:
    """Yield the active transaction connection or a short-lived autocommit connection."""
    existing = current_mssql_transaction_connection()
    if existing is not None:
        yield existing
        return

    connection = _connect(autocommit=True)
    try:
        yield connection
    finally:
        connection.close()


@contextmanager
def mssql_server_connection(database: str | None = None) -> Iterator[object]:
    """Yield an autocommit connection, optionally selecting a specific database.

    Pass ``database=None`` with ``use_config_database=False`` to connect without
    an initial database (needed for CREATE DATABASE statements).
    """
    conn = _connect(autocommit=True, database=database, use_config_database=database is not None)
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def mssql_transaction() -> Iterator[None]:
    """Run a block inside a single SQL Server transaction.

    Nested calls reuse the outer connection transparently.
    """
    existing = current_mssql_transaction_connection()
    if existing is not None:
        yield
        return

    connection = _connect(autocommit=False)
    token = _transaction_connection.set(connection)
    try:
        yield
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        _transaction_connection.reset(token)
        connection.close()


def close_mssql_connections() -> None:
    """Shutdown hook — close any lingering transaction connection."""
    active = current_mssql_transaction_connection()
    if active is not None:
        try:
            active.close()
        except Exception:
            pass
