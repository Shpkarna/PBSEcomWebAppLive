"""Cart API routes"""
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPAuthorizationCredentials
from app.data.repository_providers import get_order_cart_repository
from app.schemas.schemas import CartItemRequest, CartResponse
from app.services.cart_service import CartService
from app.utils.security import decode_token, get_token_from_credentials, security

router = APIRouter(prefix="/api/cart", tags=["Cart"])


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = get_token_from_credentials(credentials)
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    username = payload.get("sub")
    session_id = payload.get("sid")
    if not username or not session_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims")
    return {"username": username, "session_id": session_id}


@router.post("/add")
async def add_to_cart(
    item: CartItemRequest,
    current_user: dict = Depends(get_current_user),
    repo=Depends(get_order_cart_repository),
):
    """Add item to cart"""
    service = CartService(repo)
    return service.add_to_cart(current_user["username"], current_user["session_id"], item)


@router.get("/", response_model=CartResponse)
async def get_cart(
    current_user: dict = Depends(get_current_user),
    repo=Depends(get_order_cart_repository),
):
    """Get user's cart for the current session"""
    service = CartService(repo)
    return service.get_cart(current_user["username"], current_user["session_id"])


@router.delete("/item/{product_id}")
async def remove_from_cart(
    product_id: str,
    current_user: dict = Depends(get_current_user),
    repo=Depends(get_order_cart_repository),
):
    """Remove item from cart"""
    service = CartService(repo)
    return service.remove_from_cart(current_user["username"], current_user["session_id"], product_id)


@router.delete("/")
async def clear_cart(
    current_user: dict = Depends(get_current_user),
    repo=Depends(get_order_cart_repository),
):
    """Clear user's cart for the current session"""
    service = CartService(repo)
    return service.clear_cart(current_user["username"], current_user["session_id"])
