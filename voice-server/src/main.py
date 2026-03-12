"""FastAPI application entry point for VoiceClaw server."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.stt.qwen_asr import ASREngine, TranscriptionResult, get_asr_engine

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# Global engine instances
_asr_engine: ASREngine | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    global _asr_engine
    
    logger.info(f"Starting VoiceClaw server on {settings.host}:{settings.port}")
    logger.info(f"ASR model: {settings.asr_model}")
    logger.info(f"TTS model: {settings.tts_model}")
    
    # Initialize ASR engine
    _asr_engine = get_asr_engine()
    
    yield
    
    logger.info("Shutting down VoiceClaw server")


app = FastAPI(
    title="VoiceClaw",
    description="Voice interface for OpenClaw using Qwen3-ASR/TTS with MLX",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check() -> dict[str, bool]:
    """Health check endpoint."""
    return {"ok": True}


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "name": "VoiceClaw",
        "version": "0.1.0",
        "description": "Voice interface for OpenClaw",
    }


@app.post("/stt", response_model=TranscriptionResult)
async def speech_to_text(
    file: UploadFile = File(..., description="Audio file (WAV/MP3/OGG)"),
    language: str = "Chinese",
) -> TranscriptionResult:
    """Transcribe audio to text using Qwen3-ASR.
    
    Args:
        file: Audio file upload.
        language: Language code (e.g., "Chinese", "English").
    
    Returns:
        Transcription result with text.
    
    Raises:
        HTTPException: If transcription fails.
    """
    if _asr_engine is None:
        raise HTTPException(status_code=503, detail="ASR engine not initialized")
    
    try:
        audio_bytes = await file.read()
        result = _asr_engine.transcribe(audio_bytes, language=language)
        logger.info(f"Transcribed: {result.text[:50]}...")
        return result
    except Exception as e:
        logger.error(f"STT failed: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")


def run_server() -> None:
    """Run the server using uvicorn."""
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    run_server()
