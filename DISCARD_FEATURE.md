# Discard Sample Data Feature

## Overview
The **Discard Sample Data** feature provides a comprehensive data reset mechanism for development and testing environments. It clears all transaction and master data while preserving the admin user account.

## Features

### What Gets Cleared
The discard operation systematically clears the following data categories:

#### Transaction Collections (Cleared)
- `orders` - All sales and exchange orders
- `order_items` - Individual items in orders
- `payments` - Payment records
- `invoices` - Invoice records
- `carts` - Shopping cart data
- `contact_inquiries` - Contact form submissions
- `saved_products` - User saved product lists

#### Master Data (Cleared)
- `products` - All product catalog entries
- `categories` - Product categories
- `vendors` - Vendor/supplier information

#### Ledger & Session Data (Cleared)
- `stock_ledger` - Stock transaction history
- `financial_ledger` - Financial transaction records
- `ledger` - General ledger entries
- `sessions` - User session tokens
- `counters` - ID generation sequence counters

#### User & Permission Data (Cleared - Except Admin)
- `users` - All user accounts **EXCEPT the admin user**
- `user_role_mappings` - Role assignments for non-admin users
- `role_permissions` - Role permission definitions
- `role_functionality_mappings` - Functionality access mappings
- `company_assets` - Company asset records

### What Gets Preserved
- **Admin User Account** - The configured admin user (default: `admin`) is always preserved
- **Admin Credentials** - Admin login credentials remain unchanged

## API Endpoint

### POST `/api/admin/discard-sample-data`

**Authentication Required:** Yes (Admin only)

**Request Headers:**
```
Authorization: Bearer <admin_jwt_token>
```

**Response (Success - 200):**
```json
{
  "message": "All sample data discarded. Admin user preserved. Total records deleted: 258",
  "deleted": {
    "orders": 10,
    "users": 37,
    "products": 5,
    "categories": 5,
    "vendors": 3,
    "stock_ledger": 26,
    "sessions": 136,
    ...
  },
  "preserved_admin": "admin"
}
```

**Error Responses:**
- `403 Forbidden` - If called in production mode (`package_option != "dev"`)
- `401 Unauthorized` - If not authenticated as admin

## Usage Example

### Step 1: Authenticate as Admin
```bash
curl -X POST http://localhost:7999/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Qsrt#09-MWQ"}'
```

Response includes `access_token`.

### Step 2: Call Discard Endpoint
```bash
curl -X POST http://localhost:7999/api/admin/discard-sample-data \
  -H "Authorization: Bearer <access_token>"
```

## Important Notes

### Environment Restrictions
- **Development/Test Only**: This endpoint is disabled in production mode
- Protection: Environment variable `package_option` must be set to a value other than `"prod"`
- If you attempt to call this in production, you'll get: `"Sample data tools are disabled in production"`

### What Happens to Sample Index
- If a `sample_index.json` file exists (from previous `load-sample-data` calls), it is automatically deleted
- This allows a clean reload of sample data if needed

### Atomic Operation
- The discard operation clears collections sequentially
- If an error occurs during the operation, some collections may already be cleared
- The admin user is always processed last to minimize risk of being accidentally deleted

### ID Counter Reset
- The `counters` collection is completely cleared
- After discard, the next call to `load-sample-data` or any ID generation will start fresh counters
- Example: After discard, next order will be `SO-2026-1000001` (reset counter)

## Use Cases

### 1. Reset for Fresh Testing
```
1. Load sample data
2. Run tests
3. Discard all sample data
4. Load fresh sample data
5. Run tests again
```

### 2. Clean Up Before Deployment
```
1. Run full test suite with sample data
2. Discard sample data
3. Deploy to staging with clean database
```

### 3. Development Workflow Cleanup
```
1. Develop with sample data
2. Test changes
3. Discard to reset state
4. Restart development cycle
```

## Testing

A comprehensive discard operation test was performed:

**Test Results:**
- ✓ Sample data loaded (12 initial records)
- ✓ Discard operation completed successfully
- ✓ 258 records deleted across 16 collections
- ✓ Admin user preserved
- ✓ Admin can still login with original credentials
- ✓ DB is in clean state for next cycle

**Sample Output:**
```
Deleted records by collection:
  - cart: 5
  - categories: 5
  - company_assets: 1
  - contact_inquiries: 3
  - counters: 2
  - ledger: 11
  - orders: 10
  - products: 5
  - role_functionality_mappings: 3
  - role_permissions: 3
  - saved_products: 4
  - sessions: 136
  - stock_ledger: 26
  - user_role_mappings: 4
  - users: 37
  - vendors: 3
```

## Technical Implementation

### File Modified
- **Backend:** `backend/app/api/admin.py`

### Changes Made
- Updated `POST /api/admin/discard-sample-data` endpoint
- Implementation now performs systematic collection cleanup instead of index-based deletion
- Admin user is specifically preserved using query filter `{"username": {"$ne": settings.admin_username}}`
- Counters collection is cleared for fresh ID generation sequences
- Sample index file is automatically deleted

### Benefits of This Approach
1. **Complete Reset**: No orphaned data left in any collection
2. **Admin Safety**: Admin account always preserved
3. **ID Generator Compatible**: Counters reset allows clean ID generation from starting sequence
4. **Production-Safe**: Environment check prevents accidental data loss in production
5. **Transparent**: Returns detailed breakdown of deleted records per collection

## Related Endpoints

- `POST /api/admin/load-sample-data` - Load sample data (requires admin)
- `POST /api/auth/login` - Authenticate as admin
