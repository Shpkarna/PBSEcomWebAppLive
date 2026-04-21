"""Canonical domain entities for Phase 1 model-layer extraction.

These entities are storage-agnostic and avoid database-specific constructs.
All monetary fields follow the canonical 2-decimal-place precision rule.
All datetime fields are UTC-naive; see domain.conventions for the full policy.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Literal

from app.models.enums import OrderStatus, PaymentMethod, UserRole


SexType = Literal["M", "F", "Other", ""]
MaritalStatusType = Literal["Single", "Married", "Divorced", "Widowed", ""]
ProductDiscount = Literal["Discount percentage", "Discount amount", ""]
ProductDiscountType = Literal["per quantity", "Total quantity", "Category", ""]


@dataclass(slots=True)
class Address:
    street1: Optional[str] = None
    street2: Optional[str] = None
    landmark: Optional[str] = None
    district: Optional[str] = None
    area: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    pincode: Optional[str] = None
    phone: Optional[str] = None


@dataclass(slots=True)
class SavedPayment:
    card_holder: Optional[str] = None
    card_last4: Optional[str] = None
    card_brand: Optional[str] = None
    expiry_month: Optional[int] = None
    expiry_year: Optional[int] = None
    upi_id: Optional[str] = None


@dataclass(slots=True)
class UserEntity:
    username: str
    email: Optional[str]
    password_hash: str
    role: UserRole = UserRole.CUSTOMER
    full_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    dob: Optional[str] = None
    sex: SexType = ""
    marital_status: MaritalStatusType = ""
    address_data: Optional[Address] = None
    saved_payment_data: Optional[SavedPayment] = None
    phone_verified: bool = False
    email_verified: bool = False
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    id: Optional[str] = None


@dataclass(slots=True)
class ProductEntity:
    name: str
    sku: str
    barcode: str
    stock_price: float
    sell_price: float
    description: Optional[str] = None
    category: Optional[str] = None
    discount: ProductDiscount = ""
    discount_value: Optional[float] = None
    discount_type: ProductDiscountType = ""
    stock_quantity: int = 0
    gst_rate: float = 0.18
    image_media_ids: list[str] = field(default_factory=list)
    video_media_ids: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    id: Optional[str] = None


@dataclass(slots=True)
class CartItemEntity:
    product_id: str
    quantity: int
    price: float
    product_name: str = ""
    product_spec: str = ""
    line_subtotal: float = 0.0
    discount_amount: float = 0.0
    taxable_amount: float = 0.0
    gst_amount: float = 0.0
    total: float = 0.0


@dataclass(slots=True)
class ShippingAddress:
    street1: str
    landmark: str
    district: str
    state: str
    country: str
    pincode: str
    phone: str
    street2: Optional[str] = None
    area: Optional[str] = None


@dataclass(slots=True)
class OrderItemEntity:
    product_id: str
    product_name: str
    quantity: int
    sell_price: float
    line_subtotal: float
    discount_amount: float
    taxable_amount: float
    gst_amount: float
    total: float


@dataclass(slots=True)
class OrderEntity:
    customer_id: str
    items: list[OrderItemEntity]
    payment_method: PaymentMethod
    shipping_address: Optional[ShippingAddress] = None
    order_number: str = ""
    cart_quote_id: Optional[str] = None
    subtotal: float = 0.0
    total_discount: float = 0.0
    total_gst: float = 0.0
    total: float = 0.0
    status: OrderStatus = OrderStatus.PENDING
    shipment_date: Optional[str] = None
    return_reason: Optional[str] = None
    exchange_order_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    id: Optional[str] = None


# ── Phase 1 Step 2 additions: Reports / Logs / Data-sync aggregates ──────────

ContactInquiryStatus = Literal["new", "in_progress", "resolved", "closed"]
StockTransactionType = Literal["inbound", "outbound", "adjustment"]
LedgerTransactionType = Literal["credit", "debit"]


@dataclass(slots=True)
class SavedProductEntity:
    customer_id: str
    product_id: str
    saved_price: float  # 2 decimal places — snapshot of sell_price at save time
    created_at: datetime = field(default_factory=datetime.utcnow)
    id: Optional[str] = None


@dataclass(slots=True)
class CategoryEntity:
    name: str
    description: Optional[str] = None
    discount_type: Optional[str] = None   # "Discount percentage" | "Discount amount"
    discount_value: Optional[float] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    id: Optional[str] = None


@dataclass(slots=True)
class VendorEntity:
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    gst_number: Optional[str] = None
    bank_details: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    id: Optional[str] = None


@dataclass(slots=True)
class ContactInquiryEntity:
    name: str
    email: str
    subject: str
    message: str
    status: ContactInquiryStatus = "new"
    admin_notes: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    id: Optional[str] = None


@dataclass(slots=True)
class StockLedgerEntity:
    product_id: str
    transaction_type: StockTransactionType
    quantity: int  # non-zero; positive = in, negative allowed for adjustment
    reference: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    id: Optional[str] = None


@dataclass(slots=True)
class LedgerEntryEntity:
    transaction_type: LedgerTransactionType
    category: str
    amount: float  # 2 decimal places; gt=0
    reference_id: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    id: Optional[str] = None


@dataclass(slots=True)
class AuditLogEntity:
    action: str
    user: str = "anonymous"
    path: str = ""
    details: dict = field(default_factory=dict)
    immutable: bool = True  # insert-only; never updated or deleted
    created_at: datetime = field(default_factory=datetime.utcnow)
    id: Optional[str] = None


@dataclass(slots=True)
class SessionEntity:
    username: str
    client_ip: str
    client_mac: str
    session_token: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    id: Optional[str] = None
