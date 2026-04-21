"""Cart, order, and saved product Pydantic schemas."""
from pydantic import BaseModel, Field
from typing import Optional, List, Union
from datetime import datetime
from app.schemas import PyObjectId


class CartItemRequest(BaseModel):
    product_id: str
    quantity: int = Field(..., gt=0)


class CartItem(BaseModel):
    product_id: str
    product_name: str = ""
    product_spec: str = ""
    quantity: int
    price: float
    line_subtotal: float = 0.0
    discount_amount: float = 0.0
    taxable_amount: float = 0.0
    gst_amount: float = 0.0
    total: float


class CartResponse(BaseModel):
    items: List[CartItem]
    cart_quote_id: Optional[str] = None
    subtotal: float
    total_discount: float = 0.0
    total_gst: float
    total: float


class OrderItemRequest(BaseModel):
    product_id: str
    quantity: int = Field(..., gt=0)


class OrderItemResponse(BaseModel):
    product_id: str = ""
    product_name: str = ""
    quantity: int = 0
    sell_price: float = 0.0
    line_subtotal: float = 0.0
    discount_amount: float = 0.0
    taxable_amount: float = 0.0
    gst_amount: float = 0.0
    total: float = 0.0


class ShippingAddress(BaseModel):
    street1: str = Field(..., min_length=1)
    street2: Optional[str] = None
    landmark: str = Field(..., min_length=1)
    district: str = Field(..., min_length=1)
    area: Optional[str] = None
    state: str = Field(..., min_length=1)
    country: str = Field(..., min_length=1)
    pincode: str = Field(..., min_length=1)
    phone: str = Field(..., min_length=1)


class OrderRequest(BaseModel):
    items: List[OrderItemRequest]
    payment_method: str = Field(..., pattern="^(cod|netbanking|upi|card)$")
    shipping_address: ShippingAddress
    shipment_date: Optional[str] = None
    cart_quote_id: Optional[str] = None
    razorpay_order_id: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
    razorpay_signature: Optional[str] = None


class RazorpayOrderCreateRequest(BaseModel):
    items: List[OrderItemRequest]
    payment_method: str = Field(..., pattern="^(netbanking|upi|card)$")
    shipping_address: ShippingAddress
    shipment_date: Optional[str] = None
    cart_quote_id: Optional[str] = None


class RazorpayOrderCreateResponse(BaseModel):
    key_id: str
    razorpay_order_id: str
    amount: int
    currency: str
    receipt: str
    total: float
    subtotal: float
    total_gst: float
    total_discount: float


class RazorpayKeyConfigResponse(BaseModel):
    """Public Razorpay config — key_id only (never exposes key_secret)."""
    key_id: str


class OrderResponse(BaseModel):
    id: PyObjectId = Field(alias="_id")
    customer_id: str
    order_number: str
    cart_quote_id: Optional[str] = None
    items: List[OrderItemResponse]
    subtotal: float
    total_discount: float = 0.0
    total_gst: float
    total: float
    payment_method: str
    shipping_address: Optional[Union[dict, str]] = None
    shipment_date: Optional[str] = None
    status: str
    return_reason: Optional[str] = None
    exchange_order_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True


class ReturnRequest(BaseModel):
    reason: str = Field(..., min_length=5, max_length=500)


class ExchangeRequest(BaseModel):
    reason: str = Field(..., min_length=5, max_length=500)
    new_product_id: str
    quantity: int = Field(1, gt=0)


class SaveProductRequest(BaseModel):
    product_id: str


class SavedProductResponse(BaseModel):
    id: PyObjectId = Field(alias="_id")
    customer_id: str
    product_id: str
    saved_price: float
    created_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True
