import asyncio
import numpy as np
from pydantic import BaseModel
import structlog

logger = structlog.getLogger(__name__)


class AudioChunk(BaseModel):
    data: bytes
    sample_rate: int
    user_id: str
    timestamp: float
    session_id: str
    is_final: bool = False


class AudioProcessor:
    def __init__(self, chunk_size_ms=20, sample_rate=16000):
        self.chunk_size_ms = chunk_size_ms
        self.sample_rate = sample_rate
        self.vad_threshold = 0.3  # Voice Activity Detection threshold
        self._processing_tasks = {}

    async def process_stream(self, audio_stream, session_id, user_id):
        """Process incoming audio stream in real-time"""

        async for chunk in audio_stream:
            # Create a task for each chunk to process concurrently
            task = asyncio.create_task(
                self._process_chunk(
                    AudioChunk(
                        data=chunk,
                        sample_rate=self.sample_rate,
                        user_id=user_id,
                        timestamp=asyncio.get_event_loop().time(),
                        session_id=session_id,
                    )
                )
            )
            self._processing_tasks[session_id] = task

    async def _process_chunk(self, chunk: AudioChunk):
        """Process a single audio chunk with various enhancement techniques"""
        try:
            # Convert bytes to numpy array
            audio_data = np.frombuffer(chunk.data, dtype=np.int16)

            # Apply noise reduction
            processed_data = await self._reduce_noise(audio_data)

            # Apply automatic gain control
            processed_data = await self._apply_gain_control(processed_data)

            # Check voice activity
            is_speech = await self._detect_voice_activity(processed_data)

            if is_speech:
                # Pack back into bytes
                processed_bytes = processed_data.astype(np.int16).tobytes()

                # Return enhanced audio
                return AudioChunk(
                    data=processed_bytes,
                    sample_rate=chunk.sample_rate,
                    user_id=chunk.user_id,
                    timestamp=chunk.timestamp,
                    session_id=chunk.session_id,
                )
            return None

        except Exception as e:
            logger.error(f"Error processing audio chunk: {str(e)}")
            return None

    async def _reduce_noise(self, audio_data):
        """Apply noise reduction algorithm"""
        # Placeholder for actual noise reduction implementation
        # In production, use a proper noise reduction library
        return audio_data

    async def _apply_gain_control(self, audio_data):
        """Apply automatic gain control to normalize volume"""
        # Simple normalization example (actual AGC would be more complex)
        if audio_data.size > 0:
            max_amplitude = np.max(np.abs(audio_data))
            if max_amplitude > 0:
                gain_factor = 0.7 * 32767 / max_amplitude  # Target 70% of max amplitude
                return audio_data * min(gain_factor, 2.0)  # Limit max gain
        return audio_data

    async def _detect_voice_activity(self, audio_data):
        """Detect if audio chunk contains speech"""
        if audio_data.size > 0:
            energy = np.mean(np.abs(audio_data))
            return energy > self.vad_threshold * 32767
        return False

    async def terminate_session(self, session_id):
        """Clean up resources for a session"""
        if session_id in self._processing_tasks:
            self._processing_tasks[session_id].cancel()
            del self._processing_tasks[session_id]
