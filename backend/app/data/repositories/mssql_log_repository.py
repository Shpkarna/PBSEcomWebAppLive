"""SQL Server-backed audit log repository (Phase 7)."""
from __future__ import annotations

from typing import Any, Iterable

from app.config import settings
from app.data.mssql_client import mssql_server_connection
from app.data.repositories.mssql_base import MSSQLRepositoryBase
from app.domain.contracts.log_repository import LogRepository


class MSSQLLogRepository(MSSQLRepositoryBase, LogRepository):
    """SQL Server implementation for audit log persistence."""

    def _execute_log(
        self,
        sql: str,
        params: Iterable[Any] | None = None,
        *,
        fetchall: bool = False,
    ) -> Any:
        with mssql_server_connection(database=settings.mssql_log_database) as connection:
            cursor = connection.cursor()
            cursor.execute(sql, tuple(params or ()))
            if fetchall:
                return self._rows_to_dicts(cursor)
            return cursor.rowcount

    def insert_event(self, event: dict) -> None:
        spec = self._spec("audit_logs")
        columns, values, _ = self._prepare_insert(spec, event)
        placeholders = ", ".join(["?"] * len(columns))
        self._execute_log(
            f"INSERT INTO {spec.table_name} ({', '.join(columns)}) VALUES ({placeholders})",
            values,
        )

    def list_events(self, limit: int = 100) -> list[dict]:
        spec = self._spec("audit_logs")
        rows = self._execute_log(
            (
                f"SELECT TOP (?) * FROM {spec.table_name} "
                f"ORDER BY created_at DESC"
            ),
            [int(limit)],
            fetchall=True,
        )
        return [self._row_to_doc(spec, row) for row in rows or [] if row]
