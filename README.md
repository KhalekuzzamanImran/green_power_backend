# Green Power Backend

Backend services for ingesting and serving grid, generator, environment, and solar data.

## Project layout

- `config/`: Django project configuration and settings modules
- `apps/`: Domain apps, API, realtime, and ingestion services
- `docker/`: Dockerfile, entrypoint, and docker-compose
- `nginx/`: Reverse proxy configuration
- `templates/`: Django templates
- `logs/`: Application log output (if enabled)

## Quickstart (local)

1) Create `.env` from `.env.example` and set values (including `DJANGO_SETTINGS_MODULE`).
2) Use a single `.env` with both local and Docker DB hostnames. For Docker Compose, set `DJANGO_SETTINGS_MODULE=config.settings.prod` and keep `*_DOCKER` values (e.g. `POSTGRES_HOST_DOCKER=green_power_postgres`).
2) Install deps and run:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## Docker

```bash
docker compose --env-file .env -f docker/docker-compose.yml up --build
```

## Settings

- Default module: `config.settings.dev`
- Production: set `DJANGO_SETTINGS_MODULE=config.settings.prod`
- Tests: set `DJANGO_SETTINGS_MODULE=config.settings.test`

## Ingestion services

```bash
python manage.py run_mqtt_subscriber
python manage.py run_tcp_server
```

## Authentication and roles (RBAC)

- JWT endpoints:
  - `POST /api/auth/token/` (username, password)
  - `POST /api/auth/token/refresh/`
  - `POST /api/auth/token/verify/`
- Default API access requires authentication and one of the roles: `admin`, `user`.
- Role keys available: `admin`, `user`, `viewer`.
- Refresh tokens rotate by default; old refresh tokens are blacklisted after rotation.
  - OAuth2-style responses include `token_type`, `expires_in`, and `refresh_expires_in`.

Viewer access is intended for live data via WebSocket only; HTTP API endpoints remain restricted to `admin` and `user`.
All DRF endpoints enforce role checks via the default `RoleRequired` permission.
The Django admin panel is restricted to `admin` role users (staff or superuser).

### WebSocket auth

WebSocket connections require JWT authentication for all roles (including `viewer`).
Provide the access token via:
- `Authorization: Bearer <token>` header, or
- `?token=<access_token>` query parameter.

Create the default roles:

```bash
python manage.py create_default_roles
```

Assign a role to a user (example):

```bash
python manage.py shell
>>> from django.contrib.auth.models import User
>>> from apps.api.models import Role, UserProfile
>>> user = User.objects.get(username="your-user")
>>> viewer = Role.objects.get(name="viewer")
>>> UserProfile.objects.update_or_create(user=user, defaults={"role": viewer})
```
