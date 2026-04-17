# Deployment

This folder contains the Docker deployment assets for running the project locally with Docker Compose.

Use the root helper script for the common local workflow:

```powershell
.\docker-local.ps1 up
```

## Files

- `docker-compose.yml`: Runs MongoDB, backend, and frontend.
- `.env.aiecom`: Environment file template used by Docker Compose.
- `env.aiecom`: Compatibility copy of the same environment template.
- `backend.Dockerfile`: Backend image build definition.
- `frontend.Dockerfile`: Frontend image build definition.
- `nginx.conf`: Frontend nginx config with `/api` proxying to the backend.
- `mongo-init.js`: MongoDB initialization script.

## Build And Run

From the repository root:

```powershell
docker compose -f deployment/docker-compose.yml --env-file deployment/.env.aiecom up -d --build
```

Or with the helper script:

```powershell
.\docker-local.ps1 up
```

This starts:

- MongoDB on `localhost:27017`
- FastAPI backend on `http://localhost:7999`
- React frontend on `http://localhost:3000`

The backend connects to MongoDB through `mongodb_url` and `MONGO_URI`, both pointing to the `mongo` service on the internal Docker network.

The default admin account is created by the backend startup initializer with the values from `.env.aiecom`:

- Username: `admin`
- Password: `Qsrt#09-MWQ`
- Email: `admin@paultrades.com`

## Stop The Stack

```powershell
docker compose -f deployment/docker-compose.yml --env-file deployment/.env.aiecom down
```

```powershell
.\docker-local.ps1 down
```

Add `-v` if you want to remove the named MongoDB volume and start with a clean database.

## Verify Health

```powershell
docker compose -f deployment/docker-compose.yml --env-file deployment/.env.aiecom ps
```

```powershell
.\docker-local.ps1 ps
```

```powershell
docker compose -f deployment/docker-compose.yml --env-file deployment/.env.aiecom exec backend python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health').read().decode())"
```

```powershell
docker compose -f deployment/docker-compose.yml --env-file deployment/.env.aiecom exec mongo mongosh --quiet -u root -p rootpassword --authenticationDatabase admin --eval "db.adminCommand('ping')"
```

## Access Logs

```powershell
docker compose -f deployment/docker-compose.yml --env-file deployment/.env.aiecom logs -f
```

```powershell
.\docker-local.ps1 logs
```

To inspect one service only:

```powershell
docker compose -f deployment/docker-compose.yml --env-file deployment/.env.aiecom logs -f backend
```

```powershell
.\docker-local.ps1 logs backend
```

## Endpoints

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:7999`
- Backend health: `http://localhost:7999/health`
- Backend docs: `http://localhost:7999/docs`
- MongoDB: `mongodb://root:rootpassword@localhost:27017/admin`

## Notes

- MongoDB is stored in the named volume `econsite_mongo_data`.
- The Mongo init script creates the application user and bootstraps the `ecomdb` and `logDB` databases.
- The backend startup routine seeds the admin user inside the application database.
- The Docker build context excludes `test_suit/` from both backend and frontend image builds.
- The backend runs as a non-root user and the frontend runs on the unprivileged nginx image on internal port `8080`.