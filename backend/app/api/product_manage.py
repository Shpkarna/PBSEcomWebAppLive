"""Product update, delete, and stock management routes."""
import os
from fastapi import APIRouter, HTTPException, status, Depends, File, UploadFile
from fastapi.responses import Response
from app.data.repository_providers import get_order_cart_repository, get_product_repository
from app.domain.contracts.order_cart_repository import OrderCartRepository
from app.domain.contracts.product_repository import ProductRepository
from app.schemas.schemas import ProductUpdate, ProductResponse
from app.utils.logger import log_event
from app.utils.rbac import require_functionality, require_role
from datetime import datetime

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


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(product_id: str, product_update: ProductUpdate,
                         current_user=Depends(require_functionality("inventory_manage")),
                         product_repo: ProductRepository = Depends(get_product_repository)):
    """Update product."""
    current = product_repo.get_by_id(product_id)
    if current is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    update_dict = product_update.model_dump(exclude_unset=True)
    effective_discount = update_dict.get("discount", current.get("discount"))
    effective_discount_value = update_dict.get("discount_value", current.get("discount_value"))
    _validate_discount_fields(effective_discount, effective_discount_value)

    update_dict["updated_at"] = datetime.utcnow()
    result = product_repo.update_product(product_id, update_dict)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    log_event("product_update", user=current_user["username"],
              details={"product_id": product_id, "updated_fields": update_dict},
              path=f"/api/products/{product_id}")
    return ProductResponse(**_normalize_product_doc(result))


@router.delete("/{product_id}")
async def delete_product(
    product_id: str,
    current_user=Depends(require_role(["admin"])),
    product_repo: ProductRepository = Depends(get_product_repository),
):
    """Delete product (Admin only)"""
    if not product_repo.delete_product(product_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    log_event("product_delete", user=current_user["username"],
              details={"product_id": product_id}, path=f"/api/products/{product_id}")
    return {"message": "Product deleted successfully"}


@router.post("/{product_id}/stock")
async def update_stock(product_id: str, quantity: int,
                       current_user=Depends(require_functionality("inventory_manage")),
                       product_repo: ProductRepository = Depends(get_product_repository),
                       repo: OrderCartRepository = Depends(get_order_cart_repository)):
    """Update product stock"""
    if current_user["role"] in ["business", "vendor"] and quantity <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Business users can only increase stock quantity")
    try:
        product = product_repo.get_by_id(product_id)
    except ValueError:
        product = None
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    new_qty = max(0, product.get("stock_quantity", 0) + quantity)
    repo.update_product_stock(product_id, new_qty)
    repo.insert_stock_ledger_row({
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
    product_repo: ProductRepository = Depends(get_product_repository),
):
    """Upload one or more product media files and store them in MongoDB."""
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No media files provided")

    try:
        product = product_repo.get_by_id(product_id)
    except ValueError:
        product = None
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    inserted_items = []
    for file in files:
        content = await file.read()
        media_type = _resolve_media_type(file.filename or "", file.content_type)

        if media_type == "image" and len(content) > MAX_IMAGE_BYTES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"Image '{file.filename}' exceeds max size of {MAX_IMAGE_BYTES // (1024 * 1024)} MB")
        if media_type == "video" and len(content) > MAX_VIDEO_BYTES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"Video '{file.filename}' exceeds max size of {MAX_VIDEO_BYTES // (1024 * 1024)} MB")

        item = product_repo.upload_media(
            product_id=product_id,
            filename=file.filename or "media",
            content=content,
            content_type=file.content_type or "application/octet-stream",
            media_type=media_type,
            created_by=current_user["username"],
        )
        inserted_items.append(item)

    image_ids = [item["id"] for item in inserted_items if item["media_type"] == "image"]
    video_ids = [item["id"] for item in inserted_items if item["media_type"] == "video"]

    product_repo.add_media_ids_to_product(product_id, image_ids, video_ids)

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
    product_repo: ProductRepository = Depends(get_product_repository),
):
    """List all media metadata for a product."""
    return {"items": product_repo.list_media(product_id)}


@router.get("/media/file/{media_id}")
async def get_product_media_file(
    media_id: str,
    product_repo: ProductRepository = Depends(get_product_repository),
):
    """Serve product media binary from storage."""
    result = product_repo.get_media_content(media_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")
    content, content_type = result
    return Response(
        content=content,
        media_type=content_type,
        headers={"Cache-Control": "no-store, max-age=0"},
    )
