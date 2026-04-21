# Deployment

This folder contains the production MySQL deployment assets for the live webapp repository.

This repository intentionally excludes `test_suit/` and `mobile_source/`. The deployment flow here is focused only on the production web frontend, backend, and MySQL stack.

## Files

- `docker-compose.mysql.yml`: Production-oriented compose stack for MySQL, backend, and frontend.
- `env.mysql.template`: Template for the required deployment environment file.
- `deploy_mysql.ps1`: First-time deployment script that validates config, builds images, starts containers, bootstraps schema, seeds admin, and runs smoke checks.
- `docker-mysql.ps1`: Day-to-day helper for `up`, `down`, `ps`, `logs`, `restart`, and `health`.
- `backend.Dockerfile`: Backend image build definition.
- `frontend.Dockerfile`: Frontend image build definition.
- `backend.Dockerfile.dockerignore`: Backend Docker build-context filter.
- `frontend.Dockerfile.dockerignore`: Frontend Docker build-context filter.
- `mysql-init.sh`: First-boot MySQL container initialization script.
- `nginx.conf`: Frontend nginx config with `/api` proxying to the backend container.

## First-Time Deployment

From the repository root:

```powershell
Copy-Item deployment\env.mysql.template deployment\.env.mysql
```

Update every `CHANGE_ME` value in `deployment\.env.mysql`, then run:

```powershell
.\deployment\deploy_mysql.ps1
```

That flow will:

- build the backend and frontend images
- start MySQL, backend, and frontend containers
- bootstrap the MySQL schema
- seed the admin user
- run smoke checks against the deployed stack

## Day-to-Day Operations

Start or rebuild the stack:

```powershell
.\deployment\docker-mysql.ps1 up
```

Stop the stack:

```powershell
.\deployment\docker-mysql.ps1 down
```

Inspect status:

```powershell
.\deployment\docker-mysql.ps1 ps
```

Check health:

```powershell
.\deployment\docker-mysql.ps1 health
```

Stream logs:

```powershell
.\deployment\docker-mysql.ps1 logs
```

## Endpoints

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:7999`
- Backend health: `http://localhost:7999/health`
- Backend docs: `http://localhost:7999/docs`
- MySQL host binding: `127.0.0.1:3306` by default

## Notes

- `docker-compose.mysql.yml` is the only deployment compose file included in this repository.
- Backend runtime is configured for `DB_ENGINE=mysql` by the compose file.
- The backend image already includes `PyMySQL`; no MongoDB service is required.
- The frontend Docker build skips Playwright browser downloads to keep the production image build lean.
- The Docker build context excludes test-only and mobile-only source trees from the production image inputs.