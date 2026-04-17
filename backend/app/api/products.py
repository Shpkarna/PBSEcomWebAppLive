"""Product CRUD API routes (create, list, get)."""
from fastapi import APIRouter, HTTPException, status, Depends, Query
from app.database import get_collection
from app.schemas.schemas import ProductCreate, ProductResponse
from app.utils.logger import log_event
from app.utils.rbac import require_functionality
from bson import ObjectId
from datetime import datetime

router = APIRouter(prefix="/api/products", tags=["Products"])

DISCOUNT_PERCENTAGE = "Discount percentage"
DISCOUNT_AMOUNT = "Discount amount"


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


@router.post("/", response_model=ProductResponse)
async def create_product(product: ProductCreate, current_user=Depends(require_functionality("inventory_manage"))):
    """Create a new product."""
    products_col = get_collection("products")
    if products_col.find_one({"sku": product.sku}):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Product with SKU {product.sku} already exists")
    product_dict = product.model_dump()
    _validate_discount_fields(product_dict.get("discount"), product_dict.get("discount_value"))
    product_dict["image_media_ids"] = []
    product_dict["video_media_ids"] = []
    product_dict["created_at"] = datetime.utcnow()
    product_dict["updated_at"] = datetime.utcnow()
    result = products_col.insert_one(product_dict)
    product_dict["_id"] = result.inserted_id
    log_event("product_create", user=current_user["username"],
              details={"product_id": str(result.inserted_id), "sku": product.sku}, path="/api/products")
    return ProductResponse(**_normalize_product_doc(product_dict))


@router.get("/", response_model=list[ProductResponse])
async def list_products(skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=500),
                        category: str = Query(None),
                        sort_by: str = Query("latest")):
    """List all products"""
    query = {"category": {"$regex": f"^{category}$", "$options": "i"}} if category else {}

    sort_map: dict[str, tuple[str, int]] = {
        "latest": ("created_at", -1),
        "name_asc": ("name", 1),
        "name_desc": ("name", -1),
        "price_asc": ("sell_price", 1),
        "price_desc": ("sell_price", -1),
    }
    sort_field, sort_dir = sort_map.get(sort_by, ("created_at", -1))

    products = list(get_collection("products").find(query).sort(sort_field, sort_dir).skip(skip).limit(limit))
    return [ProductResponse(**_normalize_product_doc(p)) for p in products]


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: str):
    """Get product by ID"""
    try:
        product = get_collection("products").find_one({"_id": ObjectId(product_id)})
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid product ID")
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return ProductResponse(**_normalize_product_doc(product))


@router.get("/barcode/{barcode}", response_model=ProductResponse)
async def get_product_by_barcode(barcode: str):
    """Get product by barcode"""
    product = get_collection("products").find_one({"barcode": barcode})
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return ProductResponse(**_normalize_product_doc(product))
