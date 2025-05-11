import asyncio
from typing import Dict, List, Any, Union, AsyncGenerator
from pydantic import BaseModel
import httpx
import logging
import time
import wave
import io

logger = logging.getLogger(__name__)


class TTSRequest(BaseModel):
    text: str
    voice_id: str
    session_id: str
    request_id: str
    parameters: Dict[str, Any] = {}


class TTSResponse(BaseModel):
    audio_data: bytes
    duration: float
    sample_rate: int
    format: str = "wav"
    session_id: str
    request_id: str
    text: str


class ResponseGenerator:
    def __init__(
        self,
        tts_endpoint: str,
        enable_streaming: bool = True,
        chunk_size_chars: int = 100,
        audio_buffer_size: int = 3,
    ):
        self.tts_endpoint = tts_endpoint
        self.enable_streaming = enable_streaming
        self.chunk_size_chars = chunk_size_chars
        self.audio_buffer_size = audio_buffer_size
        self.session_info = {}

    async def generate_audio_response(
        self, ml_response, voice_id: str = "default"
    ) -> AsyncGenerator[Union[bytes, TTSResponse], None]:
        """Generate audio response from text, streaming if enabled"""
        text = ml_response.text
        session_id = ml_response.session_id
        request_id = ml_response.request_id

        # Track session
        if session_id not in self.session_info:
            self.session_info[session_id] = {
                "last_activity": time.time(),
                "audio_queue": asyncio.Queue(maxsize=self.audio_buffer_size),
            }
        else:
            self.session_info[session_id]["last_activity"] = time.time()

        if self.enable_streaming and len(text) > self.chunk_size_chars:
            # Stream response in chunks for better user experience
            chunks = self._split_text_into_chunks(text)

            for i, chunk in enumerate(chunks):
                tts_request = TTSRequest(
                    text=chunk,
                    voice_id=voice_id,
                    session_id=session_id,
                    request_id=f"{request_id}-{i}",
                    parameters={
                        "is_streaming": True,
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                    },
                )

                chunk_response = await self._send_tts_request(tts_request)

                # Add to the queue for buffer management
                await self.session_info[session_id]["audio_queue"].put(chunk_response)

                # Yield the audio data
                yield chunk_response

                # If queue is full, wait for some consumption
                if self.session_info[session_id]["audio_queue"].full():
                    await asyncio.sleep(0.1)
        else:
            # Single request for shorter text
            tts_request = TTSRequest(
                text=text,
                voice_id=voice_id,
                session_id=session_id,
                request_id=request_id,
                parameters={"is_streaming": False},
            )

            response = await self._send_tts_request(tts_request)
            yield response

    def _split_text_into_chunks(self, text: str) -> List[str]:
        """Split text into streamable chunks at appropriate boundaries"""
        if len(text) <= self.chunk_size_chars:
            return [text]

        chunks = []
        current_pos = 0

        while current_pos < len(text):
            # Find a good breaking point near chunk_size_chars
            end_pos = min(current_pos + self.chunk_size_chars, len(text))

            # Try to break at sentence end (.!?)
            sentence_break = max(
                text.rfind(". ", current_pos, end_pos),
                text.rfind("! ", current_pos, end_pos),
                text.rfind("? ", current_pos, end_pos),
            )

            if sentence_break > current_pos:
                end_pos = sentence_break + 1  # Include the punctuation
            else:
                # Try to break at comma
                comma_break = text.rfind(", ", current_pos, end_pos)
                if comma_break > current_pos:
                    end_pos = comma_break + 1
                else:
                    # Just break at a space if possible
                    space_break = text.rfind(" ", current_pos, end_pos)
                    if space_break > current_pos:
                        end_pos = space_break

            # Extract the chunk
            chunks.append(text[current_pos:end_pos].strip())
            current_pos = end_pos

        return chunks

    async def _send_tts_request(self, tts_request: TTSRequest) -> TTSResponse:
        """Send request to TTS service"""
        try:
            payload = tts_request.dict()

            async with httpx.AsyncClient() as client:
                response = await client.post(self.tts_endpoint, json=payload)

                if response.status_code == 200:
                    audio_data = await response.aread()

                    # Parse audio data to get duration and sample rate
                    duration, sample_rate = self._analyze_audio_data(audio_data)

                    return TTSResponse(
                        audio_data=audio_data,
                        duration=duration,
                        sample_rate=sample_rate,
                        session_id=tts_request.session_id,
                        request_id=tts_request.request_id,
                        text=tts_request.text,
                    )
                else:
                    error_text = response.text
                    logger.error(
                        f"TTS service error: {response.status_code}, {error_text}"
                    )
                    raise Exception(f"TTS service error: {response.status_code}")
        except Exception as e:
            logger.error(f"Error in TTS request: {str(e)}")
            raise

    def _analyze_audio_data(self, audio_data: bytes) -> tuple:
        """Extract duration and sample rate from WAV audio data"""
        try:
            with io.BytesIO(audio_data) as audio_io:
                with wave.open(audio_io, "rb") as wav_file:
                    frames = wav_file.getnframes()
                    rate = wav_file.getframerate()
                    duration = frames / float(rate)
                    return duration, rate
        except Exception as e:
            logger.warning(f"Could not analyze audio data: {str(e)}")
            # Return default values
            return 1.0, 16000

    async def clean_session(self, session_id: str):
        """Clean up resources for a session"""
        if session_id in self.session_info:
            # Clear audio queue
            queue = self.session_info[session_id]["audio_queue"]
            while not queue.empty():
                try:
                    queue.get_nowait()
                    queue.task_done()
                except asyncio.QueueEmpty:
                    break

            # Remove session info
            del self.session_info[session_id]
