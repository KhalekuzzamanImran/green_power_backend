from urllib.parse import parse_qs

import django
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from django.apps import apps


def _get_token_from_scope(scope) -> str | None:
    headers = dict(scope.get("headers", []))
    auth_header = headers.get(b"authorization")
    if auth_header:
        try:
            parts = auth_header.decode().split()
        except UnicodeDecodeError:
            parts = []
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1]

    query_string = scope.get("query_string", b"").decode()
    query_params = parse_qs(query_string)
    token = query_params.get("token", [None])[0]
    return token


class JwtAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        if not apps.ready:
            django.setup()

        from django.contrib.auth.models import AnonymousUser
        from rest_framework_simplejwt.authentication import JWTAuthentication
        token = _get_token_from_scope(scope)
        user = AnonymousUser()

        if token:
            auth = JWTAuthentication()
            try:
                validated = auth.get_validated_token(token)
                user = await database_sync_to_async(auth.get_user)(validated)
            except Exception:
                user = AnonymousUser()

        scope["user"] = user
        return await super().__call__(scope, receive, send)
