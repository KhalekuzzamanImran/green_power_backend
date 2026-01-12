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
