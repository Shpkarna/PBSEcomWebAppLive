# Testing Quick Start

## 1) Start Backend (port 7999)
cd c:\Users\admin\OneDrive\Documents\AI_ECom_site\backend
python -m uvicorn app.main:app --reload --port 7999

## 2) Start Frontend (port 3000)
cd c:\Users\admin\OneDrive\Documents\AI_ECom_site\frontend
npm run build
npx http-server dist -p 3000

## 3) Run Centralized Tests (from repo root)
cd c:\Users\admin\OneDrive\Documents\AI_ECom_site
python run_tests.py

## What this runs
- test_suit/backend/test_backend.py
- test_suit/frontend/test_frontend.js
- test_suit/frontend/tests/ui-tests.spec.ts (Playwright)
- test_suit/integration/test_integration.py

## Where artifacts are stored
- test_suit/frontend/test_results/
- test_suit/artifacts/logs/
