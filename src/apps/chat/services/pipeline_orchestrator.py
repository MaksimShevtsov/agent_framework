import asyncio
from typing import Dict, Optional, List
import uuid
from datetime import datetime

# Import pipeline components
from .audio_pipeline import AudioProcessor
from .stt_pipeline import SpeechToTextPipeline
from .message_orchestrator import MessageOrchestrator, Message
from .ai_pipeline import MLPipeline, MLRequest
from .tts_pipeline import ResponseGenerator

import structlog

logger = structlog.get_logger()


class PipelineOrchestrator:
    def __init__(
        self,
        model_endpoint: str,
        tts_endpoint: str,
        redis_url: Optional[str] = None,
        enable_monitoring: bool = True,
    ):
        # Initialize pipeline components
        self.audio_processor = AudioProcessor()
        self.speech_to_text = SpeechToTextPipeline(model_endpoint + "/stt")
        self.message_orchestrator = MessageOrchestrator(redis_url)
        self.ml_pipeline = MLPipeline(model_endpoint + "/inference", batch_enabled=True)
        self.response_generator = ResponseGenerator(tts_endpoint)

        # Configuration
        self.enable_monitoring = enable_monitoring

        # Runtime state
        self.active_sessions: Dict[str, Dict] = {}
        self.monitoring_data = {
            "requests_processed": 0,
            "audio_chunks_processed": 0,
            "ml_requests": 0,
            "tts_requests": 0,
            "errors": 0,
            "avg_processing_time": 0,
        }

    async def initialize(self):
        """Initialize all pipeline components"""
        await self.message_orchestrator.initialize()
        await self.ml_pipeline.initialize()

        # Start monitoring task if enabled
        if self.enable_monitoring:
            asyncio.create_task(self._monitoring_task())

    async def process_audio_stream(self, audio_stream, session_id: str, user_id: str):
        """Process incoming audio stream"""
        # Register session if new
        self._register_session(session_id, user_id)

        try:
            # Process audio through the pipeline
            audio_task = asyncio.create_task(
                self.audio_processor.process_stream(audio_stream, session_id, user_id)
            )

            # Process transcription results
            async for chunk in self.speech_to_text.process_audio_chunk(audio_task):
                if chunk and chunk.is_final:
                    # Process final transcription
                    context = await self.message_orchestrator.process_transcription(
                        chunk
                    )

                    # Generate AI response if we have a final transcription
                    if context:
                        response = await self._generate_response(
                            context, session_id, user_id
                        )

                        # Return the response
                        return response

            return None
        except Exception as e:
            logger.error(f"Error processing audio stream: {str(e)}")
            self.monitoring_data["errors"] += 1
            raise

    async def process_text_message(self, text: str, session_id: str, user_id: str):
        """Process incoming text message"""
        # Register session if new
        self._register_session(session_id, user_id)

        try:
            start_time = asyncio.get_event_loop().time()

            # Create message
            message = Message(
                content=text,
                role="user",
                timestamp=start_time,
                message_id=f"msg-{uuid.uuid4()}",
                session_id=session_id,
                metadata={"source": "text"},
            )

            # Process through message orchestrator
            context = await self.message_orchestrator.process_message(message)

            # Generate AI response
            response = await self._generate_response(context, session_id, user_id)

            # Update monitoring
            end_time = asyncio.get_event_loop().time()
            self._update_monitoring(end_time - start_time)

            return response
        except Exception as e:
            logger.error(f"Error processing text message: {str(e)}")
            self.monitoring_data["errors"] += 1
            raise

    async def _generate_response(
        self, context: List[Message], session_id: str, user_id: str
    ):
        """Generate AI response based on context"""
        try:
            # Format messages for ML model
            formatted_context = []
            for msg in context:
                formatted_context.append({"role": msg.role, "content": msg.content})

            # Create ML request
            request_id = f"req-{uuid.uuid4()}"
            ml_request = MLRequest(
                context=formatted_context,
                session_id=session_id,
                user_id=user_id,
                request_id=request_id,
                model_name="gpt-4",  # This can be configurable
                parameters={},
                timestamp=asyncio.get_event_loop().time(),
            )

            # Get response from ML model
            self.monitoring_data["ml_requests"] += 1
            ml_response = await self.ml_pipeline.process_request(ml_request)

            # Create assistant message
            assistant_message = Message(
                content=ml_response.text,
                role="assistant",
                timestamp=ml_response.timestamp,
                message_id=f"assistant-{request_id}",
                session_id=session_id,
                metadata={
                    "model_used": ml_response.model_used,
                    "processing_time": ml_response.processing_time,
                },
            )

            # Add to context
            await self.message_orchestrator.process_message(assistant_message)

            # Generate audio response
            self.monitoring_data["tts_requests"] += 1
            voice_id = self.active_sessions[session_id].get("voice_id", "default")

            audio_responses = []
            async for audio_chunk in self.response_generator.generate_audio_response(
                ml_response, voice_id
            ):
                audio_responses.append(audio_chunk)

            # Return complete response
            return {
                "text_response": assistant_message,
                "audio_response": audio_responses,
            }

        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            self.monitoring_data["errors"] += 1
            raise

    def _register_session(self, session_id: str, user_id: str):
        """Register a new session or update existing one"""
        now = datetime.utcnow().isoformat()

        if session_id not in self.active_sessions:
            # New session
            self.active_sessions[session_id] = {
                "user_id": user_id,
                "created_at": now,
                "last_activity": now,
                "message_count": 0,
                "voice_id": "default",  # Default voice ID
            }
        else:
            # Update existing session
            self.active_sessions[session_id]["last_activity"] = now
            self.active_sessions[session_id]["message_count"] += 1

    def _update_monitoring(self, processing_time: float):
        """Update monitoring metrics"""
        self.monitoring_data["requests_processed"] += 1

        # Update average processing time
        current_avg = self.monitoring_data["avg_processing_time"]
        count = self.monitoring_data["requests_processed"]

        # Weighted average (more weight to recent requests)
        if count > 1:
            self.monitoring_data["avg_processing_time"] = (
                current_avg * 0.8 + processing_time * 0.2
            )
        else:
            self.monitoring_data["avg_processing_time"] = processing_time

    async def _monitoring_task(self):
        """Background task to log monitoring data"""
        while True:
            try:
                await asyncio.sleep(60)  # Log every minute

                # Log current stats
                logger.info(f"Pipeline stats: {self.monitoring_data}")

                # Check for inactive sessions
                now = datetime.utcnow()
                inactive_sessions = []

                for session_id, info in self.active_sessions.items():
                    last_active = datetime.fromisoformat(info["last_activity"])
                    if (now - last_active).total_seconds() > 3600:  # 1 hour inactive
                        inactive_sessions.append(session_id)

                # Clean up inactive sessions
                for session_id in inactive_sessions:
                    await self.terminate_session(session_id)

            except Exception as e:
                logger.error(f"Error in monitoring task: {str(e)}")

    async def terminate_session(self, session_id: str):
        """Clean up resources for a session"""
        try:
            # Clean up all pipeline components
            await self.speech_to_text.terminate_session(session_id)
            await self.message_orchestrator.terminate_session(session_id)
            await self.response_generator.clean_session(session_id)

            # Remove from active sessions
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]

            logger.info(f"Session terminated: {session_id}")
        except Exception as e:
            logger.error(f"Error terminating session: {str(e)}")
