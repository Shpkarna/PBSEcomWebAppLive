"""MySQL connection and transaction helpers."""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator

from app.config import settings

try:
    import pymysql
    from pymysql.cursors import DictCursor
except ImportError:  # pragma: no cover - validated at runtime when mysql engine is selected.
    pymysql = None
    DictCursor = None


_transaction_connection: ContextVar[object | None] = ContextVar("mysql_transaction_connection", default=None)


def _require_driver() -> None:
    if pymysql is None or DictCursor is None:
        raise RuntimeError(
            "PyMySQL is not installed. Install backend requirements before using the MySQL engine."
        )


def _connect(*, autocommit: bool, database: str | None = None, use_config_database: bool = True):
    _require_driver()
    connection_kwargs = {
        "host": settings.mysql_host,
        "port": int(settings.mysql_port),
        "user": settings.mysql_user,
        "password": settings.mysql_password,
        "charset": settings.mysql_charset,
        "connect_timeout": int(settings.mysql_connect_timeout),
        "cursorclass": DictCursor,
        "autocommit": autocommit,
    }
    if database is not None:
        connection_kwargs["database"] = database
    elif use_config_database:
        connection_kwargs["database"] = settings.mysql_database
    return pymysql.connect(
        **connection_kwargs,
    )


def current_mysql_transaction_connection():
    """Return the active transaction connection, if one exists."""
    return _transaction_connection.get()


@contextmanager
def mysql_connection() -> Iterator[object]:
    """Yield the active transaction connection or a short-lived autocommit connection."""
    existing = current_mysql_transaction_connection()
    if existing is not None:
        yield existing
        return

    connection = _connect(autocommit=True)
    try:
        yield connection
    finally:
        connection.close()


@contextmanager
def mysql_server_connection(database: str | None = None) -> Iterator[object]:
    """Yield an autocommit connection, optionally without selecting a default database."""
    connection = _connect(autocommit=True, database=database, use_config_database=database is not None)
    try:
        yield connection
    finally:
        connection.close()


@contextmanager
def mysql_transaction() -> Iterator[None]:
    """Run a block inside a single MySQL transaction."""
    existing = current_mysql_transaction_connection()
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


def close_mysql_connections() -> None:
    """No-op shutdown hook for the current per-operation connection model."""
    active = current_mysql_transaction_connection()
    if active is not None:
        active.close()