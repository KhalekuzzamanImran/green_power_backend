from .base import *  # noqa: F401,F403

DEBUG = False

SECRET_KEY = "test-secret-key"
ALLOWED_HOSTS = ["testserver"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

MONGO_CREATE_INDEXES = False
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
