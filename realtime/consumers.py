from channels.generic.websocket import AsyncWebsocketConsumer
import json

class RealtimeConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add('realtime_updates', self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard('realtime_updates', self.channel_name)

    async def send_update(self, event):
        await self.send(text_data=json.dumps(event['data']))