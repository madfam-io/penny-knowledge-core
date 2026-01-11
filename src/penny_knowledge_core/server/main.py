"""
Main FastAPI application and MCP server for PENNY Knowledge Core.

This is the central gateway that routes requests to the Hydra fleet.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from mcp.server import Server
from mcp.server.fastmcp import FastMCP
from mcp.types import Tool, TextContent

from penny_knowledge_core import __version__
from penny_knowledge_core.config import get_settings
from penny_knowledge_core.logging import configure_logging, get_logger
from penny_knowledge_core.router import FleetRouter, get_current_profile
from penny_knowledge_core.schemas.manifest import OntologyManifest
from penny_knowledge_core.schemas.tools import (
    CreateObjectInput,
    CreateSpaceInput,
    EnsureOntologyInput,
    SearchGlobalInput,
    SmartIngestInput,
    SwitchProfileInput,
    DailyBriefingInput,
)
from penny_knowledge_core.tools import primitive
from penny_knowledge_core.tools.composite import daily_briefing, ensure_ontology, smart_ingest
from penny_knowledge_core.tools.profile import switch_profile

logger = get_logger(__name__)

# Global router instance
_router: FleetRouter | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.

    Initializes the fleet router on startup and closes it on shutdown.
    """
    global _router

    configure_logging()
    settings = get_settings()

    logger.info(
        "Starting PENNY Knowledge Core",
        version=__version__,
        debug=settings.debug,
    )

    # Initialize fleet router
    _router = FleetRouter(settings)
    await _router._init_clients()
    primitive.set_router(_router)

    logger.info("Fleet router initialized")

    yield

    # Cleanup
    if _router:
        await _router.close()
        logger.info("Fleet router closed")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application.
    """
    settings = get_settings()

    app = FastAPI(
        title="PENNY Knowledge Core",
        description="Persistent Memory and Ontological Architect for the PENNY ecosystem",
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    # CORS middleware for development
    if settings.debug:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    return app


# Create the FastAPI app
app = create_app()

# Create the MCP server
mcp = FastMCP("penny-knowledge-core")


# =============================================================================
# Health & Status Endpoints
# =============================================================================


@app.get("/health")
async def health_check() -> dict[str, Any]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": __version__,
        "profile": get_current_profile().profile_name,
    }


@app.get("/status")
async def get_status() -> dict[str, Any]:
    """Get detailed status of the gateway and fleet."""
    if not _router:
        raise HTTPException(status_code=503, detail="Router not initialized")

    fleet_status = await _router.get_all_profiles_status()
    settings = get_settings()

    return {
        "version": __version__,
        "current_profile": get_current_profile().profile_name,
        "default_profile": settings.default_profile,
        "fleet": fleet_status,
    }


# =============================================================================
# MCP Tools Registration
# =============================================================================


@mcp.tool()
async def mcp_switch_profile(profile_name: str) -> str:
    """
    Switch the active profile for subsequent operations.

    Args:
        profile_name: Profile to switch to ('personal', 'work', or 'research')

    Returns:
        Confirmation message
    """
    result = await switch_profile(SwitchProfileInput(profile_name=profile_name))
    return result.message


@mcp.tool()
async def mcp_create_space(name: str, icon: str | None = None, profile_name: str | None = None) -> str:
    """
    Create a new AnyType Space.

    Args:
        name: Name for the new space
        icon: Optional emoji icon
        profile_name: Target profile (defaults to active profile)

    Returns:
        Confirmation message with space ID
    """
    result = await primitive.create_space(
        CreateSpaceInput(name=name, icon=icon, profile_name=profile_name)
    )
    return f"{result.message}\n\nSpace ID: {result.space.id}"


@mcp.tool()
async def mcp_list_spaces(profile_name: str | None = None) -> str:
    """
    List all spaces in a profile.

    Args:
        profile_name: Target profile (defaults to active profile)

    Returns:
        List of spaces
    """
    result = await primitive.list_spaces(profile_name)
    if not result.spaces:
        return f"No spaces found in '{result.profile}' profile"

    lines = [f"Spaces in '{result.profile}' profile:"]
    for space in result.spaces:
        icon = space.icon or "📁"
        lines.append(f"  {icon} {space.name} (ID: {space.id})")
    return "\n".join(lines)


@mcp.tool()
async def mcp_create_object(
    space_id: str,
    type_id: str,
    name: str,
    fields: dict[str, Any] | None = None,
    icon: str | None = None,
    profile_name: str | None = None,
) -> str:
    """
    Create a new object in an AnyType Space.

    Args:
        space_id: Target space ID
        type_id: Object type ID
        name: Object name/title
        fields: Optional field values as key-value pairs
        icon: Optional emoji icon
        profile_name: Target profile

    Returns:
        Confirmation message with object ID
    """
    result = await primitive.create_object(
        CreateObjectInput(
            space_id=space_id,
            type_id=type_id,
            name=name,
            fields=fields or {},
            icon=icon,
            profile_name=profile_name,
        )
    )
    return f"{result.message}\n\nObject ID: {result.object.id}"


@mcp.tool()
async def mcp_search(
    query: str,
    space_id: str | None = None,
    type_id: str | None = None,
    limit: int = 20,
    profile_name: str | None = None,
) -> str:
    """
    Search for objects across the knowledge graph.

    Args:
        query: Search query
        space_id: Optional space filter
        type_id: Optional type filter
        limit: Maximum results (default 20)
        profile_name: Target profile

    Returns:
        Search results
    """
    result = await primitive.search_global(
        SearchGlobalInput(
            query=query,
            space_id=space_id,
            type_id=type_id,
            limit=limit,
            profile_name=profile_name,
        )
    )

    if not result.objects:
        return f"No results found for '{query}'"

    lines = [f"Found {result.total} results for '{query}':"]
    for obj in result.objects:
        lines.append(f"  - {obj.name} (Type: {obj.type_id}, ID: {obj.id})")
    return "\n".join(lines)


@mcp.tool()
async def mcp_get_graph_stats(profile_name: str | None = None) -> str:
    """
    Get statistics about the knowledge graph.

    Args:
        profile_name: Target profile

    Returns:
        Graph statistics
    """
    result = await primitive.get_graph_stats(profile_name)
    stats = result.stats

    lines = [
        f"Graph Statistics ({result.profile}):",
        f"  Spaces: {stats.total_spaces}",
        f"  Types: {stats.total_types}",
        f"  Relations: {stats.total_relations}",
        f"  Objects: {stats.total_objects}",
        f"  Storage: {stats.storage_bytes / 1024 / 1024:.2f} MB",
    ]

    if stats.objects_by_type:
        lines.append("  Objects by Type:")
        for type_name, count in list(stats.objects_by_type.items())[:10]:
            lines.append(f"    - {type_name}: {count}")

    return "\n".join(lines)


@mcp.tool()
async def mcp_ensure_ontology(
    space_id: str,
    manifest_json: str,
    dry_run: bool = False,
    profile_name: str | None = None,
) -> str:
    """
    Ensure a set of Types and Relations exists in the knowledge graph.

    This is the core "Ontological Architect" capability. Pass a JSON manifest
    defining the types and relations that should exist.

    Args:
        space_id: Target space ID
        manifest_json: JSON string containing the ontology manifest
        dry_run: If true, only report what would be created
        profile_name: Target profile

    Returns:
        Summary of created/skipped elements
    """
    import json

    try:
        manifest_data = json.loads(manifest_json)
        manifest = OntologyManifest(**manifest_data)
    except Exception as e:
        return f"Error parsing manifest: {e}"

    result = await ensure_ontology(
        EnsureOntologyInput(
            space_id=space_id,
            manifest=manifest,
            dry_run=dry_run,
            profile_name=profile_name,
        )
    )

    lines = [result.message]

    if result.created_relations:
        lines.append(f"\nCreated Relations: {', '.join(result.created_relations)}")
    if result.created_types:
        lines.append(f"Created Types: {', '.join(result.created_types)}")
    if result.skipped_relations:
        lines.append(f"Existing Relations: {', '.join(result.skipped_relations)}")
    if result.skipped_types:
        lines.append(f"Existing Types: {', '.join(result.skipped_types)}")

    return "\n".join(lines)


@mcp.tool()
async def mcp_smart_ingest(
    content: str,
    space_id: str,
    type_hint: str | None = None,
    auto_link: bool = True,
    profile_name: str | None = None,
) -> str:
    """
    Intelligently ingest raw content into structured objects.

    Args:
        content: Raw text, URL, or content to ingest
        space_id: Target space ID
        type_hint: Suggested type for the content
        auto_link: Automatically link to related objects
        profile_name: Target profile

    Returns:
        Summary of ingested content
    """
    result = await smart_ingest(
        SmartIngestInput(
            content=content,
            space_id=space_id,
            type_hint=type_hint,
            auto_link=auto_link,
            profile_name=profile_name,
        )
    )

    lines = [result.message]
    for obj in result.created_objects:
        lines.append(f"  - {obj.name} (ID: {obj.id})")
    return "\n".join(lines)


@mcp.tool()
async def mcp_daily_briefing(
    hours: int = 24,
    space_id: str | None = None,
    profile_name: str | None = None,
) -> str:
    """
    Generate a markdown summary of recent changes.

    Args:
        hours: Lookback period in hours (default 24)
        space_id: Optional space filter
        profile_name: Target profile

    Returns:
        Markdown-formatted daily briefing
    """
    result = await daily_briefing(
        DailyBriefingInput(
            hours=hours,
            space_id=space_id,
            profile_name=profile_name,
        )
    )
    return result.summary


# =============================================================================
# REST API Endpoints (for direct access)
# =============================================================================


@app.post("/api/v1/profile/switch")
async def api_switch_profile(input: SwitchProfileInput) -> dict[str, Any]:
    """Switch the active profile."""
    result = await switch_profile(input)
    return result.model_dump()


@app.post("/api/v1/spaces")
async def api_create_space(input: CreateSpaceInput) -> dict[str, Any]:
    """Create a new space."""
    result = await primitive.create_space(input)
    return result.model_dump()


@app.get("/api/v1/spaces")
async def api_list_spaces(profile_name: str | None = None) -> dict[str, Any]:
    """List all spaces."""
    result = await primitive.list_spaces(profile_name)
    return result.model_dump()


@app.post("/api/v1/objects")
async def api_create_object(input: CreateObjectInput) -> dict[str, Any]:
    """Create a new object."""
    result = await primitive.create_object(input)
    return result.model_dump()


@app.post("/api/v1/search")
async def api_search(input: SearchGlobalInput) -> dict[str, Any]:
    """Search objects."""
    result = await primitive.search_global(input)
    return result.model_dump()


@app.get("/api/v1/stats")
async def api_get_stats(profile_name: str | None = None) -> dict[str, Any]:
    """Get graph statistics."""
    result = await primitive.get_graph_stats(profile_name)
    return result.model_dump()


@app.post("/api/v1/ontology/ensure")
async def api_ensure_ontology(input: EnsureOntologyInput) -> dict[str, Any]:
    """Ensure ontology exists."""
    result = await ensure_ontology(input)
    return result.model_dump()


# =============================================================================
# Main Entry Point
# =============================================================================


def main() -> None:
    """Run the server."""
    configure_logging()
    settings = get_settings()

    logger.info(
        "Starting server",
        host=settings.gateway_host,
        port=settings.gateway_port,
    )

    uvicorn.run(
        "penny_knowledge_core.server.main:app",
        host=settings.gateway_host,
        port=settings.gateway_port,
        reload=settings.reload,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
