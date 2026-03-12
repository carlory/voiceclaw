"""Tests for health check endpoint."""

import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client() -> TestClient:
    """Create a test client."""
    return TestClient(app)


def test_health_check(client: TestClient) -> None:
    """Test health check endpoint returns ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_root_endpoint(client: TestClient) -> None:
    """Test root endpoint returns app info."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "VoiceClaw"
    assert data["version"] == "0.1.0"
