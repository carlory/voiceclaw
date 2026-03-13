"""Tests for TTS engine."""

import tempfile
from pathlib import Path

import pytest

from src.config import settings
from src.tts.qwen_tts import SynthesisResult, TTSEngine


class TestTTSEngine:
    """Tests for TTSEngine class."""

    def test_init_default_model(self) -> None:
        """Test engine initialization with default model."""
        engine = TTSEngine()
        assert engine.model_name == settings.tts_model
        assert engine.speaker == settings.tts_speaker

    def test_init_custom_model(self) -> None:
        """Test engine initialization with custom model."""
        engine = TTSEngine(model_name="custom-model", speaker="custom-speaker")
        assert engine.model_name == "custom-model"
        assert engine.speaker == "custom-speaker"

    def test_synthesize_basic(self) -> None:
        """Test basic text synthesis."""
        engine = TTSEngine()
        result = engine.synthesize("你好世界")

        assert isinstance(result, SynthesisResult)
        assert isinstance(result.audio, bytes)
        assert result.sample_rate == settings.sample_rate

    def test_synthesize_with_language(self) -> None:
        """Test synthesis with language code."""
        engine = TTSEngine()
        result = engine.synthesize("Hello world", lang_code="en")

        assert isinstance(result, SynthesisResult)
        assert isinstance(result.audio, bytes)

    def test_synthesize_empty_text(self) -> None:
        """Test that empty text raises ValueError."""
        engine = TTSEngine()
        with pytest.raises(ValueError, match="Text cannot be empty"):
            engine.synthesize("")

    def test_synthesize_whitespace_only(self) -> None:
        """Test that whitespace-only text raises ValueError."""
        engine = TTSEngine()
        with pytest.raises(ValueError, match="Text cannot be empty"):
            engine.synthesize("   ")

    def test_synthesize_to_file(self) -> None:
        """Test synthesis to file."""
        engine = TTSEngine()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_output.wav"
            result_path = engine.synthesize_to_file(
                "测试文本",
                output_path,
                lang_code="zh",
            )

            assert result_path.exists()
            assert result_path.stat().st_size > 0

    def test_get_model_path(self) -> None:
        """Test model path conversion."""
        engine = TTSEngine(model_name="Qwen/Qwen3-TTS-1.7B")
        path = engine._get_model_path()
        assert path == "mlx-community/Qwen3-TTS-1.7B-4bit"

    def test_get_model_path_mlx_format(self) -> None:
        """Test model path with MLX format already."""
        engine = TTSEngine(model_name="mlx-community/Qwen3-TTS-12Hz-0.6B-Base-4bit")
        path = engine._get_model_path()
        assert path == "mlx-community/Qwen3-TTS-12Hz-0.6B-Base-4bit"
