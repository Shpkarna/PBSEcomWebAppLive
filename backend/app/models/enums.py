"""Enum definitions for models."""
from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    BUSINESS = "business"
    USER = "user"
    CUSTOMER = "customer"
    VENDOR = "vendor"


class PaymentMethod(str, Enum):
    CASH = "cash"
    COD = "cod"
    NETBANKING = "netbanking"
    UPI = "upi"
    CARD = "card"


class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    RETURN_REQUESTED = "return_requested"
    RETURNED = "returned"
