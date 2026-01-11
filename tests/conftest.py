"""
Pytest configuration and fixtures for PENNY Knowledge Core tests.
"""

import asyncio
from collections.abc import AsyncGenerator, Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from fastapi.testclient import TestClient

from penny_knowledge_core.config import Settings
from penny_knowledge_core.router import FleetRouter
from penny_knowledge_core.server.main import app


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings() -> Settings:
    """Create test settings."""
    return Settings(
        gateway_host="127.0.0.1",
        gateway_port=8000,
        log_level="DEBUG",
        debug=True,
        fleet_personal_url="http://mock-heart:31009",
        fleet_work_url="http://mock-heart:31009",
        fleet_research_url="http://mock-heart:31009",
        default_profile="personal",
        redis_url="redis://localhost:6379/1",
    )


@pytest.fixture
def mock_httpx_client() -> AsyncMock:
    """Create a mock httpx async client."""
    client = AsyncMock(spec=httpx.AsyncClient)

    # Default response
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {}
    mock_response.content = b"{}"
    mock_response.raise_for_status = MagicMock()

    client.request.return_value = mock_response
    client.get.return_value = mock_response
    client.post.return_value = mock_response
    client.put.return_value = mock_response
    client.delete.return_value = mock_response

    return client


@pytest.fixture
async def mock_router(
    test_settings: Settings,
    mock_httpx_client: AsyncMock,
) -> AsyncGenerator[FleetRouter, None]:
    """Create a fleet router with mocked HTTP clients."""
    router = FleetRouter(test_settings)

    # Inject mock clients
    for name in ["personal", "work", "research"]:
        router._clients[name] = mock_httpx_client

    yield router

    # Cleanup
    router._clients.clear()


@pytest.fixture
def test_client() -> TestClient:
    """Create FastAPI test client."""
    return TestClient(app)


# =============================================================================
# Mock Response Factories
# =============================================================================


def make_space_response(
    space_id: str = "space_123",
    name: str = "Test Space",
) -> dict[str, Any]:
    """Create a mock space response."""
    return {
        "id": space_id,
        "name": name,
        "icon": "📁",
        "isPersonal": False,
    }


def make_object_response(
    object_id: str = "obj_123",
    space_id: str = "space_123",
    type_id: str = "type_123",
    name: str = "Test Object",
) -> dict[str, Any]:
    """Create a mock object response."""
    return {
        "id": object_id,
        "spaceId": space_id,
        "typeId": type_id,
        "name": name,
        "details": {},
    }


def make_type_response(
    type_id: str = "type_123",
    name: str = "Test Type",
) -> dict[str, Any]:
    """Create a mock type response."""
    return {
        "id": type_id,
        "key": name.lower().replace(" ", "_"),
        "name": name,
        "layout": "basic",
    }


def make_relation_response(
    relation_id: str = "rel_123",
    name: str = "Test Relation",
) -> dict[str, Any]:
    """Create a mock relation response."""
    return {
        "id": relation_id,
        "key": name.lower().replace(" ", "_"),
        "name": name,
        "format": "shorttext",
    }


def make_search_response(
    objects: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create a mock search response."""
    return {
        "objects": objects or [],
        "total": len(objects or []),
        "hasMore": False,
    }


def make_stats_response() -> dict[str, Any]:
    """Create a mock stats response."""
    return {
        "totalObjects": 100,
        "totalTypes": 10,
        "totalRelations": 25,
        "totalSpaces": 3,
        "objectsByType": {"Note": 50, "Task": 30, "Bookmark": 20},
        "storageBytes": 1024 * 1024 * 50,
    }
