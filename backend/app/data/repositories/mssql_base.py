"""Shared SQL Server repository helpers (Phase 7).

Mirrors mysql_base.py contract exactly.  Key differences vs MySQL:
- pyodbc uses ``?`` placeholders (not ``%s``)
- pyodbc cursor rows are tuples — converted to dicts via cursor.description
- Pagination uses T-SQL ``OFFSET n ROWS FETCH NEXT m ROWS ONLY``
  which requires an ORDER BY clause (``spec.id_column`` used as fallback)
- Single-row fetch uses ``SELECT TOP (1)`` instead of ``LIMIT 1``
"""
from __future__ import annotations

from typing import Any, Iterable, Optional

from app.data.mssql_client import mssql_connection, mssql_transaction
from app.data.mssql_support import (
    MSSQL_TABLE_SPECS,
    TableSpec,
    dumps_json,
    generate_id,
    loads_json,
    normalize_document_value,
    normalize_scalar_for_storage,
)


class MSSQLRepositoryBase:
    """Common SQL and row-mapping helpers used by SQL Server repositories."""

    def transaction(self):
        return mssql_transaction()

    def _spec(self, collection_name: str) -> TableSpec:
        try:
            return MSSQL_TABLE_SPECS[collection_name]
        except KeyError as exc:
            raise ValueError(f"Unsupported MSSQL collection '{collection_name}'") from exc

    # ------------------------------------------------------------------
    # Low-level execute helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _rows_to_dicts(cursor) -> list[dict]:
        """Convert all fetched rows to a list of dicts using cursor.description."""
        if cursor.description is None:
            return []
        cols = [col[0] for col in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]

    @staticmethod
    def _row_to_dict(cursor, row) -> dict | None:
        """Convert a single pyodbc Row to a dict."""
        if row is None:
            return None
        if cursor.description is None:
            return None
        cols = [col[0] for col in cursor.description]
        return dict(zip(cols, row))

    def _execute(
        self,
        sql: str,
        params: Iterable[Any] | None = None,
        *,
        fetchone: bool = False,
        fetchall: bool = False,
    ) -> Any:
        with mssql_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(sql, tuple(params or ()))
            if fetchone:
                row = cursor.fetchone()
                return self._row_to_dict(cursor, row)
            if fetchall:
                return self._rows_to_dicts(cursor)
            return cursor.rowcount

    def _execute_many(self, sql: str, seq_of_params: Iterable[Iterable[Any]]) -> int:
        with mssql_connection() as connection:
            cursor = connection.cursor()
            cursor.executemany(sql, [tuple(params) for params in seq_of_params])
            return cursor.rowcount

    # ------------------------------------------------------------------
    # Row → document mapping
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_column(spec: TableSpec, key: str) -> str:
        if key in {"id", "_id"}:
            return spec.id_column
        if key == spec.id_column:
            return spec.id_column
        if key in spec.columns:
            return key
        raise ValueError(f"Unsupported filter field '{key}' for table '{spec.table_name}'")

    def _coerce_row_value(self, spec: TableSpec, column: str, value: Any) -> Any:
        if value is None:
            return None
        if column in spec.bool_columns:
            return bool(value)
        if column in spec.decimal_columns:
            return float(value)
        if column in spec.binary_columns:
            return bytes(value)
        return normalize_document_value(value)

    def _row_to_doc(self, spec: TableSpec, row: dict | None) -> Optional[dict]:
        if not row:
            return None

        doc: dict[str, Any] = {}
        if spec.json_column:
            payload = loads_json(row.get(spec.json_column))
            if isinstance(payload, dict):
                doc.update(payload)

        id_value = row.get(spec.id_column)
        doc["_id"] = str(id_value)
        doc["id"] = str(id_value)
        if spec.id_column != "id":
            doc[spec.id_column] = id_value

        for column in spec.columns:
            if column == spec.id_column:
                continue
            if column not in row:
                continue
            doc[column] = self._coerce_row_value(spec, column, row.get(column))

        return doc

    @staticmethod
    def _apply_projection(doc: dict | None, projection: dict | None) -> Optional[dict]:
        if doc is None or not projection:
            return doc

        include = {key for key, value in projection.items() if value}
        exclude = {key for key, value in projection.items() if not value}

        if include:
            projected = {key: value for key, value in doc.items() if key in include}
            if "_id" in doc and "_id" not in projected:
                projected["_id"] = doc["_id"]
            if "id" in doc and "id" not in projected:
                projected["id"] = doc["id"]
            return projected

        projected = dict(doc)
        for key in exclude:
            projected.pop(key, None)
        return projected

    # ------------------------------------------------------------------
    # WHERE clause builder (? placeholders)
    # ------------------------------------------------------------------

    def _build_where(self, spec: TableSpec, filter_doc: dict) -> tuple[str, list[Any]]:
        if not filter_doc:
            return "1=1", []

        clauses: list[str] = []
        params: list[Any] = []

        for key, value in filter_doc.items():
            column = self._resolve_column(spec, key)
            if isinstance(value, dict):
                for operator, operand in value.items():
                    if operator == "$ne":
                        clauses.append(f"({column} <> ? OR {column} IS NULL)")
                        params.append(normalize_scalar_for_storage(column, operand))
                    elif operator == "$in":
                        values = list(operand or [])
                        if not values:
                            clauses.append("1=0")
                            continue
                        placeholders = ", ".join(["?"] * len(values))
                        clauses.append(f"{column} IN ({placeholders})")
                        params.extend(normalize_scalar_for_storage(column, item) for item in values)
                    elif operator == "$gte":
                        clauses.append(f"{column} >= ?")
                        params.append(normalize_scalar_for_storage(column, operand))
                    elif operator == "$lte":
                        clauses.append(f"{column} <= ?")
                        params.append(normalize_scalar_for_storage(column, operand))
                    elif operator == "$gt":
                        clauses.append(f"{column} > ?")
                        params.append(normalize_scalar_for_storage(column, operand))
                    elif operator == "$lt":
                        clauses.append(f"{column} < ?")
                        params.append(normalize_scalar_for_storage(column, operand))
                    elif operator == "$regex":
                        pattern = str(operand).strip("^").strip("$")
                        clauses.append(f"LOWER({column}) LIKE LOWER(?)")
                        params.append(f"%{pattern}%")
                    else:
                        raise ValueError(f"Unsupported filter operator '{operator}'")
                continue

            if value is None:
                clauses.append(f"({column} IS NULL OR {column} = '')")
                continue

            clauses.append(f"{column} = ?")
            params.append(normalize_scalar_for_storage(column, value))

        return " AND ".join(clauses), params

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def _find_one_row(self, collection_name: str, filter_doc: dict) -> Optional[dict]:
        spec = self._spec(collection_name)
        where_sql, params = self._build_where(spec, filter_doc)
        return self._execute(
            f"SELECT TOP (1) * FROM {spec.table_name} WHERE {where_sql}",
            params,
            fetchone=True,
        )

    def _find_rows(
        self,
        collection_name: str,
        filter_doc: dict,
        *,
        order_by: str | None = None,
        descending: bool = False,
        skip: int = 0,
        limit: int | None = None,
    ) -> list[dict]:
        spec = self._spec(collection_name)
        where_sql, params = self._build_where(spec, filter_doc)
        sort_key = order_by or spec.id_column
        direction = "DESC" if descending else "ASC"
        sql = f"SELECT * FROM {spec.table_name} WHERE {where_sql} ORDER BY {sort_key} {direction}"
        if limit is not None:
            sql += " OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
            params = [*params, int(skip), int(limit)]
        elif skip:
            sql += " OFFSET ? ROWS FETCH NEXT 2147483647 ROWS ONLY"
            params = [*params, int(skip)]

        return self._execute(sql, params, fetchall=True) or []

    # ------------------------------------------------------------------
    # Insert / update / delete helpers
    # ------------------------------------------------------------------

    def _prepare_insert(self, spec: TableSpec, doc: dict) -> tuple[list[str], list[Any], str]:
        source = dict(doc)
        if spec.id_column == "id":
            identifier = str(source.pop("_id", source.pop("id", generate_id())))
        else:
            raw_identifier = source.get(spec.id_column) or source.pop("_id", None) or source.pop("id", None)
            identifier = str(raw_identifier or generate_id())
            source[spec.id_column] = identifier

        columns: list[str] = [spec.id_column]
        values: list[Any] = [normalize_scalar_for_storage(spec.id_column, identifier)]
        base_columns = set(spec.columns)

        for column in spec.columns:
            if column == spec.id_column:
                continue
            if column not in source:
                continue
            columns.append(column)
            values.append(normalize_scalar_for_storage(column, source.pop(column)))

        if spec.id_column in source:
            source.pop(spec.id_column, None)
        source.pop("_id", None)
        source.pop("id", None)

        if spec.json_column:
            payload = {key: value for key, value in source.items() if key not in base_columns}
            if payload:
                columns.append(spec.json_column)
                values.append(dumps_json(payload))

        return columns, values, identifier

    def _insert_doc(self, collection_name: str, doc: dict) -> dict:
        spec = self._spec(collection_name)
        columns, values, identifier = self._prepare_insert(spec, doc)
        placeholders = ", ".join(["?"] * len(columns))
        self._execute(
            f"INSERT INTO {spec.table_name} ({', '.join(columns)}) VALUES ({placeholders})",
            values,
        )

        stored = dict(doc)
        stored["_id"] = identifier
        stored["id"] = identifier
        if spec.id_column != "id":
            stored[spec.id_column] = identifier
        return stored

    def _update_doc(self, collection_name: str, filter_doc: dict, updates: dict, *, upsert: bool = False) -> int:
        spec = self._spec(collection_name)
        existing_row = self._find_one_row(collection_name, filter_doc)
        if existing_row is None:
            if not upsert:
                return 0
            insert_doc = dict(filter_doc)
            insert_doc.update(updates)
            self._insert_doc(collection_name, insert_doc)
            return 1

        current_doc = self._row_to_doc(spec, existing_row) or {}
        merged_doc = dict(current_doc)
        merged_doc.update(updates)
        merged_doc["_id"] = current_doc["_id"]
        merged_doc["id"] = current_doc["id"]
        if spec.id_column != "id":
            merged_doc[spec.id_column] = current_doc.get(spec.id_column, current_doc["id"])

        assignments: list[str] = []
        values: list[Any] = []
        for column in spec.columns:
            if column == spec.id_column:
                continue
            assignments.append(f"{column} = ?")
            values.append(normalize_scalar_for_storage(column, merged_doc.get(column)))

        if spec.json_column:
            payload = {
                key: value
                for key, value in merged_doc.items()
                if key not in set(spec.columns) | {"_id", "id", spec.id_column}
            }
            assignments.append(f"{spec.json_column} = ?")
            values.append(dumps_json(payload))

        where_sql, where_params = self._build_where(spec, filter_doc)
        values.extend(where_params)
        return self._execute(
            f"UPDATE {spec.table_name} SET {', '.join(assignments)} WHERE {where_sql}",
            values,
        )

    def _delete_docs(self, collection_name: str, filter_doc: dict) -> int:
        spec = self._spec(collection_name)
        where_sql, params = self._build_where(spec, filter_doc)
        return self._execute(f"DELETE FROM {spec.table_name} WHERE {where_sql}", params)

    # ------------------------------------------------------------------
    # Public contract methods
    # ------------------------------------------------------------------

    def find_one_doc(self, collection_name: str, filter_doc: dict, projection: dict | None = None) -> Optional[dict]:
        spec = self._spec(collection_name)
        row = self._find_one_row(collection_name, filter_doc)
        return self._apply_projection(self._row_to_doc(spec, row), projection)

    def find_many_docs(
        self,
        collection_name: str,
        filter_doc: dict,
        *,
        projection: dict | None = None,
        order_by: str | None = None,
        descending: bool = False,
        skip: int = 0,
        limit: int | None = None,
    ) -> list[dict]:
        spec = self._spec(collection_name)
        rows = self._find_rows(
            collection_name,
            filter_doc,
            order_by=order_by,
            descending=descending,
            skip=skip,
            limit=limit,
        )
        docs = [self._row_to_doc(spec, row) for row in rows]
        return [self._apply_projection(doc, projection) for doc in docs if doc is not None]

    def insert_one_doc(self, collection_name: str, doc: dict) -> dict:
        return self._insert_doc(collection_name, doc)

    def update_one_doc(self, collection_name: str, filter_doc: dict, updates: dict, *, upsert: bool = False) -> int:
        return self._update_doc(collection_name, filter_doc, updates, upsert=upsert)

    def delete_many_docs(self, collection_name: str, filter_doc: dict) -> int:
        return self._delete_docs(collection_name, filter_doc)
