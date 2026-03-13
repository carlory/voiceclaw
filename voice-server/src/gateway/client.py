"""OpenClaw Gateway client for LLM responses."""

import logging
from typing import Optional

import httpx

from src.config import settings

logger = logging.getLogger(__name__)


class GatewayClient:
    """Client for OpenClaw Gateway API with connection pooling."""

    def __init__(self, base_url: Optional[str] = None) -> None:
        """Initialize Gateway client.

        Args:
            base_url: Gateway base URL (default from settings)
        """
        self.base_url = base_url or settings.openclaw_gateway_url
        self.timeout = httpx.Timeout(30.0)
        self._client: Optional[httpx.AsyncClient] = None

    async def start(self) -> None:
        """Start the HTTP client for connection pooling."""
        if self._client is not None:
            return

        headers = {}
        if settings.openclaw_gateway_token:
            headers["Authorization"] = f"Bearer {settings.openclaw_gateway_token}"

        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers=headers if headers else None,
        )
        logger.debug("GatewayClient started")

    async def stop(self) -> None:
        """Stop the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.debug("GatewayClient stopped")

    async def __aenter__(self) -> "GatewayClient":
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.stop()

    @property
    def client(self) -> httpx.AsyncClient:
        """Get HTTP client."""
        if self._client is None:
            raise RuntimeError("GatewayClient not started. Call start() or use 'async with'.")
        return self._client

    async def chat(
        self,
        message: str,
        session_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Send a chat message to OpenClaw Gateway.

        Args:
            message: User message
            session_id: Optional session ID for conversation continuity
            system_prompt: Optional system prompt override

        Returns:
            Assistant response text

        Raises:
            httpx.HTTPStatusError: If HTTP request fails (4xx/5xx)
            httpx.RequestError: If connection fails
            RuntimeError: If Gateway returns an error response
        """
        # Build request payload for OpenClaw Gateway
        payload = {
            "model": settings.openclaw_model,
            "messages": [
                {"role": "user", "content": message},
            ],
        }

        if session_id:
            payload["session_id"] = session_id

        if system_prompt:
            payload["messages"].insert(0, {"role": "system", "content": system_prompt})

        logger.debug(f"Sending chat request (len={len(message)}, session={session_id})")

        # OpenClaw Gateway chat endpoint
        response = await self.client.post(
            "/v1/chat/completions",
            json=payload,
        )
        response.raise_for_status()

        # Parse response
        data = response.json()

        # Handle OpenAI-compatible response format
        if "choices" in data and len(data["choices"]) > 0:
            content = data["choices"][0].get("message", {}).get("content", "")
            return content.strip()

        # Handle simple text response
        if "response" in data:
            return data["response"].strip()

        # Handle error response
        if "error" in data:
            logger.error(f"Gateway error: {data['error']}")
            raise RuntimeError(f"Gateway error: {data['error']}")

        logger.warning(f"Unexpected Gateway response format: {data}")
        return "抱歉，我无法理解响应。"

    async def health_check(self) -> bool:
        """Check if Gateway is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            response = await self.client.get("/health")
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Gateway health check failed: {e}")
            return False


# Singleton instance
_gateway_client: Optional[GatewayClient] = None


def get_gateway_client() -> GatewayClient:
    """Get or create Gateway client singleton.

    Note: For async usage, prefer creating a new client with context manager.
    """
    global _gateway_client
    if _gateway_client is None:
        _gateway_client = GatewayClient()
    return _gateway_client
