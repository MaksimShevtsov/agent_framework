import logging
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from django.contrib.auth.models import User
from apps.chat.services.sanitizers import InputSanitizer
from apps.tokens.models import WebSocketToken
from apps.chat.models import Chat, Conversation, Thread, Message

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncJsonWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None
        self.chat_user = None
        self.room_name = None
        self.room_group_name = None
        self.chat_session = None
        self.conversation = None
        self.sanitizer = InputSanitizer()

    async def connect(self):
        """Handle WebSocket connection"""
        try:
            token = self.scope["url_route"]["kwargs"].get("token")
            if not token or not await self.validate_token(token):
                await self.close(code=4001)
                return

            conversation_id = self.scope["url_route"]["kwargs"].get("conversation_id")
            if conversation_id:
                self.room_name = conversation_id
                self.room_group_name = f"chat_{self.room_name}"

                # Setup chat session
                await self.setup_chat_session(conversation_id)

                # Join room group
                await self.channel_layer.group_add(
                    self.room_group_name, self.channel_name
                )

                await self.accept()

                # Send connection success message
                await self.send_json(
                    {
                        "type": "connection_established",
                        "session_id": conversation_id,
                        "user_id": getattr(self.chat_user, "pk", None),
                        "message": "Connected successfully",
                    }
                )
            else:
                await self.close(code=4002)

        except Exception as e:
            logger.error(f"Connection error: {e}")
            await self.close(code=4003)

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        if self.room_group_name:
            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name
            )
        logger.info(f"WebSocket disconnected: {close_code}")

    async def receive_json(self, content):
        """Handle incoming WebSocket messages"""
        try:
            message_type = content.get("type")

            if message_type == "chat_message":
                await self.handle_chat_message(content)
            elif message_type == "webrtc_signal":
                await self.handle_webrtc_signal(content)
            elif message_type == "voice_data":
                await self.handle_voice_data(content)
            elif message_type == "typing":
                await self.handle_typing_indicator(content)
            elif message_type == "ping":
                await self.send_json(
                    {"type": "pong", "timestamp": timezone.now().isoformat()}
                )
            else:
                await self.send_json(
                    {
                        "type": "error",
                        "message": f"Unknown message type: {message_type}",
                    }
                )

        except Exception as e:
            logger.error(f"Error processing WebSocket message: {e}")
            await self.send_json(
                {"type": "error", "message": "Failed to process message"}
            )

    async def handle_chat_message(self, content):
        """Process text chat messages"""
        try:
            message_content = content.get("message", "")

            # Sanitize input
            sanitized_content = await database_sync_to_async(
                self.sanitizer.sanitize_text
            )(message_content)

            # Create thread for this message exchange
            thread = await self.create_thread()
            if not thread:
                await self.send_json(
                    {"type": "error", "message": "Failed to create thread"}
                )
                return

            # Save user message
            user_message = await self.save_message(
                thread=thread, content=sanitized_content, sender="user"
            )

            if user_message:
                # Broadcast user message to room
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "chat_message_broadcast",
                        "message": {
                            "id": user_message.id,
                            "content": sanitized_content,
                            "sender": "user",
                            "timestamp": user_message.created_at.isoformat(),
                        },
                    },
                )

                # Generate AI response
                ai_response_content = await self.generate_ai_response(sanitized_content)

                # Save AI response
                ai_message = await self.save_message(
                    thread=thread, content=ai_response_content, sender="assistant"
                )

                if ai_message:
                    # Broadcast AI response
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            "type": "chat_message_broadcast",
                            "message": {
                                "id": ai_message.id,
                                "content": ai_response_content,
                                "sender": "assistant",
                                "timestamp": ai_message.created_at.isoformat(),
                            },
                        },
                    )

        except Exception as e:
            logger.error(f"Chat message error: {e}")
            await self.send_json(
                {"type": "error", "message": "Failed to process chat message"}
            )

    async def handle_webrtc_signal(self, content):
        """Handle WebRTC signaling for voice calls"""
        try:
            signal_type = content.get("signal_type")
            signal_data = content.get("data")
            target_user = content.get("target_user")

            # Broadcast WebRTC signal to room or specific user
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "webrtc_signal_broadcast",
                    "signal": {
                        "type": signal_type,
                        "data": signal_data,
                        "from_user": getattr(self.chat_user, "pk", None),
                        "target_user": target_user,
                        "timestamp": timezone.now().isoformat(),
                    },
                },
            )
        except Exception as e:
            logger.error(f"WebRTC signal error: {e}")

    async def handle_voice_data(self, content):
        """Handle real-time voice data processing"""
        try:
            audio_data = content.get("audio_data")
            metadata = content.get("metadata", {})

            if audio_data:
                # Process voice data (STT, analysis, etc.)
                processed_data = await self.process_voice_data(audio_data, metadata)

                # Broadcast processed voice data
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "voice_data_broadcast",
                        "data": processed_data,
                        "from_user": getattr(self.chat_user, "pk", None),
                        "timestamp": timezone.now().isoformat(),
                    },
                )

        except Exception as e:
            logger.error(f"Voice data error: {e}")

    async def handle_typing_indicator(self, content):
        """Handle typing indicators"""
        try:
            is_typing = content.get("is_typing", False)

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "typing_indicator_broadcast",
                    "user_id": getattr(self.chat_user, "pk", None),
                    "is_typing": is_typing,
                    "timestamp": timezone.now().isoformat(),
                },
            )
        except Exception as e:
            logger.error(f"Typing indicator error: {e}")

    # Group message handlers
    async def chat_message_broadcast(self, event):
        """Send chat message to WebSocket"""
        await self.send_json({"type": "chat_message", "message": event["message"]})

    async def webrtc_signal_broadcast(self, event):
        """Send WebRTC signal to WebSocket"""
        signal = event["signal"]
        user_id = getattr(self.chat_user, "pk", None)

        # Only send to target user or broadcast if no target specified
        if not signal.get("target_user") or signal["target_user"] == user_id:
            await self.send_json({"type": "webrtc_signal", "signal": signal})

    async def voice_data_broadcast(self, event):
        """Send voice data to WebSocket"""
        user_id = getattr(self.chat_user, "pk", None)
        if event.get("from_user") != user_id:  # Don't echo back to sender
            await self.send_json(
                {
                    "type": "voice_data",
                    "data": event["data"],
                    "from_user": event["from_user"],
                    "timestamp": event["timestamp"],
                }
            )

    async def typing_indicator_broadcast(self, event):
        """Send typing indicator to WebSocket"""
        user_id = getattr(self.chat_user, "pk", None)
        if event["user_id"] != user_id:  # Don't send to self
            await self.send_json(
                {
                    "type": "typing_indicator",
                    "user_id": event["user_id"],
                    "is_typing": event["is_typing"],
                    "timestamp": event["timestamp"],
                }
            )

    async def validate_token(self, token):
        """Validate WebSocket token"""
        try:
            token_obj = await database_sync_to_async(WebSocketToken.objects.get)(
                token=token
            )

            is_valid = await database_sync_to_async(token_obj.is_valid)()
            if not is_valid:
                return False

            # Mark token as used
            await database_sync_to_async(lambda: setattr(token_obj, "used", True))()
            await database_sync_to_async(token_obj.save)()

            # Store user reference
            self.chat_user = token_obj.user
            return True

        except WebSocketToken.DoesNotExist:
            return False
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return False

    @database_sync_to_async
    def setup_chat_session(self, conversation_id):
        """Get or create chat session and conversation"""
        try:
            # Create or get Django user
            username = f"chat_user_{self.chat_user.pk if self.chat_user else 'unknown'}"
            django_user, created = User.objects.get_or_create(
                username=username, defaults={"email": f"{username}@example.com"}
            )

            # Get or create chat
            self.chat_session, created = Chat.objects.get_or_create(
                user=django_user, defaults={}
            )

            # Get or create conversation
            self.conversation, created = Conversation.objects.get_or_create(
                id=conversation_id,
                defaults={"chat": self.chat_session, "is_active": True},
            )
            return True

        except Exception as e:
            logger.error(f"Setup chat session error: {e}")
            return False

    @database_sync_to_async
    def create_thread(self):
        """Create a new thread for message exchange"""
        try:
            if self.conversation:
                return Thread.objects.create(conversation=self.conversation)
        except Exception as e:
            logger.error(f"Create thread error: {e}")
        return None

    @database_sync_to_async
    def save_message(self, thread, content, sender):
        """Save message to database"""
        try:
            if self.conversation and thread:
                return Message.objects.create(
                    conversation=self.conversation,
                    thread=thread,
                    content=content,
                    sender=sender,
                )
        except Exception as e:
            logger.error(f"Save message error: {e}")
        return None

    async def generate_ai_response(self, user_message):
        """Generate AI response to user message"""
        try:
            # Mock AI response - in production, integrate with actual AI models
            responses = [
                f"I understand you're saying: {user_message}",
                f"That's an interesting point about '{user_message[:50]}...'",
                f"Let me help you with that. Regarding '{user_message}', I think...",
                f"Thanks for sharing that. In response to '{user_message}', here's what I think...",  # noqa: E501
            ]

            import random

            return random.choice(responses)

        except Exception as e:
            logger.error(f"AI response generation error: {e}")
            return "I'm sorry, I couldn't process that request."

    async def process_voice_data(self, audio_data, metadata):
        """Process voice data for real-time features"""
        try:
            # Mock voice processing - in production, implement STT, analysis, etc.
            return {
                "processed": True,
                "transcript": "Voice data processed",
                "confidence": 0.85,
                "metadata": metadata,
            }
        except Exception as e:
            logger.error(f"Voice processing error: {e}")
            return {"processed": False, "error": str(e)}
