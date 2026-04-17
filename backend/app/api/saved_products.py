"""Saved Products (Save for Later) API routes"""
from fastapi import APIRouter, HTTPException, status, Depends
from app.database import get_collection
from app.schemas.schemas import SaveProductRequest, SavedProductResponse
from app.utils.security import decode_token, get_token_from_credentials, security
from fastapi.security import HTTPAuthorizationCredentials
from bson import ObjectId
from datetime import datetime

router = APIRouter(prefix="/api/cart/saved", tags=["Saved Products"])


def _get_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = get_token_from_credentials(credentials)
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return payload.get("sub")


@router.post("/add", response_model=SavedProductResponse)
async def save_product(request: SaveProductRequest, current_user: str = Depends(_get_user)):
    """Save product for later"""
    users_col = get_collection("users")
    products_col = get_collection("products")
    saved_col = get_collection("saved_products")

    user = users_col.find_one({"username": current_user})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    try:
        product_oid = ObjectId(request.product_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid product ID")

    product = products_col.find_one({"_id": product_oid})
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    user_id = str(user["_id"])
    if saved_col.find_one({"customer_id": user_id, "product_id": request.product_id}):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Product already in saved list")

    saved_product = {
        "customer_id": user_id,
        "product_id": request.product_id,
        "saved_price": product["sell_price"],
        "created_at": datetime.utcnow(),
    }
    result = saved_col.insert_one(saved_product)
    saved_product["_id"] = result.inserted_id
    return SavedProductResponse(**saved_product)


@router.get("/")
async def get_saved_products(current_user: str = Depends(_get_user)):
    """Get user's saved products"""
    users_col = get_collection("users")
    saved_col = get_collection("saved_products")
    products_col = get_collection("products")

    user = users_col.find_one({"username": current_user})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    saved_items = list(saved_col.find({"customer_id": str(user["_id"])}))
    result = []
    for item in saved_items:
        try:
            product = products_col.find_one({"_id": ObjectId(item["product_id"])})
            if product:
                product["_id"] = str(product["_id"])
                result.append({
                    "saved_product": SavedProductResponse(**item),
                    "product": product,
                    "available": product.get("stock_quantity", 0) > 0,
                })
        except Exception:
            pass
    return result


@router.delete("/{product_id}")
async def remove_saved_product(product_id: str, current_user: str = Depends(_get_user)):
    """Remove product from saved list"""
    users_col = get_collection("users")
    saved_col = get_collection("saved_products")

    user = users_col.find_one({"username": current_user})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    result = saved_col.delete_one({"customer_id": str(user["_id"]), "product_id": product_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Saved product not found")
    return {"message": "Saved product removed"}
