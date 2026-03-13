"""Tests for WebSocket handler."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ws.handler import DEFAULT_SYSTEM_PROMPT, MessageType, VoiceSession, WSMessage


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
            assert session.session_id is None
            assert session._started is False

    def test_system_prompt(self) -> None:
        """Test system prompt is defined."""
        assert "祥子" in DEFAULT_SYSTEM_PROMPT
        assert "风趣" in DEFAULT_SYSTEM_PROMPT

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
    async def test_handle_text_with_gateway(self, mock_websocket: MagicMock) -> None:
        """Test handling text with Gateway integration."""
        with patch("src.ws.handler.get_asr_engine"), \
             patch("src.ws.handler.get_tts_engine") as mock_tts, \
             patch("src.ws.handler.GatewayClient") as mock_gateway_cls:

            # Mock GatewayClient instance
            mock_gateway = MagicMock()
            mock_gateway.start = AsyncMock()
            mock_gateway.stop = AsyncMock()
            mock_gateway.chat = AsyncMock(return_value="测试回复")
            mock_gateway_cls.return_value = mock_gateway

            # Mock TTS
            mock_tts_instance = MagicMock()
            mock_tts_instance.synthesize = MagicMock(return_value=MagicMock(audio=b"test_audio"))
            mock_tts.return_value = mock_tts_instance

            session = VoiceSession(mock_websocket)
            await session.start()

            # Handle text message
            await session.handle_message(json.dumps({"type": "text", "text": "你好"}))

            # Verify GatewayClient.chat was called with correct args
            mock_gateway.chat.assert_called_once_with(
                message="你好",
                session_id=None,
                system_prompt=DEFAULT_SYSTEM_PROMPT,
            )

            # Verify message types sent
            calls = mock_websocket.send_text.call_args_list
            message_types = [json.loads(call[0][0])["type"] for call in calls]

            assert "transcript" in message_types, "Should send transcript"
            assert "audio" in message_types, "Should send audio"
            assert "done" in message_types, "Should send done"

            await session.stop()
            mock_gateway.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_text_gateway_fallback(self, mock_websocket: MagicMock) -> None:
        """Test handling text when Gateway fails."""
        with patch("src.ws.handler.get_asr_engine"), \
             patch("src.ws.handler.get_tts_engine") as mock_tts, \
             patch("src.ws.handler.GatewayClient") as mock_gateway_cls:

            # Mock GatewayClient that raises exception
            mock_gateway = MagicMock()
            mock_gateway.start = AsyncMock()
            mock_gateway.stop = AsyncMock()
            mock_gateway.chat = AsyncMock(side_effect=Exception("Connection failed"))
            mock_gateway_cls.return_value = mock_gateway

            # Mock TTS
            mock_tts_instance = MagicMock()
            mock_tts_instance.synthesize = MagicMock(return_value=MagicMock(audio=b"fallback_audio"))
            mock_tts.return_value = mock_tts_instance

            session = VoiceSession(mock_websocket)
            await session.start()

            # Handle text message
            await session.handle_message(json.dumps({"type": "text", "text": "你好"}))

            # Verify fallback message was used
            mock_tts_instance.synthesize.assert_called()
            # The fallback message should be the one defined in _get_llm_response
            synthesize_arg = mock_tts_instance.synthesize.call_args[0][0]
            assert "连不上大脑" in synthesize_arg

            await session.stop()

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


class TestGatewayClient:
    """Tests for GatewayClient."""

    def test_import(self) -> None:
        """Test GatewayClient can be imported."""
        from src.gateway.client import GatewayClient

        client = GatewayClient(base_url="http://test:8080")
        assert client.base_url == "http://test:8080"

    @pytest.mark.asyncio
    async def test_start_stop(self) -> None:
        """Test GatewayClient start/stop lifecycle."""
        from src.gateway.client import GatewayClient

        client = GatewayClient(base_url="http://test:8080")
        assert client._client is None

        await client.start()
        assert client._client is not None

        await client.stop()
        assert client._client is None
