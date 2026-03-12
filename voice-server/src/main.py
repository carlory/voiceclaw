"""FastAPI application entry point for VoiceClaw server."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    logger.info(f"Starting VoiceClaw server on {settings.host}:{settings.port}")
    logger.info(f"ASR model: {settings.asr_model}")
    logger.info(f"TTS model: {settings.tts_model}")
    
    # TODO: Initialize ASR model
    # TODO: Initialize TTS model
    
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
