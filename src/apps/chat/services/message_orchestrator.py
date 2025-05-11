from typing import Any
import aioredis
from pydantic import BaseModel
import structlog
from datetime import datetime

logger = structlog.get_logger()


class Message(BaseModel):
    content: str
    role: str  # 'user', 'system', or 'assistant'
    timestamp: float
    message_id: str
    session_id: str
    metadata: dict[str, Any] = {}


class ContextManager:
    def __init__(self, max_context_length: int = 20):
        self.max_context_length = max_context_length
        self.session_contexts: dict[str, list[Message]] = {}

    def add_message(self, message: Message):
        if message.session_id not in self.session_contexts:
            self.session_contexts[message.session_id] = []
        self.session_contexts[message.session_id].append(message)
        if len(self.session_contexts[message.session_id]) > self.max_context_length:
            system_messages = [
                msg
                for msg in self.session_contexts[message.session_id]
                if msg.role == "system"
            ]

            other_messages = [
                msg
                for msg in self.session_contexts[message.session_id]
                if msg.role != "system"
            ]

            # Keep the N most recent non-system messages
            retained_count = self.max_context_length - len(system_messages)
            retained_messages = (
                other_messages[-retained_count:] if retained_count > 0 else []
            )

            # Reconstruct context with system messages first, then recent messages
            self.session_contexts[message.session_id] = (
                system_messages + retained_messages
            )

    def get_context(self, session_id: str) -> list[Message]:
        return self.session_contexts.get(session_id, [])

    def clear_session(self, session_id: str):
        if session_id in self.session_contexts:
            del self.session_contexts[session_id]
            logger.info(f"Cleared context for session {session_id}")
        else:
            logger.warning(f"Attempted to clear non-existent session {session_id}")


class MessageOrchestrator:
    def __init__(self, redis_url: str | None = None):
        self.context_manager = ContextManager()
        self.redis_url = redis_url
        self.redis_client = None
        self.active_sessions: dict[str, dict[str, Any]] = {}

    async def initialize(self):
        if self.redis_url:
            self.redis_client = await aioredis.create_redis_pool(self.redis_url)
            logger.info("Connected to Redis")
        else:
            logger.warning("No Redis URL provided, running in local mode")

    async def process_message(self, message: Message):
        """Process an incoming message and update context"""
        session_id = message.session_id

        # Add message to context
        self.context_manager.add_message(message)

        # Store in Redis if available for persistence
        if self.redis_client:
            await self.redis_client.lpush(
                f"session:{session_id}:messages", message.json()
            )
            # Trim the list to a reasonable size to prevent memory issues
            await self.redis_client.ltrim(f"session:{session_id}:messages", 0, 99)

        # Track active session
        if session_id not in self.active_sessions:
            self.active_sessions[session_id] = {
                "created_at": datetime.utcnow().isoformat(),
                "last_activity": datetime.utcnow().isoformat(),
                "message_count": 1,
            }
        else:
            self.active_sessions[session_id][
                "last_activity"
            ] = datetime.utcnow().isoformat()
            self.active_sessions[session_id]["message_count"] += 1

        return self.context_manager.get_context(session_id)

    async def process_transcription(self, transcription_result):
        """Process a transcription result into a message"""
        message = Message(
            content=transcription_result.text,
            role="user",
            timestamp=transcription_result.timestamp,
            message_id=f"transcript-{transcription_result.timestamp}",
            session_id=transcription_result.session_id,
            metadata={
                "source": "voice",
                "confidence": transcription_result.confidence,
                "is_final": transcription_result.is_final,
            },
        )

        # Only add final transcriptions to the context
        if transcription_result.is_final:
            return await self.process_message(message)
        return None

    async def terminate_session(self, session_id: str):
        """Clean up resources for a session"""
        # Clear context
        self.context_manager.clear_session(session_id)

        # Remove from active sessions
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]

        # Archive session data in Redis if needed
        if self.redis_client:
            # Move current messages to archived set
            messages = await self.redis_client.lrange(
                f"session:{session_id}:messages", 0, -1
            )
            if messages:
                archive_key = f"archive:session:{session_id}:messages"
                pipe = self.redis_client.pipeline()
                for msg in messages:
                    pipe.rpush(archive_key, msg)
                pipe.delete(f"session:{session_id}:messages")
                pipe.expire(archive_key, 60 * 60 * 24 * 30)  # 30 days retention
                await pipe.execute()
