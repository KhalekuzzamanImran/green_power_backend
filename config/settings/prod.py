from .base import *  # noqa: F401,F403

DEBUG = False

if not SECRET_KEY:
    raise ValueError("SECRET_KEY must be set in production.")

ALLOWED_HOSTS = [host.strip() for host in os.getenv("ALLOWED_HOSTS", "").split(",") if host.strip()]

POSTGRES_HOST_DOCKER = os.getenv("POSTGRES_HOST_DOCKER")
POSTGRES_PORT_DOCKER = os.getenv("POSTGRES_PORT_DOCKER")
if POSTGRES_HOST_DOCKER:
    DATABASES["default"]["HOST"] = POSTGRES_HOST_DOCKER
if POSTGRES_PORT_DOCKER:
    DATABASES["default"]["PORT"] = POSTGRES_PORT_DOCKER

MONGO_DB_HOST_DOCKER = os.getenv("MONGO_DB_HOST_DOCKER")
MONGO_DB_PORT_DOCKER = os.getenv("MONGO_DB_PORT_DOCKER")
if MONGO_DB_HOST_DOCKER:
    MONGO_DB_HOST = MONGO_DB_HOST_DOCKER
if MONGO_DB_PORT_DOCKER:
    MONGO_DB_PORT = MONGO_DB_PORT_DOCKER
    if not MONGO_DB_PORT.isdigit():
        MONGO_DB_PORT = "27017"

REDIS_HOST_DOCKER = os.getenv("REDIS_HOST_DOCKER")
if REDIS_HOST_DOCKER:
    CHANNEL_LAYERS["default"]["CONFIG"]["hosts"] = [(REDIS_HOST_DOCKER, int(os.getenv("REDIS_PORT", 6379)))]

# Rebuild Mongo URI if not explicitly set and host/port override is present.
if not os.getenv("MONGO_DB_URI") and not os.getenv("MONGODB_URI"):
    if MONGO_DB_USER and MONGO_DB_PASSWORD:
        MONGO_DB_URI = (
            f"mongodb://{MONGO_DB_USER}:{MONGO_DB_PASSWORD}@{MONGO_DB_HOST}:{MONGO_DB_PORT}/?authSource=admin"
        )
    else:
        MONGO_DB_URI = f"mongodb://{MONGO_DB_HOST}:{MONGO_DB_PORT}"

SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "true").lower() in ("true", "1", "yes")
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]
