# Dependency Snapshot Report

Date: 2026-04-03
Repository: econsite
Workspace: AI_ECom_site

## Scope
This report captures dependency and toolchain versions before and after the latest upgrade work, using:
- before state from Git HEAD manifests
- after state from current workspace manifests and installed environment

## Toolchain Snapshot
### Current (after)
- Python: 3.14.3
- pip: 26.0.1
- Node.js: v24.14.1
- npm: 11.11.0

### Before
- Python and pip before values were not pinned in repository manifests.
- npm and Node before values were not pinned in repository manifests.

## Python Dependencies (Backend)
Source files:
- before: backend/requirements.txt from Git HEAD
- after: backend/requirements.txt in workspace

| Package | Before | After | Change |
|---|---:|---:|---|
| fastapi | 0.68.1 | 0.135.3 | upgraded |
| uvicorn[standard] | 0.15.0 | 0.42.0 | upgraded |
| pymongo | 4.6.0 | 4.16.0 | upgraded |
| pydantic | 1.10.13 | 2.12.5 | upgraded (major) |
| pydantic-settings | not present | 2.13.1 | added |
| python-jose[cryptography] | 3.3.0 | 3.5.0 | upgraded |
| passlib[bcrypt] | 1.7.4 | 1.7.4 | unchanged |
| python-multipart | 0.0.5 | 0.0.22 | upgraded |
| python-dotenv | 0.19.2 | 1.2.2 | upgraded |
| requests | 2.28.2 | 2.33.1 | upgraded |
| email-validator | not present | 2.3.0 | added |

## npm Dependencies
### Root package.json
| Package | Before | After | Change |
|---|---:|---:|---|
| webpack-cli | ^7.0.2 | ^7.0.2 | unchanged |
| webpack-dev-server | ^5.2.3 | ^5.2.3 | unchanged |

Resolved installed versions (after):
- webpack-cli: 7.0.2
- webpack-dev-server: 5.2.3

### Frontend package.json
| Package | Before | After | Change |
|---|---:|---:|---|
| webpack-dev-server | ^4.15.2 | ^5.2.3 | upgraded (major) |
| webpack | ^5.89.0 | ^5.89.0 | range unchanged |
| webpack-cli | ^5.1.0 | ^5.1.0 | range unchanged |
| ts-loader | ^9.5.0 | ^9.5.0 | range unchanged |

Resolved installed versions (after):
- webpack-dev-server: 5.2.3
- webpack: 5.105.4
- webpack-cli: 5.1.4
- ts-loader: 9.5.7

Notes:
- npm audit fix --force upgraded frontend transitive packages and removed all reported npm vulnerabilities at time of run.
- Frontend lockfile and root lockfile were updated accordingly.

## Compatibility/Maintenance Notes
- Backend was migrated to support the upgraded Python stack with Pydantic v2.
- Settings handling now uses pydantic-settings.
- EmailStr validation requires email-validator, now explicitly pinned.
- Test suite target ports remain:
  - Backend: 7999
  - Frontend: 3000

## Recommended Maintenance Workflow
1. Recreate venv and install backend requirements:
   - .venv/Scripts/python.exe -m pip install -r backend/requirements.txt
2. Refresh frontend dependencies:
   - cd frontend
   - npm install
3. Run centralized suite:
   - python run_tests.py
