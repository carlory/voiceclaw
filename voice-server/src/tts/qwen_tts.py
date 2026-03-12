"""Qwen3-TTS speech synthesis module."""

import io
import logging
import tempfile
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from src.config import settings

logger = logging.getLogger(__name__)


class SynthesisResult(BaseModel):
    """TTS synthesis result."""

    audio: bytes
    sample_rate: int = settings.sample_rate
    format: str = "wav"
    duration_ms: Optional[float] = None


class TTSEngine:
    """Qwen3-TTS engine wrapper."""

    def __init__(self, model_name: Optional[str] = None, speaker: Optional[str] = None) -> None:
        """Initialize TTS engine.

        Args:
            model_name: Model name or path. Defaults to settings.tts_model.
            speaker: Speaker ID or voice name. Defaults to settings.tts_speaker.
        """
        self.model_name = model_name or settings.tts_model
        self.speaker = speaker or settings.tts_speaker
        self._model = None
        logger.info(f"TTS engine initialized with model: {self.model_name}, speaker: {self.speaker}")

    def _load_model(self) -> None:
        """Lazy load the model."""
        if self._model is None:
            logger.info("Loading TTS model...")
            try:
                from mlx_audio.tts import load

                model_path = self._get_model_path()
                self._model = load(model_path)
                logger.info(f"TTS model loaded: {model_path}")
            except ImportError:
                logger.warning("mlx-audio not installed, using mock mode")
                self._model = self._mock_model()

    def _get_model_path(self) -> str:
        """Get model path in MLX format."""
        if self.model_name.startswith("mlx-community/"):
            return self.model_name
        # Convert Qwen/Qwen3-TTS-1.7B -> mlx-community/Qwen3-TTS-12Hz-1.7B-Base-4bit
        model_id = self.model_name.split("/")[-1]
        return f"mlx-community/{model_id}-4bit"

    def _mock_model(self) -> object:
        """Return a mock model for testing."""

        class MockModel:
            def generate(self, text: str, lang_code: str = "zh", **kwargs) -> object:
                class Result:
                    audio = b"RIFF" + b"\x00" * 100  # Mock WAV header
                    sample_rate = 16000

                return Result()

        return MockModel()

    def synthesize(
        self,
        text: str,
        lang_code: str = "zh",
        speaker: Optional[str] = None,
    ) -> SynthesisResult:
        """Synthesize text to speech.

        Args:
            text: Text to synthesize.
            lang_code: Language code (e.g., "zh", "en"). Defaults to "zh".
            speaker: Speaker ID. Defaults to configured speaker.

        Returns:
            Synthesis result with audio data.

        Raises:
            RuntimeError: If synthesis fails.
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        self._load_model()

        speaker = speaker or self.speaker

        try:
            # Synthesize
            result = self._model.generate(text, lang_code=lang_code, speaker=speaker)

            # Calculate duration
            audio_data = result.audio if hasattr(result, "audio") else result
            duration_ms = None
            if isinstance(audio_data, bytes) and len(audio_data) > 44:
                # Rough estimate: 16kHz, 16-bit mono
                duration_ms = (len(audio_data) - 44) / 32  # 16kHz * 2 bytes = 32 bytes/ms

            return SynthesisResult(
                audio=audio_data if isinstance(audio_data, bytes) else bytes(audio_data),
                sample_rate=getattr(result, "sample_rate", settings.sample_rate),
                duration_ms=duration_ms,
            )
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            raise RuntimeError(f"TTS synthesis failed: {e}") from e

    def synthesize_to_file(
        self,
        text: str,
        output_path: str | Path,
        lang_code: str = "zh",
        speaker: Optional[str] = None,
    ) -> Path:
        """Synthesize text to speech and save to file.

        Args:
            text: Text to synthesize.
            output_path: Output file path.
            lang_code: Language code.
            speaker: Speaker ID.

        Returns:
            Path to the generated audio file.
        """
        result = self.synthesize(text, lang_code=lang_code, speaker=speaker)
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "wb") as f:
            f.write(result.audio)
        
        logger.info(f"Audio saved to {output_path}")
        return output_path


# Global TTS engine instance
_tts_engine: Optional[TTSEngine] = None


def get_tts_engine() -> TTSEngine:
    """Get or create TTS engine instance."""
    global _tts_engine
    if _tts_engine is None:
        _tts_engine = TTSEngine()
    return _tts_engine
