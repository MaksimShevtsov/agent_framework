from channels.generic.websocket import AsyncJsonWebsocketConsumer
from apps.chat.services.sanitizers import InputSanitizer


class ChatConsumer(AsyncJsonWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None
        self.room_name = None
        self.room_group_name = None
        self.sanitizer = InputSanitizer()

    async def connect(self):
        token = self.scope["url_route"]["kwargs"].get("token")
        if not token or not await self.validate_token(token):
            await self.close()
            return

        conversation_id = self.scope["url_route"]["kwargs"].get("conversation_id")
        if conversation_id:
            self.room_name = conversation_id
            self.room_group_name = f"chat_{self.room_name}"
        else:
            await self.close()
            return

    # async def validate_token(self, token):
    #     try:
    #         #token_obj = await WebSocketToken.objects.aget(token=token)
    #         if not token_obj.is_valid():
    #             return False

    #         # Mark token as used
    #         token_obj.used = True
    #         token_obj.save()

    #         # Store user reference
    #         self.user = token_obj.user
    #         return True
    #     except WebSocketToken.DoesNotExist:
    #         return False
