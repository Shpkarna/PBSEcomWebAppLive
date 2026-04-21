"""
Sample data for all master and transaction collections.
FOR DEVELOPMENT/TESTING ONLY — never load in production.
"""
from datetime import datetime

SAMPLE_CATEGORIES = [
    {"name": "Electronics", "description": "Electronic devices and accessories"},
    {"name": "Clothing", "description": "Apparel and fashion items"},
    {"name": "Groceries", "description": "Food and daily essentials"},
    {"name": "Books", "description": "Books, e-books, and stationery"},
    {"name": "Home & Kitchen", "description": "Household and kitchen items"},
]

SAMPLE_VENDORS = [
    {
        "name": "TechSupply Co", "email": "contact@techsupply.example",
        "phone": "9876543210", "address": "12 Tech Park, Bengaluru",
        "gst_number": "29AABCT1332L1ZV", "bank_details": "HDFC Bank - 1234567890",
    },
    {
        "name": "Fabric World", "email": "info@fabricworld.example",
        "phone": "9811122233", "address": "45 Textile Hub, Surat",
        "gst_number": "24AAACF1234M1ZX", "bank_details": "SBI - 9876543210",
    },
    {
        "name": "FreshFarm", "email": "supply@freshfarm.example",
        "phone": "9700001122", "address": "Village Road, Nashik",
        "gst_number": "27AAACG5678N1ZP", "bank_details": "Axis Bank - 1122334455",
    },
]

SAMPLE_USERS = [
    {
        "username": "customer1", "email": "customer1@example.com",
        "full_name": "Ravi Kumar", "phone": "9123456780",
        "address": "101 Main St, Mumbai", "role": "customer", "is_active": True,
    },
    {
        "username": "vendor1", "email": "vendor1@example.com",
        "full_name": "Priya Sharma", "phone": "9234567891",
        "address": "22 Market Lane, Delhi", "role": "vendor", "is_active": True,
    },
    {
        "username": "bizuser1", "email": "bizuser1@example.com",
        "full_name": "Arjun Patel", "phone": "9345678902",
        "address": "5 Business Park, Chennai", "role": "business", "is_active": True,
    },
]

SAMPLE_PRODUCTS = [
    {
        "name": "Wireless Headphones", "sku": "ELEC-001", "barcode": "8901234567890",
        "stock_price": 800.0, "sell_price": 1299.0, "description": "Bluetooth over-ear headphones",
        "category": "Electronics", "stock_quantity": 50, "gst_rate": 0.18,
    },
    {
        "name": "Cotton T-Shirt", "sku": "CLTH-001", "barcode": "8901234567891",
        "stock_price": 150.0, "sell_price": 349.0, "description": "100% cotton round-neck t-shirt",
        "category": "Clothing", "stock_quantity": 200, "gst_rate": 0.05,
    },
    {
        "name": "Basmati Rice 5kg", "sku": "GROC-001", "barcode": "8901234567892",
        "stock_price": 280.0, "sell_price": 399.0, "description": "Premium long-grain basmati rice",
        "category": "Groceries", "stock_quantity": 100, "gst_rate": 0.05,
    },
    {
        "name": "Python Programming Book", "sku": "BOOK-001", "barcode": "8901234567893",
        "stock_price": 300.0, "sell_price": 499.0, "description": "Learn Python from scratch",
        "category": "Books", "stock_quantity": 75, "gst_rate": 0.12,
    },
    {
        "name": "Non-stick Frying Pan", "sku": "HOME-001", "barcode": "8901234567894",
        "stock_price": 450.0, "sell_price": 799.0, "description": "24cm aluminum frying pan",
        "category": "Home & Kitchen", "stock_quantity": 60, "gst_rate": 0.18,
    },
]

SAMPLE_ORDERS = [
    {
        "order_number": "ORD-SAMPLE-001",
        "items": [
            {
                "product_name": "Wireless Headphones", "quantity": 1,
                "sell_price": 1299.0, "gst_rate": 0.18,
                "gst_amount": 233.82, "total": 1532.82,
            }
        ],
        "subtotal": 1299.0, "total_gst": 233.82, "total": 1532.82,
        "payment_method": "upi", "status": "delivered",
        "shipping_address": {
            "street1": "101 Main St", "street2": "", "landmark": "Near City Mall",
            "district": "Mumbai", "area": "Andheri", "state": "Maharashtra",
            "country": "India", "pincode": "400001", "phone": "9123456780",
        },
    },
]

SAMPLE_CART_ITEMS = [
    {"product_sku": "CLTH-001", "quantity": 2},
    {"product_sku": "GROC-001", "quantity": 1},
]

SAMPLE_SAVED_PRODUCTS = [
    {"product_sku": "BOOK-001"},
]

SAMPLE_STOCK_LEDGER = [
    {"product_sku": "ELEC-001", "transaction_type": "inbound", "quantity": 50,
     "reference": "Initial stock", "notes": "Sample initial inbound"},
    {"product_sku": "CLTH-001", "transaction_type": "inbound", "quantity": 200,
     "reference": "Initial stock", "notes": "Sample initial inbound"},
    {"product_sku": "ELEC-001", "transaction_type": "outbound", "quantity": 1,
     "reference": "Order ORD-SAMPLE-001", "notes": "Sample sale"},
]

SAMPLE_LEDGER = [
    {"transaction_type": "credit", "category": "sales", "amount": 1532.82,
     "reference_id": "ORD-SAMPLE-001", "notes": "Sale to customer1"},
]

SAMPLE_CONTACT_INQUIRIES = [
    {"name": "Test User", "email": "test@example.com",
     "subject": "Return policy query", "message": "What is the return window?"},
]

SAMPLE_USER_ROLE_MAPPINGS = [
    {"username": "customer1", "role": "customer"},
    {"username": "vendor1", "role": "vendor"},
    {"username": "bizuser1", "role": "business"},
]

SAMPLE_ROLE_FUNCTIONALITY_MAPPINGS = [
    {"role": "customer", "functionality_code": "customer_purchase"},
    {"role": "business", "functionality_code": "inventory_manage"},
    {"role": "vendor", "functionality_code": "inventory_manage"},
]


def get_now():
    return datetime.utcnow()
