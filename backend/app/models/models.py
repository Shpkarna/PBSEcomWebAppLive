"""Database models for the e-commerce application."""
from datetime import datetime
from typing import List
from app.models.enums import UserRole, PaymentMethod, OrderStatus  # noqa: F401


class User:
    def __init__(self, username: str, email: str, password_hash: str,
                 role: UserRole = UserRole.CUSTOMER, full_name: str = "",
                 phone: str = "", address: str = "", is_active: bool = True,
                 dob: str = "", sex: str = "", marital_status: str = "",
                 phone_verified: bool = False, email_verified: bool = False):
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.role = role
        self.full_name = full_name
        self.phone = phone
        self.address = address
        self.is_active = is_active
        self.dob = dob  # Date of birth (YYYY-MM-DD format)
        self.sex = sex  # M/F/Other
        self.marital_status = marital_status  # Single/Married/Divorced/Widowed
        self.phone_verified = phone_verified  # Phone number verified via OTP
        self.email_verified = email_verified  # Email verified via verification link
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()


class Product:
    def __init__(self, name: str, sku: str, barcode: str, stock_price: float,
                 sell_price: float, description: str = "", category: str = "",
                 stock_quantity: int = 0, gst_rate: float = 0.18):
        self.name = name
        self.sku = sku
        self.barcode = barcode
        self.stock_price = stock_price
        self.sell_price = sell_price
        self.description = description
        self.category = category
        self.stock_quantity = stock_quantity
        self.gst_rate = gst_rate
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()


class StockLedger:
    def __init__(self, product_id: str, transaction_type: str, quantity: int,
                 reference: str = "", notes: str = ""):
        self.product_id = product_id
        self.transaction_type = transaction_type
        self.quantity = quantity
        self.reference = reference
        self.notes = notes
        self.created_at = datetime.utcnow()


class CartItem:
    def __init__(self, product_id: str, quantity: int, price: float):
        self.product_id = product_id
        self.quantity = quantity
        self.price = price
        self.gst_amount = 0
        self.total = quantity * price


class OrderItem:
    def __init__(self, product_id: str, product_name: str, quantity: int,
                 stock_price: float, sell_price: float, gst_rate: float):
        self.product_id = product_id
        self.product_name = product_name
        self.quantity = quantity
        self.stock_price = stock_price
        self.sell_price = sell_price
        self.gst_rate = gst_rate
        self.gst_amount = sell_price * quantity * gst_rate
        self.total = (sell_price * quantity) + self.gst_amount


class Order:
    def __init__(self, customer_id: str, items: List[OrderItem],
                 payment_method: PaymentMethod, shipping_address: str,
                 order_number: str = ""):
        self.customer_id = customer_id
        self.items = items
        self.payment_method = payment_method
        self.shipping_address = shipping_address
        self.order_number = order_number
        self.subtotal = sum(item.sell_price * item.quantity for item in items)
        self.total_gst = sum(item.gst_amount for item in items)
        self.total = self.subtotal + self.total_gst
        self.status = OrderStatus.PENDING
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()


class SavedProduct:
    def __init__(self, customer_id: str, product_id: str, saved_price: float):
        self.customer_id = customer_id
        self.product_id = product_id
        self.saved_price = saved_price
        self.created_at = datetime.utcnow()
