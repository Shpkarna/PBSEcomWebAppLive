# Deployment

This folder contains the production MySQL deployment assets for the live webapp repository.

This repository intentionally excludes `test_suit/` and `mobile_source/`. The deployment flow here is focused only on the production web frontend, backend, and MySQL stack.

The repository supports both direct Linux VPS deployments and GitHub-driven deployments to Hostinger.

## Files

- `docker-compose.mysql.yml`: Production-oriented compose stack for MySQL, backend, and frontend.
- `env.mysql.template`: Template for the required deployment environment file.
- `deploy_mysql.ps1`: First-time deployment script that validates config, builds images, starts containers, bootstraps schema, seeds admin, and runs smoke checks.
- `deploy_mysql.sh`: Linux equivalent of the first-time deployment flow for Ubuntu/Debian VPS hosts.
- `docker-mysql.ps1`: Day-to-day helper for `up`, `down`, `ps`, `logs`, `restart`, and `health`.
- `docker-mysql.sh`: Linux helper for day-to-day container operations.
- `docker-compose.edge.yml`: Optional Caddy edge proxy for domain-based public access on ports 80/443.
- `Caddyfile`: Domain and TLS reverse-proxy configuration for the edge service.
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

On Linux VPS hosts such as Hostinger Ubuntu instances:

```bash
cp deployment/env.mysql.template deployment/.env.mysql
bash deployment/deploy_mysql.sh
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

```bash
bash deployment/docker-mysql.sh up
```

Stop the stack:

```powershell
.\deployment\docker-mysql.ps1 down
```

```bash
bash deployment/docker-mysql.sh down
```

Inspect status:

```powershell
.\deployment\docker-mysql.ps1 ps
```

```bash
bash deployment/docker-mysql.sh ps
```

Check health:

```powershell
.\deployment\docker-mysql.ps1 health
```

```bash
bash deployment/docker-mysql.sh health
```

Stream logs:

```powershell
.\deployment\docker-mysql.ps1 logs
```

```bash
bash deployment/docker-mysql.sh logs
```

## Hostinger / GitHub Deployment

The repository includes a GitHub Actions workflow at `.github/workflows/hostinger-deploy.yml`.
It is designed for Hostinger VPS deployments and will:

- connect to the VPS over SSH
- clone or hard-reset the live repository on the server
- write `deployment/.env.mysql` from a GitHub secret
- run `bash deployment/deploy_mysql.sh`

Required GitHub secrets:

- `HOSTINGER_HOST`: VPS hostname or IP
- `HOSTINGER_USER`: SSH user, for example `root`
- `HOSTINGER_SSH_PRIVATE_KEY`: private key used by GitHub Actions to SSH into the VPS
- `HOSTINGER_ENV_MYSQL`: full contents of the production `deployment/.env.mysql` file

Optional GitHub repository variable:

- `HOSTINGER_DEPLOY_PATH`: deployment path on the VPS. Default: `/opt/pbsecom/PBSEcomWebAppLive`

Recommended production defaults for the env file:

- keep `PACKAGE_OPTION=prod`
- keep `ENABLE_EMAIL_VERIFICATION=false` until an email provider is ready
- keep `ENABLE_MOBILE_OTP_VERIFICATION=false` until MSG91 is configured
- keep `FRONTEND_PORT=127.0.0.1:3000` and `BACKEND_PORT=127.0.0.1:7999` when using the edge proxy
- set `PUBLIC_DOMAIN=biyebaari.com`
- set `ACME_EMAIL` to a real mailbox that should receive Let's Encrypt notifications

Once MSG91 is configured from the admin UI, mobile OTP can be enabled without changing the deployment workflow.

## Domain Mapping For biyebaari.com

The VPS side can serve the site on `biyebaari.com` once DNS points to the Hostinger VPS.

Required DNS records:

- Apex / root domain `biyebaari.com`: set an `A` record to the VPS public IP `145.223.18.16`
- `www.biyebaari.com`: keep as a `CNAME` to `biyebaari.com`

Current observation at deployment time:

- `biyebaari.com` resolves to `2.57.91.91`, so public traffic is not yet reaching this VPS

Once the `A` record is updated and DNS propagates, the Caddy edge service can obtain TLS automatically and serve the site on `https://biyebaari.com`.

## Endpoints

- Frontend: `http://localhost:3000` (host-local only by default)
- Backend API: `http://localhost:7999` (host-local only by default)
- Backend health: `http://localhost:7999/health` (host-local only by default)
- Backend docs: `http://localhost:7999/docs` (host-local only by default)
- MySQL host binding: `127.0.0.1:3306` by default

## Notes

- `docker-compose.mysql.yml` is the only deployment compose file included in this repository.
- Backend runtime is configured for `DB_ENGINE=mysql` by the compose file.
- The recommended production env template binds the frontend to `127.0.0.1:3000` and the backend to `127.0.0.1:7999` when the Caddy edge proxy is enabled.
- The recommended production env template binds the backend to `127.0.0.1:7999` by default to avoid direct public API exposure.
- The backend image already includes `PyMySQL`; no MongoDB service is required.
- The frontend Docker build skips Playwright browser downloads to keep the production image build lean.
- The Docker build context excludes test-only and mobile-only source trees from the production image inputs.
- For internet-facing production use, place a TLS reverse proxy in front of the frontend container and restrict backend access at the firewall or network layer.