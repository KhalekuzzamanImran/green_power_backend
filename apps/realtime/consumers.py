import json

from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings

class RealtimeConsumer(AsyncWebsocketConsumer):
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
        await self.channel_layer.group_add('realtime_updates', self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard('realtime_updates', self.channel_name)

    async def send_update(self, event):
        await self.send(text_data=json.dumps(event['data']))
