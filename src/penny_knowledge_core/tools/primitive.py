"""
Primitive MCP tools for basic AnyType operations.

These are low-level tools that map directly to AnyType API calls.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any

from penny_knowledge_core.logging import get_logger
from penny_knowledge_core.router import FleetRouter
from penny_knowledge_core.schemas.anytype import (
    AnyTypeObject,
    AnyTypeSpace,
    GraphStats,
)
from penny_knowledge_core.schemas.tools import (
    CreateObjectInput,
    CreateObjectOutput,
    CreateSpaceInput,
    CreateSpaceOutput,
    GetGraphStatsOutput,
    ListSpacesOutput,
    SearchGlobalInput,
    SearchGlobalOutput,
)

logger = get_logger(__name__)

# Global router instance (initialized by server)
_router: FleetRouter | None = None


def set_router(router: FleetRouter) -> None:
    """Set the global router instance."""
    global _router
    _router = router


def get_router() -> FleetRouter:
    """Get the global router instance."""
    if _router is None:
        raise RuntimeError("Router not initialized. Call set_router() first.")
    return _router


async def create_space(input: CreateSpaceInput) -> CreateSpaceOutput:
    """
    Create a new AnyType Space.

    Args:
        input: Space creation parameters.

    Returns:
        CreateSpaceOutput with created space details.
    """
    router = get_router()

    logger.info("Creating space", name=input.name, profile=input.profile_name)

    payload = {
        "name": input.name,
    }
    if input.icon:
        payload["icon"] = input.icon

    response = await router.post(
        "/v1/spaces",
        profile_name=input.profile_name,
        json=payload,
    )
    data = response.json()

    space = AnyTypeSpace(
        id=data.get("id", ""),
        name=data.get("name", input.name),
        icon=data.get("icon"),
        created_at=datetime.now(timezone.utc),
    )

    logger.info("Space created", space_id=space.id, name=space.name)

    return CreateSpaceOutput(
        space=space,
        message=f"Created space '{space.name}' with ID {space.id}",
    )


async def list_spaces(profile_name: str | None = None) -> ListSpacesOutput:
    """
    List all spaces in a profile.

    Args:
        profile_name: Optional profile override.

    Returns:
        ListSpacesOutput with list of spaces.
    """
    router = get_router()

    logger.debug("Listing spaces", profile=profile_name)

    response = await router.get("/v1/spaces", profile_name=profile_name)
    data = response.json()

    spaces = [
        AnyTypeSpace(
            id=s.get("id", ""),
            name=s.get("name", ""),
            icon=s.get("icon"),
            is_personal=s.get("isPersonal", False),
        )
        for s in data.get("spaces", [])
    ]

    return ListSpacesOutput(
        spaces=spaces,
        profile=profile_name or "default",
    )


async def create_object(input: CreateObjectInput) -> CreateObjectOutput:
    """
    Create a new object in an AnyType Space.

    Args:
        input: Object creation parameters.

    Returns:
        CreateObjectOutput with created object details.
    """
    router = get_router()

    logger.info(
        "Creating object",
        name=input.name,
        type_id=input.type_id,
        space_id=input.space_id,
    )

    payload: dict[str, Any] = {
        "typeId": input.type_id,
        "name": input.name,
        "details": input.fields,
    }
    if input.icon:
        payload["icon"] = input.icon

    response = await router.post(
        f"/v1/spaces/{input.space_id}/objects",
        profile_name=input.profile_name,
        json=payload,
    )
    data = response.json()

    obj = AnyTypeObject(
        id=data.get("id", ""),
        space_id=input.space_id,
        type_id=input.type_id,
        name=data.get("name", input.name),
        icon=data.get("icon"),
        details=data.get("details", {}),
        created_at=datetime.now(timezone.utc),
    )

    logger.info("Object created", object_id=obj.id, name=obj.name)

    return CreateObjectOutput(
        object=obj,
        message=f"Created object '{obj.name}' with ID {obj.id}",
    )


async def search_global(input: SearchGlobalInput) -> SearchGlobalOutput:
    """
    Search for objects across the knowledge graph.

    Args:
        input: Search parameters.

    Returns:
        SearchGlobalOutput with matching objects.
    """
    router = get_router()

    logger.debug("Searching", query=input.query, limit=input.limit)

    params: dict[str, Any] = {
        "query": input.query,
        "limit": input.limit,
    }
    if input.space_id:
        params["spaceId"] = input.space_id
    if input.type_id:
        params["typeId"] = input.type_id

    response = await router.get(
        "/v1/search",
        profile_name=input.profile_name,
        params=params,
    )
    data = response.json()

    objects = [
        AnyTypeObject(
            id=o.get("id", ""),
            space_id=o.get("spaceId", ""),
            type_id=o.get("typeId", ""),
            name=o.get("name", ""),
            snippet=o.get("snippet"),
            details=o.get("details", {}),
        )
        for o in data.get("objects", [])
    ]

    logger.debug("Search results", count=len(objects), query=input.query)

    return SearchGlobalOutput(
        objects=objects,
        total=data.get("total", len(objects)),
        query=input.query,
    )


async def get_graph_stats(profile_name: str | None = None) -> GetGraphStatsOutput:
    """
    Get statistics about the knowledge graph.

    Args:
        profile_name: Optional profile override.

    Returns:
        GetGraphStatsOutput with graph statistics.
    """
    router = get_router()

    logger.debug("Getting graph stats", profile=profile_name)

    response = await router.get("/v1/stats", profile_name=profile_name)
    data = response.json()

    stats = GraphStats(
        total_objects=data.get("totalObjects", 0),
        total_types=data.get("totalTypes", 0),
        total_relations=data.get("totalRelations", 0),
        total_spaces=data.get("totalSpaces", 0),
        objects_by_type=data.get("objectsByType", {}),
        storage_bytes=data.get("storageBytes", 0),
    )

    return GetGraphStatsOutput(
        stats=stats,
        profile=profile_name or "default",
    )
