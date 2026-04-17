"""Entity-driven async CSV import/export and public entity sync APIs."""
from __future__ import annotations

import csv
import hmac
from datetime import datetime
from io import StringIO
from typing import Any

from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, Depends, File, Header, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.config import settings
from app.database import get_collection
from app.utils.rbac import require_role
from app.utils.security import hash_password


admin_router = APIRouter(prefix="/api/admin/data-sync", tags=["Data Sync"])
public_router = APIRouter(prefix="/public/api", tags=["Public Entity API"])


JOB_COLLECTION = "data_sync_jobs"


async def _require_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> str:
    """Validate the API key supplied via X-API-Key header."""
    expected = settings.public_api_key or ""
    if not expected:
        raise HTTPException(status_code=503, detail="Public API key not configured on the server")
    if not hmac.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key


class EntityUpsertRequest(BaseModel):
    data: dict[str, Any]


class EntityBulkUpsertRequest(BaseModel):
    items: list[dict[str, Any]] = Field(default_factory=list)


ENTITY_CONFIGS: dict[str, dict[str, Any]] = {
    "vendor": {
        "collection": "vendors",
        "required_fields": ["name"],
        "field_types": {
            "name": "str",
            "email": "str",
            "phone": "str",
            "address": "str",
            "gst_number": "str",
            "bank_details": "str",
        },
        "upsert_keys": ["email", "name"],
        "export_fields": ["name", "email", "phone", "address", "gst_number", "bank_details"],
    },
    "customer": {
        "collection": "users",
        "required_fields": ["username", "email", "full_name", "phone", "dob"],
        "field_types": {
            "username": "str",
            "email": "str",
            "full_name": "str",
            "phone": "str",
            "address": "str",
            "dob": "str",
            "sex": "str",
            "marital_status": "str",
            "is_active": "bool",
            "phone_verified": "bool",
            "email_verified": "bool",
            "password": "str",
        },
        "upsert_keys": ["username", "email"],
        "export_fields": [
            "username",
            "email",
            "full_name",
            "phone",
            "address",
            "dob",
            "sex",
            "marital_status",
            "is_active",
            "phone_verified",
            "email_verified",
        ],
        "base_filter": {"role": "customer"},
    },
    "product_category": {
        "collection": "categories",
        "required_fields": ["name"],
        "field_types": {
            "name": "str",
            "description": "str",
            "discount_type": "str",
            "discount_value": "float",
        },
        "upsert_keys": ["name"],
        "export_fields": ["name", "description", "discount_type", "discount_value"],
    },
    "product_master": {
        "collection": "products",
        "required_fields": ["sku", "name", "barcode", "stock_price", "sell_price"],
        "field_types": {
            "sku": "str",
            "name": "str",
            "barcode": "str",
            "stock_price": "float",
            "sell_price": "float",
            "description": "str",
            "category": "str",
            "discount": "str",
            "discount_value": "float",
            "discount_type": "str",
            "stock_quantity": "int",
            "gst_rate": "float",
            "is_active": "bool",
        },
        "upsert_keys": ["sku", "barcode"],
        "export_fields": [
            "sku",
            "name",
            "barcode",
            "stock_price",
            "sell_price",
            "description",
            "category",
            "discount",
            "discount_value",
            "discount_type",
            "stock_quantity",
            "gst_rate",
            "is_active",
        ],
    },
}


def _now() -> datetime:
    return datetime.utcnow()


def _oid(job_id: str) -> ObjectId:
    try:
        return ObjectId(job_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid job id") from exc


def _sanitize_doc(doc: dict[str, Any]) -> dict[str, Any]:
    out = dict(doc)
    out["id"] = str(out.pop("_id"))
    out.pop("password_hash", None)
    return out


def _entity_config(entity: str) -> dict[str, Any]:
    cfg = ENTITY_CONFIGS.get(entity)
    if not cfg:
        raise HTTPException(status_code=400, detail=f"Unsupported entity '{entity}'")
    return cfg


def _parse_typed_value(raw: str, typ: str) -> Any:
    value = (raw or "").strip()
    if value == "":
        return None
    if typ == "str":
        return value
    if typ == "int":
        return int(value)
    if typ == "float":
        return float(value)
    if typ == "bool":
        lowered = value.lower()
        if lowered in {"true", "1", "yes", "y"}:
            return True
        if lowered in {"false", "0", "no", "n"}:
            return False
        raise ValueError("expected boolean value")
    return value


def _validate_and_normalize_row(entity: str, row: dict[str, str]) -> tuple[dict[str, Any], list[str]]:
    cfg = _entity_config(entity)
    errors: list[str] = []
    normalized: dict[str, Any] = {}

    for field in cfg["required_fields"]:
        if not (row.get(field) or "").strip():
            errors.append(f"missing required field '{field}'")

    for field, typ in cfg["field_types"].items():
        try:
            parsed = _parse_typed_value(row.get(field, ""), typ)
        except Exception:
            errors.append(f"invalid value for field '{field}'")
            continue

        if parsed is not None:
            normalized[field] = parsed

    if entity == "customer":
        normalized.setdefault("role", "customer")
        normalized.setdefault("is_active", True)
        normalized.setdefault("phone_verified", False)
        normalized.setdefault("email_verified", False)

    if entity == "product_master":
        normalized.setdefault("stock_quantity", 0)
        normalized.setdefault("gst_rate", 0.18)

    return normalized, errors


def _resolve_upsert_filter(entity: str, normalized: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    cfg = _entity_config(entity)
    for key in cfg["upsert_keys"]:
        val = normalized.get(key)
        if val not in (None, ""):
            flt: dict[str, Any] = {key: val}
            if entity == "customer":
                flt["role"] = "customer"
            return flt, key
    return None, None


def _upsert_entity_row(entity: str, normalized: dict[str, Any]) -> None:
    cfg = _entity_config(entity)
    coll = get_collection(cfg["collection"])

    flt, _ = _resolve_upsert_filter(entity, normalized)
    if not flt:
        raise ValueError("row has no upsert key")

    now = _now()
    existing = coll.find_one(flt)

    if entity == "customer":
        password = str(normalized.pop("password", "") or "")
        if password:
            normalized["password_hash"] = hash_password(password)
        elif not existing:
            normalized["password_hash"] = hash_password("ChangeMe@123")

    normalized["updated_at"] = now

    if existing:
        coll.update_one({"_id": existing["_id"]}, {"$set": normalized})
        return

    normalized["created_at"] = now
    coll.insert_one(normalized)


def _create_job(entity: str, job_type: str, requested_by: str, source_filename: str | None = None) -> str:
    doc = {
        "entity": entity,
        "job_type": job_type,
        "status": "queued",
        "requested_by": requested_by,
        "source_filename": source_filename,
        "created_at": _now(),
        "updated_at": _now(),
        "started_at": None,
        "finished_at": None,
        "processed_rows": 0,
        "success_rows": 0,
        "failed_rows": 0,
        "errors": [],
        "result": None,
    }
    res = get_collection(JOB_COLLECTION).insert_one(doc)
    return str(res.inserted_id)


def _mark_job_started(job_oid: ObjectId) -> None:
    get_collection(JOB_COLLECTION).update_one(
        {"_id": job_oid},
        {"$set": {"status": "running", "started_at": _now(), "updated_at": _now()}},
    )


def _mark_job_finished(job_oid: ObjectId, *, processed: int, success: int, failed: int, errors: list[dict[str, Any]], result: dict[str, Any] | None = None) -> None:
    status_value = "completed" if failed == 0 else "completed_with_errors"
    get_collection(JOB_COLLECTION).update_one(
        {"_id": job_oid},
        {
            "$set": {
                "status": status_value,
                "processed_rows": processed,
                "success_rows": success,
                "failed_rows": failed,
                "errors": errors[:500],
                "result": result,
                "finished_at": _now(),
                "updated_at": _now(),
            }
        },
    )


def _mark_job_failed(job_oid: ObjectId, detail: str) -> None:
    get_collection(JOB_COLLECTION).update_one(
        {"_id": job_oid},
        {
            "$set": {
                "status": "failed",
                "finished_at": _now(),
                "updated_at": _now(),
                "errors": [{"row": 0, "errors": [detail]}],
            }
        },
    )


def _run_import_job(job_id: str, entity: str, csv_text: str) -> None:
    job_oid = _oid(job_id)
    try:
        _mark_job_started(job_oid)

        reader = csv.DictReader(StringIO(csv_text))
        processed = 0
        success = 0
        failed = 0
        errors: list[dict[str, Any]] = []

        for row_idx, row in enumerate(reader, start=2):
            processed += 1
            normalized, row_errors = _validate_and_normalize_row(entity, row)
            if row_errors:
                failed += 1
                errors.append({"row": row_idx, "errors": row_errors})
                continue

            try:
                _upsert_entity_row(entity, normalized)
                success += 1
            except Exception as exc:
                failed += 1
                errors.append({"row": row_idx, "errors": [str(exc)]})

        _mark_job_finished(job_oid, processed=processed, success=success, failed=failed, errors=errors)
    except Exception as exc:
        _mark_job_failed(job_oid, str(exc))


def _run_export_job(job_id: str, entity: str) -> None:
    job_oid = _oid(job_id)
    try:
        _mark_job_started(job_oid)

        cfg = _entity_config(entity)
        coll = get_collection(cfg["collection"])
        query = dict(cfg.get("base_filter", {}))

        projection = {field: 1 for field in cfg["export_fields"]}
        docs = list(coll.find(query, projection))

        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=cfg["export_fields"])
        writer.writeheader()

        for doc in docs:
            row = {field: doc.get(field, "") for field in cfg["export_fields"]}
            writer.writerow(row)

        csv_data = output.getvalue()
        processed = len(docs)

        _mark_job_finished(
            job_oid,
            processed=processed,
            success=processed,
            failed=0,
            errors=[],
            result={"csv_data": csv_data, "row_count": processed},
        )
    except Exception as exc:
        _mark_job_failed(job_oid, str(exc))


@admin_router.get("/entities")
async def list_supported_entities(_: dict = Depends(require_role(["admin"]))):
    return {"entities": sorted(ENTITY_CONFIGS.keys())}


@admin_router.post("/import-jobs", status_code=status.HTTP_202_ACCEPTED)
async def create_import_job(
    background_tasks: BackgroundTasks,
    entity: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(require_role(["admin"])),
):
    _entity_config(entity)
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    payload = await file.read()
    try:
        csv_text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="CSV must be UTF-8 encoded") from exc

    job_id = _create_job(entity, "import", current_user.get("username", "admin"), source_filename=file.filename)
    background_tasks.add_task(_run_import_job, job_id, entity, csv_text)

    return {"job_id": job_id, "status": "queued", "entity": entity, "job_type": "import"}


@admin_router.post("/export-jobs", status_code=status.HTTP_202_ACCEPTED)
async def create_export_job(
    background_tasks: BackgroundTasks,
    entity: str,
    current_user: dict = Depends(require_role(["admin"])),
):
    _entity_config(entity)
    job_id = _create_job(entity, "export", current_user.get("username", "admin"))
    background_tasks.add_task(_run_export_job, job_id, entity)
    return {"job_id": job_id, "status": "queued", "entity": entity, "job_type": "export"}


@admin_router.get("/jobs")
async def list_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=200),
    _: dict = Depends(require_role(["admin"])),
):
    coll = get_collection(JOB_COLLECTION)
    docs = list(coll.find().sort("created_at", -1).skip(skip).limit(limit))
    return [_sanitize_doc(d) for d in docs]


@admin_router.get("/jobs/{job_id}")
async def get_job(job_id: str, _: dict = Depends(require_role(["admin"]))):
    doc = get_collection(JOB_COLLECTION).find_one({"_id": _oid(job_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Job not found")
    return _sanitize_doc(doc)


@admin_router.get("/jobs/{job_id}/download")
async def download_export(job_id: str, _: dict = Depends(require_role(["admin"]))):
    doc = get_collection(JOB_COLLECTION).find_one({"_id": _oid(job_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Job not found")
    if doc.get("job_type") != "export":
        raise HTTPException(status_code=400, detail="Download is only available for export jobs")
    if doc.get("status") not in {"completed", "completed_with_errors"}:
        raise HTTPException(status_code=400, detail="Export is not completed yet")

    csv_data = (doc.get("result") or {}).get("csv_data")
    if not csv_data:
        raise HTTPException(status_code=404, detail="No exported CSV data found")

    filename = f"{doc.get('entity', 'entity')}_export_{str(doc.get('_id'))}.csv"
    return StreamingResponse(
        iter([csv_data.encode("utf-8")]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@admin_router.get("/templates/{entity}")
async def download_csv_template(entity: str, _: dict = Depends(require_role(["admin"]))):
    """Download a blank CSV template with the correct headers for the given entity."""
    cfg = _entity_config(entity)
    fields = list(cfg["field_types"].keys())
    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow(fields)
    csv_bytes = buf.getvalue().encode("utf-8")
    filename = f"{entity}_template.csv"
    return StreamingResponse(
        iter([csv_bytes]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@admin_router.get("/jobs/{job_id}/error-report")
async def download_error_report(job_id: str, _: dict = Depends(require_role(["admin"]))):
    """Download a CSV report of row-level errors for a completed import job."""
    doc = get_collection(JOB_COLLECTION).find_one({"_id": _oid(job_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Job not found")
    if doc.get("job_type") != "import":
        raise HTTPException(status_code=400, detail="Error reports are only available for import jobs")
    errors = doc.get("errors") or []
    if not errors:
        raise HTTPException(status_code=404, detail="No errors recorded for this job")
    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow(["row", "errors"])
    for entry in errors:
        writer.writerow([entry.get("row", ""), "; ".join(entry.get("errors", []))])
    csv_bytes = buf.getvalue().encode("utf-8")
    filename = f"{doc.get('entity', 'entity')}_import_errors_{job_id}.csv"
    return StreamingResponse(
        iter([csv_bytes]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@public_router.get("/entities")
async def public_list_entities(_: str = Depends(_require_api_key)):
    return {"entities": sorted(ENTITY_CONFIGS.keys())}


@public_router.get("/entities/{entity}")
async def public_list_entity_records(
    entity: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    _: str = Depends(_require_api_key),
):
    cfg = _entity_config(entity)
    coll = get_collection(cfg["collection"])
    query = dict(cfg.get("base_filter", {}))
    projection = {field: 1 for field in cfg["export_fields"]}
    docs = list(coll.find(query, projection).skip(skip).limit(limit))

    items: list[dict[str, Any]] = []
    for doc in docs:
        doc["id"] = str(doc.pop("_id"))
        items.append(doc)
    return {"entity": entity, "items": items, "skip": skip, "limit": limit}


@public_router.post("/entities/{entity}/upsert")
async def public_upsert_entity(entity: str, payload: EntityUpsertRequest, _: str = Depends(_require_api_key)):
    _entity_config(entity)
    normalized, row_errors = _validate_and_normalize_row(entity, {k: str(v) for k, v in payload.data.items()})
    if row_errors:
        raise HTTPException(status_code=400, detail={"validation_errors": row_errors})

    try:
        _upsert_entity_row(entity, normalized)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"message": "Upserted successfully", "entity": entity}


@public_router.post("/entities/{entity}/bulk-upsert")
async def public_bulk_upsert(entity: str, payload: EntityBulkUpsertRequest, _: str = Depends(_require_api_key)):
    _entity_config(entity)
    if not payload.items:
        raise HTTPException(status_code=400, detail="items cannot be empty")

    processed = 0
    success = 0
    failed = 0
    errors: list[dict[str, Any]] = []

    for idx, item in enumerate(payload.items, start=1):
        processed += 1
        normalized, row_errors = _validate_and_normalize_row(entity, {k: str(v) for k, v in item.items()})
        if row_errors:
            failed += 1
            errors.append({"row": idx, "errors": row_errors})
            continue

        try:
            _upsert_entity_row(entity, normalized)
            success += 1
        except Exception as exc:
            failed += 1
            errors.append({"row": idx, "errors": [str(exc)]})

    return {
        "entity": entity,
        "processed": processed,
        "success": success,
        "failed": failed,
        "errors": errors,
    }
