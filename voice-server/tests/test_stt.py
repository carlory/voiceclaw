"""Tests for ASR engine."""

import tempfile
from pathlib import Path

import numpy as np
import pytest
import scipy.io.wavfile as wavfile

from src.config import settings
from src.stt.qwen_asr import ASREngine, TranscriptionResult


@pytest.fixture
def sample_audio() -> bytes:
    """Generate a sample WAV audio file for testing."""
    # Generate 1 second of silence at 16kHz
    sample_rate = 16000
    duration = 1.0
    samples = int(sample_rate * duration)
    audio = np.zeros(samples, dtype=np.int16)

    # Save to temp WAV file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        wavfile.write(f.name, sample_rate, audio)
        path = f.name

    # Read back as bytes
    with open(path, "rb") as f:
        data = f.read()

    Path(path).unlink()
    return data


@pytest.fixture
def sample_audio_path(sample_audio: bytes) -> str:
    """Get a temp file path with sample audio."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(sample_audio)
        return f.name


class TestASREngine:
    """Tests for ASREngine class."""

    def test_init_default_model(self) -> None:
        """Test engine initialization with default model."""
        engine = ASREngine()
        assert engine.model_name == settings.asr_model

    def test_init_custom_model(self) -> None:
        """Test engine initialization with custom model."""
        engine = ASREngine(model_name="custom-model")
        assert engine.model_name == "custom-model"

    def test_transcribe_with_bytes(self, sample_audio: bytes) -> None:
        """Test transcription with raw audio bytes."""
        engine = ASREngine()
        # This will use mock mode since mlx-audio may not be installed
        result = engine.transcribe(sample_audio, language="Chinese")

        assert isinstance(result, TranscriptionResult)
        assert isinstance(result.text, str)
        assert result.language == "Chinese"

    def test_transcribe_with_path(self, sample_audio_path: str) -> None:
        """Test transcription with file path."""
        engine = ASREngine()
        result = engine.transcribe(sample_audio_path, language="Chinese")

        assert isinstance(result, TranscriptionResult)
        assert isinstance(result.text, str)

        # Cleanup
        Path(sample_audio_path).unlink(missing_ok=True)

    def test_transcribe_with_numpy(self) -> None:
        """Test transcription with numpy array."""
        engine = ASREngine()
        audio = np.zeros(16000, dtype=np.int16)  # 1 second of silence
        result = engine.transcribe(audio, language="Chinese")

        assert isinstance(result, TranscriptionResult)
        assert isinstance(result.text, str)

    def test_unsupported_audio_type(self) -> None:
        """Test that unsupported audio types raise ValueError."""
        engine = ASREngine()
        with pytest.raises(ValueError, match="Unsupported audio type"):
            engine.transcribe(12345)  # type: ignore

    def test_get_model_path(self) -> None:
        """Test model path conversion."""
        engine = ASREngine(model_name="Qwen/Qwen3-ASR-1.7B")
        path = engine._get_model_path()
        assert path == "mlx-community/Qwen3-ASR-1.7B-8bit"

    def test_get_model_path_mlx_format(self) -> None:
        """Test model path with MLX format already."""
        engine = ASREngine(model_name="mlx-community/Qwen3-ASR-0.6B-8bit")
        path = engine._get_model_path()
        assert path == "mlx-community/Qwen3-ASR-0.6B-8bit"
