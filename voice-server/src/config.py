"""Configuration management for VoiceClaw server."""

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Find .env file
ENV_FILE = Path(__file__).parent.parent / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE) if ENV_FILE.exists() else ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server
    host: str = Field(default="127.0.0.1", description="Server host")
    port: int = Field(default=8765, description="Server port")
    debug: bool = Field(default=False, description="Debug mode")

    # OpenClaw Gateway
    openclaw_gateway_url: str = Field(
        default="http://127.0.0.1:18789",
        description="OpenClaw Gateway URL",
    )
    openclaw_gateway_token: Optional[str] = Field(
        default=None,
        description="OpenClaw Gateway auth token",
    )
    openclaw_model: str = Field(default="openclaw", description="OpenClaw model name")

    # Qwen3-ASR
    asr_model: str = Field(
        default="Qwen/Qwen3-ASR-1.7B",
        description="Qwen3-ASR model name or path",
    )
    asr_device: str = Field(default="mps", description="Device for ASR inference")

    # Qwen3-TTS
    tts_model: str = Field(
        default="Qwen/Qwen3-TTS-1.7B",
        description="Qwen3-TTS model name or path",
    )
    tts_device: str = Field(default="mps", description="Device for TTS inference")
    tts_speaker: str = Field(default="default", description="Default TTS speaker")

    # VAD
    vad_threshold: float = Field(default=0.5, description="VAD threshold")
    vad_min_silence_ms: int = Field(default=500, description="Min silence duration for VAD")

    # Audio
    sample_rate: int = Field(default=16000, description="Audio sample rate")
    audio_channels: int = Field(default=1, description="Audio channels")


# Global settings instance
settings = Settings()
