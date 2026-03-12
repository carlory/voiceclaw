"""Tests for WebSocket handler."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ws.handler import MessageType, VoiceSession, WSMessage


@pytest.fixture
def mock_websocket() -> MagicMock:
    """Create a mock WebSocket."""
    ws = MagicMock()
    ws.remote_address = ("127.0.0.1", 12345)
    ws.client = MagicMock()
    ws.client.host = "127.0.0.1"
    ws.client.port = 12345
    ws.send_text = AsyncMock()
    return ws


class TestWSMessage:
    """Tests for WSMessage model."""

    def test_message_type_audio(self) -> None:
        """Test AUDIO message type."""
        msg = WSMessage(type=MessageType.AUDIO, data="base64data")
        assert msg.type == MessageType.AUDIO
        assert msg.data == "base64data"

    def test_message_type_text(self) -> None:
        """Test TEXT message type."""
        msg = WSMessage(type=MessageType.TEXT, text="你好")
        assert msg.type == MessageType.TEXT
        assert msg.text == "你好"

    def test_message_type_transcript(self) -> None:
        """Test TRANSCRIPT message type."""
        msg = WSMessage(
            type=MessageType.TRANSCRIPT,
            text="识别结果",
            language="Chinese",
        )
        assert msg.type == MessageType.TRANSCRIPT
        assert msg.text == "识别结果"
        assert msg.language == "Chinese"


class TestVoiceSession:
    """Tests for VoiceSession class."""

    def test_init(self, mock_websocket: MagicMock) -> None:
        """Test session initialization."""
        with patch("src.ws.handler.get_asr_engine"), \
             patch("src.ws.handler.get_tts_engine"):
            session = VoiceSession(mock_websocket)
            
            assert session.websocket == mock_websocket
            assert session.audio_buffer == []
            assert session.is_recording is False

    @pytest.mark.asyncio
    async def test_handle_text_empty(self, mock_websocket: MagicMock) -> None:
        """Test handling empty text."""
        with patch("src.ws.handler.get_asr_engine"), \
             patch("src.ws.handler.get_tts_engine"):
            session = VoiceSession(mock_websocket)
            
            await session.handle_message(json.dumps({"type": "text", "text": ""}))
            
            # Should send error
            mock_websocket.send_text.assert_called_once()
            call_args = mock_websocket.send_text.call_args[0][0]
            response = json.loads(call_args)
            assert response["type"] == "error"

    @pytest.mark.asyncio
    async def test_handle_unknown_type(self, mock_websocket: MagicMock) -> None:
        """Test handling unknown message type."""
        with patch("src.ws.handler.get_asr_engine"), \
             patch("src.ws.handler.get_tts_engine"):
            session = VoiceSession(mock_websocket)
            
            await session.handle_message(json.dumps({"type": "unknown"}))
            
            # Should send error
            mock_websocket.send_text.assert_called_once()
            call_args = mock_websocket.send_text.call_args[0][0]
            response = json.loads(call_args)
            assert response["type"] == "error"
            assert "Unknown message type" in response["text"]

    @pytest.mark.asyncio
    async def test_handle_invalid_json(self, mock_websocket: MagicMock) -> None:
        """Test handling invalid JSON."""
        with patch("src.ws.handler.get_asr_engine"), \
             patch("src.ws.handler.get_tts_engine"):
            session = VoiceSession(mock_websocket)
            
            await session.handle_message("not valid json")
            
            # Should send error
            mock_websocket.send_text.assert_called_once()
            call_args = mock_websocket.send_text.call_args[0][0]
            response = json.loads(call_args)
            assert response["type"] == "error"
            assert "Invalid JSON" in response["text"]
