from .base import *  # noqa: F401,F403

DEBUG = True

SECRET_KEY = os.getenv("SECRET_KEY", "insecure-dev-key")
ALLOWED_HOSTS = [host.strip() for host in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if host.strip()]
