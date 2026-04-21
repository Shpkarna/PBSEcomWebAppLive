"""Brand image upload/serve API."""
import os
from datetime import datetime
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, status, Request
from fastapi.responses import Response
from app.data.repository_providers import get_order_cart_repository
from app.domain.contracts.order_cart_repository import OrderCartRepository
from app.utils.rbac import require_functionality

router = APIRouter(prefix="/api/brand", tags=["Brand"])

ALLOWED_EXTENSIONS = {".svg", ".png", ".jpg", ".jpeg", ".webp"}
MAX_SIZE = 5 * 1024 * 1024  # 5 MB
MEDIA_TYPES = {
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}
COMPANY_ASSET_KEY = "company_image"


@router.post("/upload")
async def upload_brand_image(
    file: UploadFile = File(...),
    ctx: dict = Depends(require_functionality("inventory_manage")),
    repo: OrderCartRepository = Depends(get_order_cart_repository),
):
    """Upload a new company image (admin only)."""
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"File type not allowed. Accepted: {', '.join(ALLOWED_EXTENSIONS)}")

    contents = await file.read()
    if len(contents) > MAX_SIZE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File too large (max 5 MB)")

    repo.upsert_company_asset(COMPANY_ASSET_KEY, {
        "asset_key": COMPANY_ASSET_KEY,
        "filename": file.filename or f"company-image{ext}",
        "extension": ext,
        "content_type": MEDIA_TYPES.get(ext, file.content_type or "application/octet-stream"),
        "size": len(contents),
        "data": contents,
        "updated_at": datetime.utcnow(),
        "updated_by": ctx.get("username", "unknown"),
    })

    return {"message": "Company image uploaded", "filename": file.filename or f"company-image{ext}"}


@router.get("/image")
async def get_brand_image(request: Request, repo: OrderCartRepository = Depends(get_order_cart_repository)):
    """Serve the current company image."""
    asset = repo.get_company_assets(COMPANY_ASSET_KEY)
    if asset and asset.get("data"):
        updated_at = asset.get("updated_at")
        if isinstance(updated_at, datetime):
            version_tag = int(updated_at.timestamp())
        else:
            version_tag = len(asset["data"])
        etag = f'"company-image-{version_tag}-{asset.get("size", len(asset["data"]))}"'

        if request.headers.get("if-none-match") == etag:
            return Response(
                status_code=status.HTTP_304_NOT_MODIFIED,
                headers={
                    "Cache-Control": "public, max-age=3600, must-revalidate",
                    "ETag": etag,
                },
            )

        return Response(
            content=bytes(asset["data"]),
            media_type=asset.get("content_type", "application/octet-stream"),
            headers={
                "Cache-Control": "public, max-age=3600, must-revalidate",
                "ETag": etag,
                "Content-Disposition": f'inline; filename="{asset.get("filename", "company-image")}"',
            },
        )

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No company image uploaded")
