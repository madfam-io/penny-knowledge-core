#!/usr/bin/env python3
"""
Mock AnyType Heart Server

Provides a mock API that mimics AnyType Heart responses for development
and testing without requiring actual AnyType credentials.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Mock AnyType Heart")

# In-memory storage
spaces: dict[str, dict[str, Any]] = {}
objects: dict[str, dict[str, Any]] = {}
types: dict[str, dict[str, Any]] = {}
relations: dict[str, dict[str, Any]] = {}


def gen_id(prefix: str = "") -> str:
    """Generate a mock ID."""
    return f"{prefix}{uuid.uuid4().hex[:12]}"


# =============================================================================
# Health Check
# =============================================================================


@app.get("/v1/health")
async def health_check() -> dict[str, Any]:
    """Health check endpoint."""
    return {"status": "healthy", "version": "mock-1.0.0"}


# =============================================================================
# Spaces
# =============================================================================


class CreateSpaceRequest(BaseModel):
    name: str
    icon: str | None = None


@app.get("/v1/spaces")
async def list_spaces() -> dict[str, Any]:
    """List all spaces."""
    return {"spaces": list(spaces.values())}


@app.post("/v1/spaces")
async def create_space(request: CreateSpaceRequest) -> dict[str, Any]:
    """Create a new space."""
    space_id = gen_id("space_")
    space = {
        "id": space_id,
        "name": request.name,
        "icon": request.icon,
        "isPersonal": False,
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    spaces[space_id] = space
    return space


# =============================================================================
# Types
# =============================================================================


class CreateTypeRequest(BaseModel):
    name: str
    key: str | None = None
    layout: str = "basic"
    description: str | None = None
    icon: str | None = None
    recommendedRelations: list[str] = []


@app.get("/v1/spaces/{space_id}/types")
async def list_types(space_id: str) -> dict[str, Any]:
    """List all types in a space."""
    space_types = [t for t in types.values() if t.get("spaceId") == space_id]
    return {"types": space_types}


@app.post("/v1/spaces/{space_id}/types")
async def create_type(space_id: str, request: CreateTypeRequest) -> dict[str, Any]:
    """Create a new type."""
    type_id = gen_id("type_")
    typ = {
        "id": type_id,
        "spaceId": space_id,
        "name": request.name,
        "key": request.key or request.name.lower().replace(" ", "_"),
        "layout": request.layout,
        "description": request.description,
        "icon": request.icon,
        "recommendedRelations": request.recommendedRelations,
    }
    types[type_id] = typ
    return typ


# =============================================================================
# Relations
# =============================================================================


class CreateRelationRequest(BaseModel):
    name: str
    key: str | None = None
    format: str = "shorttext"
    description: str | None = None
    maxCount: int = 0
    selectOptions: list[dict[str, Any]] = []


@app.get("/v1/spaces/{space_id}/relations")
async def list_relations(space_id: str) -> dict[str, Any]:
    """List all relations in a space."""
    space_relations = [r for r in relations.values() if r.get("spaceId") == space_id]
    return {"relations": space_relations}


@app.post("/v1/spaces/{space_id}/relations")
async def create_relation(space_id: str, request: CreateRelationRequest) -> dict[str, Any]:
    """Create a new relation."""
    rel_id = gen_id("rel_")
    rel = {
        "id": rel_id,
        "spaceId": space_id,
        "name": request.name,
        "key": request.key or request.name.lower().replace(" ", "_"),
        "format": request.format,
        "description": request.description,
        "maxCount": request.maxCount,
        "selectOptions": request.selectOptions,
    }
    relations[rel_id] = rel
    return rel


# =============================================================================
# Objects
# =============================================================================


class CreateObjectRequest(BaseModel):
    typeId: str
    name: str
    icon: str | None = None
    details: dict[str, Any] = {}


@app.get("/v1/spaces/{space_id}/objects")
async def list_objects(space_id: str) -> dict[str, Any]:
    """List all objects in a space."""
    space_objects = [o for o in objects.values() if o.get("spaceId") == space_id]
    return {"objects": space_objects}


@app.post("/v1/spaces/{space_id}/objects")
async def create_object(space_id: str, request: CreateObjectRequest) -> dict[str, Any]:
    """Create a new object."""
    obj_id = gen_id("obj_")
    obj = {
        "id": obj_id,
        "spaceId": space_id,
        "typeId": request.typeId,
        "name": request.name,
        "icon": request.icon,
        "details": request.details,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    }
    objects[obj_id] = obj
    return obj


# =============================================================================
# Search
# =============================================================================


@app.get("/v1/search")
async def search(
    query: str,
    limit: int = 20,
    spaceId: str | None = None,
    typeId: str | None = None,
) -> dict[str, Any]:
    """Search objects."""
    results = []
    query_lower = query.lower()

    for obj in objects.values():
        if spaceId and obj.get("spaceId") != spaceId:
            continue
        if typeId and obj.get("typeId") != typeId:
            continue
        if query_lower in obj.get("name", "").lower():
            results.append(obj)
            if len(results) >= limit:
                break

    return {
        "objects": results,
        "total": len(results),
        "hasMore": False,
    }


# =============================================================================
# Stats
# =============================================================================


@app.get("/v1/stats")
async def get_stats() -> dict[str, Any]:
    """Get graph statistics."""
    objects_by_type: dict[str, int] = {}
    for obj in objects.values():
        type_id = obj.get("typeId", "unknown")
        objects_by_type[type_id] = objects_by_type.get(type_id, 0) + 1

    return {
        "totalObjects": len(objects),
        "totalTypes": len(types),
        "totalRelations": len(relations),
        "totalSpaces": len(spaces),
        "objectsByType": objects_by_type,
        "storageBytes": 1024 * 1024 * 10,  # Mock 10MB
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=31009)
