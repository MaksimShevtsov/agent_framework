import asyncio
from typing import List, Dict, AsyncGenerator, Optional
from pydantic import BaseModel
import httpx
import structlog

logger = structlog.getLogger(__name__)


class TranscriptionResult(BaseModel):
    text: str
    confidence: float
    is_final: bool
    user_id: str
    session_id: str
    timestamp: float


class SpeechToTextPipeline:
    def __init__(
        self, model_endpoint: str, batch_size: int = 3, max_latency_ms: int = 300
    ):
        self.model_endpoint = model_endpoint
        self.batch_size = batch_size
        self.max_latency_ms = max_latency_ms
        self.batch_buffer: Dict[str, List] = {}  # Session ID -> audio chunks
        self.session_state: Dict[
            str, Dict
        ] = {}  # Store session state for continuous STT

    async def process_audio_chunk(
        self, audio_chunk
    ) -> AsyncGenerator[TranscriptionResult, None]:
        """Process a single audio chunk and return transcription when ready"""
        session_id = audio_chunk.session_id

        # Initialize session state if needed
        if session_id not in self.session_state:
            self.session_state[session_id] = {
                "buffer": [],
                "last_sent": asyncio.get_event_loop().time(),
                "pending_request": None,
            }

        # Add chunk to buffer
        self.session_state[session_id]["buffer"].append(audio_chunk)

        # Check if we should process now
        current_time = asyncio.get_event_loop().time()
        buffer_size = len(self.session_state[session_id]["buffer"])
        time_since_last_sent = (
            current_time - self.session_state[session_id]["last_sent"]
        ) * 1000

        should_process = (
            buffer_size >= self.batch_size
            or time_since_last_sent >= self.max_latency_ms
            or audio_chunk.is_final
        )

        if should_process:
            # Process the buffered chunks
            buffer = self.session_state[session_id]["buffer"]
            self.session_state[session_id]["buffer"] = []
            self.session_state[session_id]["last_sent"] = current_time

            # Create a task for the API request
            if self.session_state[session_id]["pending_request"]:
                # Wait for previous request to finish to maintain proper sequence
                await self.session_state[session_id]["pending_request"]

            task = asyncio.create_task(self._send_to_stt_service(buffer, session_id))
            self.session_state[session_id]["pending_request"] = task

            # Wait for the result
            result = await task
            self.session_state[session_id]["pending_request"] = None

            if result:
                yield TranscriptionResult(
                    text=result["text"],
                    confidence=result["confidence"],
                    is_final=audio_chunk.is_final,
                    user_id=audio_chunk.user_id,
                    session_id=session_id,
                    timestamp=current_time,
                )

    async def _send_to_stt_service(self, audio_chunks, session_id) -> Optional[Dict]:
        """Send audio data to STT service and get transcription result"""
        try:
            # Combine audio chunks into a single payload
            combined_audio = b"".join([chunk.data for chunk in audio_chunks])

            # Get session context for continuous transcription
            session_context = self.session_state[session_id].get("context", {})

            # Prepare the request payload
            payload = {
                "audio_data": combined_audio.hex(),  # Convert bytes to hex string
                "sample_rate": audio_chunks[0].sample_rate,
                "session_id": session_id,
                "context": session_context,
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(self.model_endpoint, json=payload)

                if response.status_code == 200:
                    result = response.json()

                    # Save context for next request
                    if "context" in result:
                        self.session_state[session_id]["context"] = result["context"]

                    return {
                        "text": result["text"],
                        "confidence": result.get("confidence", 1.0),
                    }
                else:
                    logger.error(
                        f"STT service error: {response.status_code}, {response.text}"
                    )
                    return None

        except Exception as e:
            logger.error(f"Error in STT processing: {str(e)}")
            return None

    async def terminate_session(self, session_id: str):
        """Clean up resources for a session"""
        if session_id in self.session_state:
            # Process any remaining audio in the buffer with final flag
            if self.session_state[session_id]["buffer"]:
                # Mark the last chunk as final
                self.session_state[session_id]["buffer"][-1].is_final = True

                # Process remaining audio
                async for result in self.process_audio_chunk(
                    self.session_state[session_id]["buffer"][-1]
                ):
                    # Return or handle the final result
                    pass

            # Clean up session state
            if self.session_state[session_id]["pending_request"]:
                await self.session_state[session_id]["pending_request"]
            del self.session_state[session_id]
