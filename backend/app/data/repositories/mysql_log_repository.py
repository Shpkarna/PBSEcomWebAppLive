"""MySQL-backed audit log repository."""
from __future__ import annotations

from typing import Any, Iterable

from app.config import settings
from app.data.mysql_client import mysql_server_connection
from app.data.repositories.mysql_base import MySQLRepositoryBase
from app.domain.contracts.log_repository import LogRepository


class MySQLLogRepository(MySQLRepositoryBase, LogRepository):
    """MySQL implementation for audit log persistence."""

    def _execute_log(
        self,
        sql: str,
        params: Iterable[Any] | None = None,
        *,
        fetchall: bool = False,
    ) -> Any:
        with mysql_server_connection(database=settings.log_database) as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, tuple(params or ()))
                if fetchall:
                    return list(cursor.fetchall())
                return cursor.rowcount

    def insert_event(self, event: dict) -> None:
        spec = self._spec("audit_logs")
        columns, values, _ = self._prepare_insert(spec, event)
        placeholders = ", ".join(["%s"] * len(columns))
        self._execute_log(
            f"INSERT INTO {spec.table_name} ({', '.join(columns)}) VALUES ({placeholders})",
            values,
        )

    def list_events(self, limit: int = 100) -> list[dict]:
        spec = self._spec("audit_logs")
        rows = self._execute_log(
            f"SELECT * FROM {spec.table_name} ORDER BY created_at DESC LIMIT %s",
            [int(limit)],
            fetchall=True,
        )
        return [self._row_to_doc(spec, row) for row in rows or [] if row]