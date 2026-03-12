"""WebSocket handler for real-time voice communication."""

import base64
import json
import logging
import time
from enum import Enum
from typing import Optional

import numpy as np
from pydantic import BaseModel

from src.config import settings
from src.stt.qwen_asr import get_asr_engine
from src.tts.qwen_tts import get_tts_engine

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """WebSocket message types."""

    AUDIO = "audio"
    TEXT = "text"
    TRANSCRIPT = "transcript"
    RESPONSE = "response"
    ERROR = "error"
    DONE = "done"


class WSMessage(BaseModel):
    """WebSocket message format."""

    type: MessageType
    data: Optional[str] = None  # base64 for audio, text for others
    text: Optional[str] = None  # for TEXT type
    language: Optional[str] = None
    speaker: Optional[str] = None


class VoiceSession:
    """Manages a single voice session."""

    def __init__(self, websocket) -> None:
        """Initialize voice session.

        Args:
            websocket: FastAPI/Starlette WebSocket connection.
        """
        self.websocket = websocket
        self.asr_engine = get_asr_engine()
        self.tts_engine = get_tts_engine()
        self.audio_buffer: list[np.ndarray] = []
        self.is_recording = False
        self.vad_threshold = settings.vad_threshold
        self.vad_min_silence_ms = settings.vad_min_silence_ms
        self.sample_rate = settings.sample_rate
        self.last_speech_time: Optional[float] = None
        self.silence_start_time: Optional[float] = None
        logger.info(f"VoiceSession initialized for {self._get_client_info()}")

    def _get_client_info(self) -> str:
        """Get client info for logging."""
        try:
            client = self.websocket.client
            if client:
                return f"{client.host}:{client.port}"
        except AttributeError:
            pass
        return "unknown"

    async def handle_message(self, message: str) -> None:
        """Handle incoming WebSocket message."""
        try:
            data = json.loads(message)
            msg_type = data.get("type")

            if msg_type == MessageType.AUDIO:
                await self._handle_audio(data.get("data", ""))
            elif msg_type == MessageType.TEXT:
                await self._handle_text(data.get("text", ""), data.get("language", "Chinese"))
            else:
                await self._send_error(f"Unknown message type: {msg_type}")

        except json.JSONDecodeError:
            await self._send_error("Invalid JSON message")
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await self._send_error(str(e))

    async def _handle_audio(self, audio_base64: str) -> None:
        """Handle incoming audio data."""
        try:
            # Reject missing/empty base64 payloads early
            if not audio_base64:
                await self._send_error("Empty audio data")
                return

            # Decode base64 audio
            audio_bytes = base64.b64decode(audio_base64)
            if not audio_bytes:
                logger.warning("Decoded empty audio payload")
                await self._send_error("Empty audio payload")
                return

            # Convert to numpy array (assuming 16-bit PCM)
            audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
            if audio_array.size == 0:
                logger.warning("Received empty audio array after decoding")
                await self._send_error("Empty audio array")
                return

            # Add to buffer
            self.audio_buffer.append(audio_array)
            self.is_recording = True

            logger.debug(f"Received audio chunk: {len(audio_array)} samples")

            # Check for silence (simple energy-based VAD)
            current_time = time.time()
            if self._is_silence(audio_array):
                logger.debug("Silence detected")
                if self.last_speech_time is not None:
                    # Start tracking silence
                    if self.silence_start_time is None:
                        self.silence_start_time = current_time
                    elif (current_time - self.silence_start_time) * 1000 >= self.vad_min_silence_ms:
                        # Silence duration exceeded threshold, flush audio
                        logger.info(f"Silence duration ({self.vad_min_silence_ms}ms) exceeded, flushing audio")
                        await self.flush_audio()
            else:
                logger.debug("Speech detected")
                self.last_speech_time = current_time
                self.silence_start_time = None

        except Exception as e:
            logger.error(f"Error processing audio: {e}")
            await self._send_error(f"Audio processing error: {e}")

    async def _handle_text(self, text: str, language: str = "Chinese") -> None:
        """Handle incoming text (bypass STT)."""
        if not text:
            await self._send_error("Empty text")
            return

        try:
            # Send acknowledgment
            await self._send_transcript(text, language)

            # TODO: Forward to OpenClaw Gateway
            response_text = f"收到：{text}"  # Placeholder

            # Synthesize response
            await self._synthesize_and_send(response_text)

        except Exception as e:
            logger.error(f"Error processing text: {e}")
            await self._send_error(f"Text processing error: {e}")

    async def flush_audio(self) -> None:
        """Flush buffered audio and transcribe."""
        if not self.audio_buffer:
            return

        try:
            # Concatenate audio buffer
            audio_data = np.concatenate(self.audio_buffer)

            logger.info(f"Transcribing {len(audio_data)} samples ({len(audio_data) / self.sample_rate:.2f}s)")

            # Transcribe
            result = self.asr_engine.transcribe(audio_data)

            # Send transcript
            await self._send_transcript(result.text, result.language or "Chinese")

            # Clear buffer and reset VAD state
            self.audio_buffer.clear()
            self.is_recording = False
            self.last_speech_time = None
            self.silence_start_time = None

            # TODO: Forward to OpenClaw Gateway
            response_text = f"识别结果：{result.text}"  # Placeholder

            # Synthesize response
            await self._synthesize_and_send(response_text)

        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            await self._send_error(f"Transcription error: {e}")
            self.audio_buffer.clear()
            self.is_recording = False
            self.last_speech_time = None
            self.silence_start_time = None

    async def _synthesize_and_send(self, text: str) -> None:
        """Synthesize text and send audio."""
        try:
            # Synthesize
            result = self.tts_engine.synthesize(text)

            # Send as base64
            audio_base64 = base64.b64encode(result.audio).decode("utf-8")
            await self._send_message(
                MessageType.AUDIO,
                data=audio_base64,
            )

            # Send done
            await self._send_message(MessageType.DONE)

        except Exception as e:
            logger.error(f"Error synthesizing speech: {e}")
            await self._send_error(f"Synthesis error: {e}")

    def _is_silence(self, audio: np.ndarray, threshold: Optional[float] = None) -> bool:
        """Check if audio segment is silence (simple energy-based)."""
        if threshold is None:
            threshold = self.vad_threshold
        energy = np.sqrt(np.mean(audio.astype(float) ** 2))
        max_val = np.iinfo(np.int16).max
        normalized_energy = energy / max_val
        return normalized_energy < threshold

    async def _send_transcript(self, text: str, language: str) -> None:
        """Send transcription result."""
        await self._send_message(
            MessageType.TRANSCRIPT,
            text=text,
            language=language,
        )

    async def _send_message(
        self,
        msg_type: MessageType,
        data: Optional[str] = None,
        text: Optional[str] = None,
        language: Optional[str] = None,
    ) -> None:
        """Send a WebSocket message."""
        message = WSMessage(
            type=msg_type,
            data=data,
            text=text,
            language=language,
        )
        await self.websocket.send_text(message.model_dump_json(exclude_none=True))

    async def _send_error(self, message: str) -> None:
        """Send an error message."""
        await self._send_message(MessageType.ERROR, text=message)


async def websocket_handler(websocket) -> None:
    """Main WebSocket handler for FastAPI/Starlette WebSocket.

    Args:
        websocket: FastAPI/Starlette WebSocket connection.
    """
    client_info = "unknown"
    try:
        client = websocket.client
        if client:
            client_info = f"{client.host}:{client.port}"
    except AttributeError:
        pass

    logger.info(f"New WebSocket connection from {client_info}")

    session = VoiceSession(websocket)

    try:
        while True:
            # Receive message from client
            message = await websocket.receive_text()
            await session.handle_message(message)
    except Exception as e:
        # WebSocket disconnect or other error
        logger.info(f"WebSocket connection closed ({client_info}): {e}")
