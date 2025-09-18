import json
from channels.generic.websocket import AsyncWebsocketConsumer
from .models import Message  # replace with your actual Message model import

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.room_group_name = f'chat_{self.user_id}'
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data['message']
        sender_id = data['sender_id']
        receiver_id = data['receiver_id']
        msg_id = data.get('id')

        if msg_id:
            msg = Message.objects.get(id=msg_id)
            msg.message = message
            msg.is_edited = True
            msg.save()
        else:
            msg = Message.objects.create(sender_id=sender_id, receiver_id=receiver_id, message=message)

        out_data = {
            "id": msg.id,
            "sender_id": msg.sender_id,
            "message": msg.message,
            "timestamp": str(msg.timestamp),
            "is_edited": msg.is_edited,
        }

        for uid in [sender_id, receiver_id]:
            await self.channel_layer.group_send(
                f'chat_{uid}',
                {"type": "chat_message", "message": out_data}
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event["message"]))
