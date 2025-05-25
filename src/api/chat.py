"""
Chat API endpoints for text messaging and conversation management
"""
from ninja import Router, Schema
from typing import List, Optional
from datetime import datetime
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
import logging

from apps.chat.models import Chat, Conversation, Message, Thread, ChatUser
from apps.tokens.models import WebSocketToken
from apps.chat.services.sanitizers import InputSanitizer
from core.models import Instance

logger = logging.getLogger(__name__)
router = Router()


# Schemas
class MessageCreate(Schema):
    content: str
    conversation_id: Optional[str] = None


class MessageResponse(Schema):
    id: int
    content: str
    sender: str
    timestamp: datetime
    conversation_id: int
    thread_id: Optional[int] = None


class ConversationResponse(Schema):
    id: int
    created_at: datetime
    is_active: bool
    is_archived: bool
    message_count: int


class WebSocketTokenResponse(Schema):
    token: str
    expires_at: datetime


class ChatUserCreate(Schema):
    settings: dict = {}


class ChatUserResponse(Schema):
    id: int
    is_verified: bool
    settings: dict


# Initialize sanitizer
sanitizer = InputSanitizer()


@router.post("/users/", response=ChatUserResponse, tags=["Users"])
def create_chat_user(request, data: ChatUserCreate):
    """Create a new chat user"""
    try:
        chat_user = ChatUser.objects.create(is_verified=False, settings=data.settings)
        return chat_user
    except Exception as e:
        logger.error(f"Failed to create chat user: {e}")
        return {"error": "Failed to create user"}, 500


@router.get("/users/{user_id}/", response=ChatUserResponse, tags=["Users"])
def get_chat_user(request, user_id: int):
    """Get chat user details"""
    chat_user = get_object_or_404(ChatUser, id=user_id)
    return chat_user


@router.post("/messages/", response=MessageResponse, tags=["Messages"])
def send_message(request, data: MessageCreate):
    """Send a chat message"""
    try:
        # Sanitize content
        sanitized_content = sanitizer.sanitize_text(data.content)

        # Get or create default user and chat
        user, created = User.objects.get_or_create(
            username="api_user", defaults={"email": "api@example.com"}
        )

        chat, created = Chat.objects.get_or_create(user=user, defaults={})

        # Get or create conversation
        if data.conversation_id:
            conversation = get_object_or_404(Conversation, id=data.conversation_id)
        else:
            conversation = Conversation.objects.create(chat=chat, is_active=True)

        # Create thread for this message
        thread = Thread.objects.create(conversation=conversation)

        # Save message
        message = Message.objects.create(
            conversation=conversation,
            thread=thread,
            content=sanitized_content,
            sender="user",
        )

        return {
            "id": message.id,
            "content": message.content,
            "sender": message.sender,
            "timestamp": message.created_at,
            "conversation_id": conversation.id,
            "thread_id": thread.id,
        }

    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        return {"error": "Failed to send message"}, 500


@router.get(
    "/conversations/", response=List[ConversationResponse], tags=["Conversations"]
)
def list_conversations(request):
    """List all active conversations"""
    try:
        conversations = Conversation.objects.filter(is_active=True).prefetch_related(
            "messages"
        )
        return [
            {
                "id": conv.id,
                "created_at": conv.created_at,
                "is_active": conv.is_active,
                "is_archived": conv.is_archived,
                "message_count": conv.messages.count(),
            }
            for conv in conversations
        ]
    except Exception as e:
        logger.error(f"Failed to list conversations: {e}")
        return {"error": "Failed to fetch conversations"}, 500


@router.get(
    "/conversations/{conversation_id}/messages/",
    response=List[MessageResponse],
    tags=["Conversations"],
)
def get_conversation_messages(request, conversation_id: int, limit: int = 50):
    """Get messages for a specific conversation"""
    try:
        conversation = get_object_or_404(Conversation, id=conversation_id)
        messages = conversation.messages.order_by("-created_at")[:limit]

        return [
            {
                "id": msg.id,
                "content": msg.content,
                "sender": msg.sender,
                "timestamp": msg.created_at,
                "conversation_id": msg.conversation.id,
                "thread_id": msg.thread.id if msg.thread else None,
            }
            for msg in reversed(messages)
        ]
    except Exception as e:
        logger.error(f"Failed to get conversation messages: {e}")
        return {"error": "Failed to fetch messages"}, 500


@router.post("/websocket-token/", response=WebSocketTokenResponse, tags=["WebSocket"])
def generate_websocket_token(request, user_id: int):
    """Generate a WebSocket token for real-time communication"""
    try:
        chat_user = get_object_or_404(ChatUser, id=user_id)
        instance, created = Instance.objects.get_or_create(defaults={"name": "default"})

        # Generate token
        token_obj = WebSocketToken.generate_token(chat_user)
        token_obj.instance = instance
        token_obj.save()

        return {"token": token_obj.token, "expires_at": token_obj.created_at}

    except Exception as e:
        logger.error(f"Failed to generate WebSocket token: {e}")
        return {"error": "Failed to generate token"}, 500


@router.delete("/conversations/{conversation_id}/", tags=["Conversations"])
def archive_conversation(request, conversation_id: int):
    """Archive a conversation"""
    try:
        conversation = get_object_or_404(Conversation, id=conversation_id)
        conversation.is_archived = True
        conversation.is_active = False
        conversation.save()

        return {"message": "Conversation archived successfully"}

    except Exception as e:
        logger.error(f"Failed to archive conversation: {e}")
        return {"error": "Failed to archive conversation"}, 500
