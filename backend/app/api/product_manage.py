"""Product update, delete, and stock management routes."""
import os
from io import BytesIO
from fastapi import APIRouter, HTTPException, status, Depends, File, UploadFile
from fastapi.responses import Response
from app.database import get_collection
from app.schemas.schemas import ProductUpdate, ProductResponse
from app.utils.logger import log_event
from app.utils.rbac import require_functionality, require_role
from bson import ObjectId
from bson.binary import Binary
from datetime import datetime
from gridfs import GridFSBucket

router = APIRouter(prefix="/api/products", tags=["Products"])

DISCOUNT_PERCENTAGE = "Discount percentage"
DISCOUNT_AMOUNT = "Discount amount"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".svg"}
VIDEO_EXTENSIONS = {".mp4", ".webm", ".ogg", ".mov", ".avi", ".mkv"}
IMAGE_MIME_PREFIX = "image/"
VIDEO_MIME_PREFIX = "video/"
MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_VIDEO_BYTES = 100 * 1024 * 1024


def _resolve_media_type(filename: str, content_type: str | None) -> str:
    ctype = (content_type or "").lower()
    if ctype.startswith(IMAGE_MIME_PREFIX):
        return "image"
    if ctype.startswith(VIDEO_MIME_PREFIX):
        return "video"

    ext = os.path.splitext(filename or "")[1].lower()
    if ext in IMAGE_EXTENSIONS:
        return "image"
    if ext in VIDEO_EXTENSIONS:
        return "video"
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported media file type for '{filename}'")


def _normalize_product_doc(product: dict) -> dict:
    product["image_media_ids"] = [str(media_id) for media_id in product.get("image_media_ids", [])]
    product["video_media_ids"] = [str(media_id) for media_id in product.get("video_media_ids", [])]
    return product


def _validate_discount_fields(discount: str | None, discount_value: float | None) -> None:
    if discount is None and discount_value is None:
        return
    if discount is None and discount_value is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Discount field is required when discount value is set")
    if discount is not None and discount_value is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Discount value is required when discount field is set")
    if discount == DISCOUNT_PERCENTAGE and (discount_value < 0 or discount_value > 100):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Discount percentage must be between 0 and 100")
    if discount == DISCOUNT_AMOUNT and discount_value < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Discount amount must be 0 or greater")


def _get_media_bucket() -> GridFSBucket:
    return GridFSBucket(get_collection("product_media").database, bucket_name="product_media_files")


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(product_id: str, product_update: ProductUpdate,
                         current_user=Depends(require_functionality("inventory_manage"))):
    """Update product."""
    products_col = get_collection("products")
    try:
        product_oid = ObjectId(product_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid product ID")
    current = products_col.find_one({"_id": product_oid})
    if not current:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    update_dict = product_update.model_dump(exclude_unset=True)
    effective_discount = update_dict.get("discount", current.get("discount"))
    effective_discount_value = update_dict.get("discount_value", current.get("discount_value"))
    _validate_discount_fields(effective_discount, effective_discount_value)

    update_dict["updated_at"] = datetime.utcnow()
    result = products_col.find_one_and_update({"_id": product_oid}, {"$set": update_dict}, return_document=True)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    log_event("product_update", user=current_user["username"],
              details={"product_id": product_id, "updated_fields": update_dict},
              path=f"/api/products/{product_id}")
    return ProductResponse(**_normalize_product_doc(result))


@router.delete("/{product_id}")
async def delete_product(product_id: str, current_user=Depends(require_role(["admin"]))):
    """Delete product (Admin only)"""
    products_col = get_collection("products")
    try:
        product_oid = ObjectId(product_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid product ID")
    result = products_col.delete_one({"_id": product_oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    log_event("product_delete", user=current_user["username"],
              details={"product_id": product_id}, path=f"/api/products/{product_id}")
    return {"message": "Product deleted successfully"}


@router.post("/{product_id}/stock")
async def update_stock(product_id: str, quantity: int,
                       current_user=Depends(require_functionality("inventory_manage"))):
    """Update product stock"""
    if current_user["role"] in ["business", "vendor"] and quantity <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Business users can only increase stock quantity")
    products_col = get_collection("products")
    stock_ledger_col = get_collection("stock_ledger")
    try:
        product_oid = ObjectId(product_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid product ID")
    product = products_col.find_one({"_id": product_oid})
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    new_qty = max(0, product.get("stock_quantity", 0) + quantity)
    products_col.update_one({"_id": product_oid},
                            {"$set": {"stock_quantity": new_qty, "updated_at": datetime.utcnow()}})
    stock_ledger_col.insert_one({
        "product_id": product_id,
        "transaction_type": "inbound" if quantity > 0 else "outbound",
        "quantity": abs(quantity), "reference": "Manual adjustment",
        "created_at": datetime.utcnow(),
    })
    log_event("stock_update", user=current_user["username"],
              details={"product_id": product_id, "adjustment": quantity, "new_quantity": new_qty},
              path=f"/api/products/{product_id}/stock")
    return {"message": "Stock updated", "new_quantity": new_qty}


@router.post("/{product_id}/media")
async def upload_product_media(
    product_id: str,
    files: list[UploadFile] = File(...),
    current_user=Depends(require_functionality("inventory_manage")),
):
    """Upload one or more product media files and store them in MongoDB."""
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No media files provided")

    products_col = get_collection("products")
    media_col = get_collection("product_media")
    media_bucket = _get_media_bucket()

    try:
        product_oid = ObjectId(product_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid product ID")

    product = products_col.find_one({"_id": product_oid})
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    inserted_items = []
    now = datetime.utcnow()
    for file in files:
        content = await file.read()
        media_type = _resolve_media_type(file.filename or "", file.content_type)

        if media_type == "image" and len(content) > MAX_IMAGE_BYTES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"Image '{file.filename}' exceeds max size of {MAX_IMAGE_BYTES // (1024 * 1024)} MB")
        if media_type == "video" and len(content) > MAX_VIDEO_BYTES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"Video '{file.filename}' exceeds max size of {MAX_VIDEO_BYTES // (1024 * 1024)} MB")

        doc = {
            "product_id": product_oid,
            "filename": file.filename or "media",
            "content_type": file.content_type or "application/octet-stream",
            "media_type": media_type,
            "size": len(content),
            "created_at": now,
            "created_by": current_user["username"],
        }
        gridfs_file_id = media_bucket.upload_from_stream(
            file.filename or "media",
            content,
            metadata={
                "product_id": str(product_oid),
                "media_type": media_type,
                "content_type": file.content_type or "application/octet-stream",
            },
        )
        doc["gridfs_file_id"] = gridfs_file_id
        result = media_col.insert_one(doc)
        inserted_items.append({"id": str(result.inserted_id), "media_type": media_type})

    image_ids = [item["id"] for item in inserted_items if item["media_type"] == "image"]
    video_ids = [item["id"] for item in inserted_items if item["media_type"] == "video"]

    update_doc = {"$set": {"updated_at": datetime.utcnow()}}
    if image_ids:
        update_doc.setdefault("$push", {})["image_media_ids"] = {"$each": image_ids}
    if video_ids:
        update_doc.setdefault("$push", {})["video_media_ids"] = {"$each": video_ids}

    products_col.update_one({"_id": product_oid}, update_doc)

    log_event(
        "product_media_upload",
        user=current_user["username"],
        details={
            "product_id": product_id,
            "uploaded_count": len(inserted_items),
            "image_count": len(image_ids),
            "video_count": len(video_ids),
        },
        path=f"/api/products/{product_id}/media",
    )

    return {
        "message": "Media uploaded successfully",
        "uploaded_count": len(inserted_items),
        "image_count": len(image_ids),
        "video_count": len(video_ids),
    }


@router.get("/{product_id}/media")
async def list_product_media(
    product_id: str,
    _: dict = Depends(require_functionality("inventory_manage")),
):
    """List all media metadata for a product."""
    try:
        product_oid = ObjectId(product_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid product ID")

    media_col = get_collection("product_media")
    docs = list(media_col.find({"product_id": product_oid}, {"data": 0}).sort("created_at", -1))

    media = []
    for d in docs:
        media.append({
            "id": str(d["_id"]),
            "filename": d.get("filename", ""),
            "content_type": d.get("content_type", "application/octet-stream"),
            "media_type": d.get("media_type", "image"),
            "size": d.get("size", 0),
            "created_at": d.get("created_at"),
            "url": f"/api/products/media/file/{str(d['_id'])}",
        })
    return {"items": media}


@router.get("/media/file/{media_id}")
async def get_product_media_file(media_id: str):
    """Serve product media binary from MongoDB."""
    try:
        media_oid = ObjectId(media_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid media ID")

    media_doc = get_collection("product_media").find_one({"_id": media_oid})
    if not media_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")

    if media_doc.get("gridfs_file_id"):
        buffer = BytesIO()
        bucket = _get_media_bucket()
        bucket.download_to_stream(media_doc["gridfs_file_id"], buffer)
        return Response(
            content=buffer.getvalue(),
            media_type=media_doc.get("content_type", "application/octet-stream"),
            headers={"Cache-Control": "no-store, max-age=0"},
        )

    return Response(
        content=bytes(media_doc.get("data") or b""),
        media_type=media_doc.get("content_type", "application/octet-stream"),
        headers={"Cache-Control": "no-store, max-age=0"},
    )
