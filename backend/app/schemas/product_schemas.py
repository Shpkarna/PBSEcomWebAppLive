"""Product and stock ledger Pydantic schemas."""
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
from app.schemas import PyObjectId


ProductDiscount = Literal["Discount percentage", "Discount amount"]
ProductDiscountType = Literal["per quantity", "Total quantity", "Category"]


class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    sku: str = Field(..., min_length=1, max_length=50)
    barcode: str = Field(..., min_length=1, max_length=100)
    stock_price: float = Field(..., gt=0)
    sell_price: float = Field(..., gt=0)
    description: Optional[str] = None
    category: Optional[str] = None
    discount: Optional[ProductDiscount] = None
    discount_value: Optional[float] = Field(default=None, ge=0)
    discount_type: Optional[ProductDiscountType] = None
    stock_quantity: int = Field(default=0, ge=0)
    gst_rate: float = Field(default=0.18, ge=0, le=1)


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    sku: Optional[str] = None
    barcode: Optional[str] = None
    stock_price: Optional[float] = None
    sell_price: Optional[float] = None
    description: Optional[str] = None
    category: Optional[str] = None
    discount: Optional[ProductDiscount] = None
    discount_value: Optional[float] = Field(default=None, ge=0)
    discount_type: Optional[ProductDiscountType] = None
    stock_quantity: Optional[int] = None
    gst_rate: Optional[float] = None


class ProductResponse(ProductBase):
    id: PyObjectId = Field(alias="_id")
    image_media_ids: list[str] = Field(default_factory=list)
    video_media_ids: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True


class StockLedgerBase(BaseModel):
    product_id: str
    transaction_type: str = Field(..., pattern="^(inbound|outbound|adjustment)$")
    quantity: int = Field(..., ne=0)
    reference: Optional[str] = None
    notes: Optional[str] = None


class StockLedgerResponse(StockLedgerBase):
    id: PyObjectId = Field(alias="_id")
    created_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True


class LedgerEntryBase(BaseModel):
    transaction_type: str = Field(..., pattern="^(credit|debit)$")
    category: str
    amount: float = Field(..., gt=0)
    reference_id: Optional[str] = None
    notes: Optional[str] = None


class LedgerEntryResponse(LedgerEntryBase):
    id: PyObjectId = Field(alias="_id")
    created_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True
