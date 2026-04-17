"""
Main FastAPI application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import close_mongo_connection
from app.config import settings
from app.init_db import initialize_databases
from app.utils.rbac import ensure_default_role_mappings

# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    description=settings.api_description,
    version=settings.api_version,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Ensure initialization of the application database and default admin on startup."""
    try:
        initialize_databases()
        ensure_default_role_mappings()
        from app.api.payment_gateways import load_gateway_settings_into_config
        load_gateway_settings_into_config()
        from app.api.company_config import load_company_config_into_settings
        load_company_config_into_settings()
        from app.services.cart_cleanup import start_cart_cleanup_task
        start_cart_cleanup_task()
        print("Application started and databases initialized")
    except Exception as error:
        print(f"Application startup failed: {error}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection on shutdown"""
    close_mongo_connection()
    print("Application shutdown")


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "app": settings.api_title}


@app.get("/api/config/package-option")
async def get_package_option():
    """Return current package option (sandbox/trial/prod)."""
    return {"package_option": settings.package_option}


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to E-Commerce API",
        "version": settings.api_version,
        "docs": "/docs"
    }


# Include routers
from app.api import auth, products, product_manage, order_create, orders
from app.api import cart, saved_products, logs
from app.api import ledger, report_sales, report_stats
from app.api import rbac_roles, rbac_users
from app.api import admin, admin_users, admin_orders, categories, vendors, stock, contact
from app.api import brand
from app.api import payment_gateways
from app.api import company_config
from app.api import data_sync

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(product_manage.router)
app.include_router(order_create.router)
app.include_router(orders.router)
app.include_router(cart.router)
app.include_router(saved_products.router)
app.include_router(ledger.router)
app.include_router(report_sales.router)
app.include_router(report_stats.router)
app.include_router(logs.router)
app.include_router(rbac_roles.router)
app.include_router(rbac_users.router)
app.include_router(admin.router)
app.include_router(admin_users.router)
app.include_router(admin_orders.router)
app.include_router(categories.router)
app.include_router(vendors.router)
app.include_router(stock.router)
app.include_router(contact.router)
app.include_router(brand.router)
app.include_router(payment_gateways.router)
app.include_router(company_config.router)
app.include_router(company_config.public_router)
app.include_router(data_sync.admin_router)
app.include_router(data_sync.public_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
