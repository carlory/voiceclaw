"""Qwen3-ASR speech recognition module."""

import logging
import tempfile
from pathlib import Path
from typing import Optional

import numpy as np
from pydantic import BaseModel

from src.config import settings

logger = logging.getLogger(__name__)


class TranscriptionResult(BaseModel):
    """ASR transcription result."""

    text: str
    language: Optional[str] = None
    confidence: Optional[float] = None
    segments: Optional[list[dict]] = None


class ASREngine:
    """Qwen3-ASR engine wrapper."""

    def __init__(self, model_name: Optional[str] = None) -> None:
        """Initialize ASR engine.

        Args:
            model_name: Model name or path. Defaults to settings.asr_model.
        """
        self.model_name = model_name or settings.asr_model
        self._model = None
        logger.info(f"ASR engine initialized with model: {self.model_name}")

    def _load_model(self) -> None:
        """Lazy load the model."""
        if self._model is None:
            logger.info("Loading ASR model...")
            try:
                from mlx_audio.stt import load

                # Map model name to MLX community format
                model_path = self._get_model_path()
                self._model = load(model_path)
                logger.info(f"ASR model loaded: {model_path}")
            except ImportError:
                logger.warning("mlx-audio not installed, using mock mode")
                self._model = self._mock_model()

    def _get_model_path(self) -> str:
        """Get model path in MLX format."""
        if self.model_name.startswith("mlx-community/"):
            return self.model_name
        # Convert Qwen/Qwen3-ASR-1.7B -> mlx-community/Qwen3-ASR-1.7B-8bit
        model_id = self.model_name.split("/")[-1]
        return f"mlx-community/{model_id}-8bit"

    def _mock_model(self) -> object:
        """Return a mock model for testing."""

        class MockModel:
            def generate(self, audio: str, language: str = "Chinese") -> object:
                class Result:
                    text = "【模拟识别结果】这是一段测试文本"
                    segments = []

                return Result()

        return MockModel()

    def transcribe(
        self,
        audio: bytes | str | np.ndarray,
        language: str = "Chinese",
    ) -> TranscriptionResult:
        """Transcribe audio to text.

        Args:
            audio: Audio data (bytes, file path, or numpy array).
            language: Language code. Defaults to "Chinese".

        Returns:
            Transcription result with text and metadata.
        """
        self._load_model()

        # Handle different input types
        audio_path = self._prepare_audio(audio)

        try:
            # Transcribe
            result = self._model.generate(audio_path, language=language)

            return TranscriptionResult(
                text=result.text,
                language=language,
                segments=getattr(result, "segments", None),
            )
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise RuntimeError(f"ASR transcription failed: {e}") from e
        finally:
            # Cleanup temp file if created
            if isinstance(audio_path, str) and audio_path.startswith(tempfile.gettempdir()):
                Path(audio_path).unlink(missing_ok=True)

    def _prepare_audio(self, audio: bytes | str | np.ndarray) -> str:
        """Prepare audio for transcription.

        Args:
            audio: Audio data in various formats.

        Returns:
            Path to audio file.
        """
        if isinstance(audio, str):
            # Already a file path
            return audio
        elif isinstance(audio, bytes):
            # Raw bytes - save to temp file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio)
                return f.name
        elif isinstance(audio, np.ndarray):
            # Numpy array - save as WAV
            import scipy.io.wavfile as wavfile

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                wavfile.write(f.name, settings.sample_rate, audio)
                return f.name
        else:
            raise ValueError(f"Unsupported audio type: {type(audio)}")


# Global ASR engine instance
_asr_engine: Optional[ASREngine] = None


def get_asr_engine() -> ASREngine:
    """Get or create ASR engine instance."""
    global _asr_engine
    if _asr_engine is None:
        _asr_engine = ASREngine()
    return _asr_engine
