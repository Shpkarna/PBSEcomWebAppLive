"""Saved Products (Save for Later) API routes"""
from fastapi import APIRouter, HTTPException, status, Depends
from app.data.repository_providers import get_order_cart_repository
from app.domain.contracts.order_cart_repository import OrderCartRepository
from app.schemas.schemas import SaveProductRequest, SavedProductResponse
from app.utils.security import decode_token, get_token_from_credentials, security
from fastapi.security import HTTPAuthorizationCredentials
from datetime import datetime

router = APIRouter(prefix="/api/cart/saved", tags=["Saved Products"])


def _get_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = get_token_from_credentials(credentials)
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return payload.get("sub")


@router.post("/add", response_model=SavedProductResponse)
async def save_product(
    request: SaveProductRequest,
    current_user: str = Depends(_get_user),
    repo: OrderCartRepository = Depends(get_order_cart_repository),
):
    """Save product for later"""
    user = repo.find_user_by_username(current_user)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    product = repo.find_product_by_id(request.product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    user_id = str(user["_id"])
    if repo.find_saved_product(user_id, request.product_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Product already in saved list")

    saved_product = {
        "customer_id": user_id,
        "product_id": request.product_id,
        "saved_price": product["sell_price"],
        "created_at": datetime.utcnow(),
    }
    stored = repo.create_saved_product(saved_product)
    return SavedProductResponse(**stored)


@router.get("/")
async def get_saved_products(
    current_user: str = Depends(_get_user),
    repo: OrderCartRepository = Depends(get_order_cart_repository),
):
    """Get user's saved products"""
    user = repo.find_user_by_username(current_user)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user_id = str(user["_id"])
    saved_items = repo.list_saved_products_for_user(user_id)
    result = []
    for item in saved_items:
        product = repo.find_product_by_id(item["product_id"])
        if product:
            product["_id"] = str(product["_id"])
            result.append({
                "saved_product": SavedProductResponse(**item),
                "product": product,
                "available": product.get("stock_quantity", 0) > 0,
            })
    return result


@router.delete("/{product_id}")
async def remove_saved_product(
    product_id: str,
    current_user: str = Depends(_get_user),
    repo: OrderCartRepository = Depends(get_order_cart_repository),
):
    """Remove product from saved list"""
    user = repo.find_user_by_username(current_user)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user_id = str(user["_id"])
    if repo.delete_saved_product(user_id, product_id) == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Saved product not found")
    return {"message": "Saved product removed"}
