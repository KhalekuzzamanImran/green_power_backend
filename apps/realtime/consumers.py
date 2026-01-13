import json

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.conf import settings

from apps.api.roles import resolve_user_roles


class RealtimeConsumer(AsyncWebsocketConsumer):
    required_roles = {"admin", "user", "viewer"}

    @database_sync_to_async
    def _get_authenticated_roles(self, user):
        return resolve_user_roles(user)

    async def connect(self):
        if settings.REALTIME_ALLOWED_ORIGINS:
            origin = None
            for header, value in self.scope.get("headers", []):
                if header == b"origin":
                    origin = value.decode("utf-8", errors="ignore")
                    break
            if origin not in settings.REALTIME_ALLOWED_ORIGINS:
                await self.close()
                return
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close()
            return

        roles = set(await self._get_authenticated_roles(user))
        if not roles.intersection(self.required_roles):
            await self.close()
            return

        await self.channel_layer.group_add("realtime_updates", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("realtime_updates", self.channel_name)

    async def send_update(self, event):
        await self.send(text_data=json.dumps(event['data']))
