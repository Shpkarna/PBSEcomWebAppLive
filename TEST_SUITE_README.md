# E-Commerce Platform - Test Suite Documentation

## Strategy
Testing is centralized in test_suit. All test execution and artifact generation is routed through test_suit.

## Entrypoint
- python run_tests.py
- Delegates to: test_suit/run_tests.py

## Test scripts
- Backend: test_suit/backend/test_backend.py
- Frontend URL: test_suit/frontend/test_frontend.js
- Frontend UI: test_suit/frontend/tests/ui-tests.spec.ts
- Integration: test_suit/integration/test_integration.py

## Artifact policy
- Frontend artifacts: test_suit/frontend/test_results/
- Master logs: test_suit/artifacts/logs/
- Normalized naming: test_results (do not use test-result, test_result, or test-results)

## Required servers
- Backend API: http://localhost:7999
- Frontend: http://localhost:3000
