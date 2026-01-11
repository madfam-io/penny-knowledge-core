"""
Composite MCP tools for high-level agentic operations.

These tools encapsulate complex multi-step logic to reduce
LLM hallucination and context usage.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from typing import Any

from penny_knowledge_core.logging import get_logger
from penny_knowledge_core.router import FleetRouter
from penny_knowledge_core.schemas.anytype import AnyTypeObject, AnyTypeRelation, AnyTypeType
from penny_knowledge_core.schemas.manifest import OntologyManifest, RelationDefinition, TypeDefinition
from penny_knowledge_core.schemas.tools import (
    DailyBriefingInput,
    DailyBriefingOutput,
    EnsureOntologyInput,
    EnsureOntologyOutput,
    OntologyDiff,
    SmartIngestInput,
    SmartIngestOutput,
)
from penny_knowledge_core.tools.primitive import get_router

logger = get_logger(__name__)

# Fuzzy matching threshold for relation deduplication
FUZZY_MATCH_THRESHOLD = 0.85


def _fuzzy_match(name1: str, name2: str) -> float:
    """
    Calculate fuzzy match ratio between two names.

    Used for relation deduplication to prevent "Status" vs "status" duplication.
    """
    return SequenceMatcher(None, name1.lower(), name2.lower()).ratio()


def _find_matching_relation(
    name: str,
    existing_relations: list[AnyTypeRelation],
) -> AnyTypeRelation | None:
    """
    Find an existing relation that fuzzy-matches the given name.

    Prevents schema pollution by reusing existing relations.
    """
    for rel in existing_relations:
        if _fuzzy_match(name, rel.name) >= FUZZY_MATCH_THRESHOLD:
            logger.debug(
                "Found matching relation",
                requested=name,
                existing=rel.name,
                match_ratio=_fuzzy_match(name, rel.name),
            )
            return rel
    return None


def _find_matching_type(
    name: str,
    existing_types: list[AnyTypeType],
) -> AnyTypeType | None:
    """Find an existing type that fuzzy-matches the given name."""
    for typ in existing_types:
        if _fuzzy_match(name, typ.name) >= FUZZY_MATCH_THRESHOLD:
            return typ
    return None


async def _fetch_existing_relations(
    router: FleetRouter,
    space_id: str,
    profile_name: str | None,
) -> list[AnyTypeRelation]:
    """Fetch all existing relations in a space."""
    response = await router.get(
        f"/v1/spaces/{space_id}/relations",
        profile_name=profile_name,
    )
    data = response.json()
    return [
        AnyTypeRelation(
            id=r.get("id", ""),
            key=r.get("key", ""),
            name=r.get("name", ""),
            format=r.get("format", "shorttext"),
            description=r.get("description"),
        )
        for r in data.get("relations", [])
    ]


async def _fetch_existing_types(
    router: FleetRouter,
    space_id: str,
    profile_name: str | None,
) -> list[AnyTypeType]:
    """Fetch all existing types in a space."""
    response = await router.get(
        f"/v1/spaces/{space_id}/types",
        profile_name=profile_name,
    )
    data = response.json()
    return [
        AnyTypeType(
            id=t.get("id", ""),
            key=t.get("key", ""),
            name=t.get("name", ""),
            description=t.get("description"),
            icon=t.get("icon"),
            layout=t.get("layout", "basic"),
        )
        for t in data.get("types", [])
    ]


async def _create_relation(
    router: FleetRouter,
    space_id: str,
    definition: RelationDefinition,
    profile_name: str | None,
) -> str:
    """Create a new relation and return its ID."""
    payload: dict[str, Any] = {
        "name": definition.name,
        "key": definition.key,
        "format": definition.format,
    }
    if definition.description:
        payload["description"] = definition.description
    if definition.max_count:
        payload["maxCount"] = definition.max_count
    if definition.select_options:
        payload["selectOptions"] = [
            {"name": opt.name, "color": opt.color}
            for opt in definition.select_options
        ]

    response = await router.post(
        f"/v1/spaces/{space_id}/relations",
        profile_name=profile_name,
        json=payload,
    )
    data = response.json()
    return data.get("id", "")


async def _create_type(
    router: FleetRouter,
    space_id: str,
    definition: TypeDefinition,
    relation_ids: list[str],
    profile_name: str | None,
) -> str:
    """Create a new type and return its ID."""
    payload: dict[str, Any] = {
        "name": definition.name,
        "key": definition.key,
        "layout": definition.layout,
        "recommendedRelations": relation_ids,
    }
    if definition.description:
        payload["description"] = definition.description
    if definition.icon:
        payload["icon"] = definition.icon

    response = await router.post(
        f"/v1/spaces/{space_id}/types",
        profile_name=profile_name,
        json=payload,
    )
    data = response.json()
    return data.get("id", "")


async def ensure_ontology(input: EnsureOntologyInput) -> EnsureOntologyOutput:
    """
    Ensure a set of Types and Relations exists in the knowledge graph.

    This is the core "Ontological Architect" capability. It:
    1. Fetches existing definitions
    2. Diffs against the requested manifest
    3. Creates missing Relations (first, since Types depend on them)
    4. Creates missing Types linked to the Relations

    Implements fuzzy-matching to prevent schema pollution
    (e.g., reuses "Status" instead of creating "status").

    Args:
        input: Ontology manifest and target space.

    Returns:
        EnsureOntologyOutput with created/skipped elements.
    """
    router = get_router()
    manifest = input.manifest

    logger.info(
        "Ensuring ontology",
        manifest=manifest.name,
        space_id=input.space_id,
        dry_run=input.dry_run,
    )

    # Step 1: Fetch existing schema
    existing_relations = await _fetch_existing_relations(
        router, input.space_id, input.profile_name
    )
    existing_types = await _fetch_existing_types(
        router, input.space_id, input.profile_name
    )

    # Step 2: Diff relations
    missing_relations: list[RelationDefinition] = []
    skipped_relations: list[str] = []
    relation_name_to_id: dict[str, str] = {}

    for rel_def in manifest.relations:
        match = _find_matching_relation(rel_def.name, existing_relations)
        if match:
            skipped_relations.append(rel_def.name)
            relation_name_to_id[rel_def.name.lower()] = match.id
        else:
            missing_relations.append(rel_def)

    # Step 3: Diff types
    missing_types: list[TypeDefinition] = []
    skipped_types: list[str] = []

    for type_def in manifest.types:
        match = _find_matching_type(type_def.name, existing_types)
        if match:
            skipped_types.append(type_def.name)
        else:
            missing_types.append(type_def)

    # Build diff
    diff = OntologyDiff(
        missing_relations=[r.name for r in missing_relations],
        missing_types=[t.name for t in missing_types],
        existing_relations=skipped_relations,
        existing_types=skipped_types,
    )

    created_relations: list[str] = []
    created_types: list[str] = []

    if input.dry_run:
        logger.info(
            "Dry run complete",
            missing_relations=len(missing_relations),
            missing_types=len(missing_types),
        )
        return EnsureOntologyOutput(
            created_relations=[],
            created_types=[],
            skipped_relations=skipped_relations,
            skipped_types=skipped_types,
            diff=diff,
            dry_run=True,
            message=f"Dry run: Would create {len(missing_relations)} relations and {len(missing_types)} types",
        )

    # Step 4: Create missing relations
    for rel_def in missing_relations:
        logger.info("Creating relation", name=rel_def.name)
        rel_id = await _create_relation(
            router, input.space_id, rel_def, input.profile_name
        )
        relation_name_to_id[rel_def.name.lower()] = rel_id
        created_relations.append(rel_def.name)
        # Small delay to avoid overwhelming single-threaded gRPC
        await asyncio.sleep(0.05)

    # Step 5: Create missing types
    for type_def in missing_types:
        # Resolve relation names to IDs
        relation_ids = []
        for rel_name in type_def.relations:
            rel_id = relation_name_to_id.get(rel_name.lower())
            if rel_id:
                relation_ids.append(rel_id)
            else:
                logger.warning(
                    "Relation not found for type",
                    type=type_def.name,
                    relation=rel_name,
                )

        logger.info("Creating type", name=type_def.name, relations=len(relation_ids))
        await _create_type(
            router, input.space_id, type_def, relation_ids, input.profile_name
        )
        created_types.append(type_def.name)
        await asyncio.sleep(0.05)

    logger.info(
        "Ontology ensured",
        created_relations=len(created_relations),
        created_types=len(created_types),
    )

    return EnsureOntologyOutput(
        created_relations=created_relations,
        created_types=created_types,
        skipped_relations=skipped_relations,
        skipped_types=skipped_types,
        diff=diff,
        dry_run=False,
        message=f"Created {len(created_relations)} relations and {len(created_types)} types",
    )


async def smart_ingest(input: SmartIngestInput) -> SmartIngestOutput:
    """
    Intelligently ingest raw content into structured objects.

    This tool:
    1. Analyzes the content to extract entities
    2. Matches entities to existing Types
    3. Creates objects and links them

    NOTE: Full implementation requires LLM integration for entity extraction.
    This is a scaffold that can be extended with LangChain/etc.

    Args:
        input: Content and ingestion parameters.

    Returns:
        SmartIngestOutput with created objects.
    """
    router = get_router()

    logger.info(
        "Smart ingesting content",
        content_length=len(input.content),
        space_id=input.space_id,
        type_hint=input.type_hint,
    )

    # TODO: Implement LLM-based entity extraction
    # For now, create a basic note object with the content

    # Get default note type
    types_response = await router.get(
        f"/v1/spaces/{input.space_id}/types",
        profile_name=input.profile_name,
    )
    types_data = types_response.json()

    # Find a suitable type (prefer type_hint, fall back to Note)
    target_type_id = None
    for t in types_data.get("types", []):
        if input.type_hint and t.get("name", "").lower() == input.type_hint.lower():
            target_type_id = t.get("id")
            break
        if t.get("name", "").lower() == "note":
            target_type_id = t.get("id")

    if not target_type_id:
        # Use first available type
        types_list = types_data.get("types", [])
        if types_list:
            target_type_id = types_list[0].get("id", "")

    # Create the object
    created_objects: list[AnyTypeObject] = []
    if target_type_id:
        # Extract a title from content (first line or truncated)
        lines = input.content.strip().split("\n")
        title = lines[0][:100] if lines else "Ingested Content"

        payload = {
            "typeId": target_type_id,
            "name": title,
            "details": {
                "description": input.content,
            },
        }

        response = await router.post(
            f"/v1/spaces/{input.space_id}/objects",
            profile_name=input.profile_name,
            json=payload,
        )
        data = response.json()

        obj = AnyTypeObject(
            id=data.get("id", ""),
            space_id=input.space_id,
            type_id=target_type_id,
            name=title,
            details=data.get("details", {}),
        )
        created_objects.append(obj)

    logger.info("Smart ingest complete", objects_created=len(created_objects))

    return SmartIngestOutput(
        created_objects=created_objects,
        linked_objects=[],
        extracted_entities=[],
        message=f"Ingested content as {len(created_objects)} object(s)",
    )


async def daily_briefing(input: DailyBriefingInput) -> DailyBriefingOutput:
    """
    Generate a markdown summary of recent changes.

    Queries objects modified in the specified time window
    and generates a human-readable briefing.

    Args:
        input: Briefing parameters.

    Returns:
        DailyBriefingOutput with markdown summary.
    """
    router = get_router()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=input.hours)

    logger.info(
        "Generating daily briefing",
        hours=input.hours,
        space_id=input.space_id,
    )

    # Search for recently modified objects
    params: dict[str, Any] = {
        "modifiedAfter": cutoff.isoformat(),
        "limit": 50,
    }
    if input.space_id:
        params["spaceId"] = input.space_id

    try:
        response = await router.get(
            "/v1/search",
            profile_name=input.profile_name,
            params=params,
        )
        data = response.json()
        objects = data.get("objects", [])
    except Exception as e:
        logger.warning("Failed to fetch recent objects", error=str(e))
        objects = []

    # Group by type for summary
    by_type: dict[str, list[dict[str, Any]]] = {}
    for obj in objects:
        type_name = obj.get("typeName", "Unknown")
        if type_name not in by_type:
            by_type[type_name] = []
        by_type[type_name].append(obj)

    # Generate markdown
    lines = [
        f"# Daily Briefing",
        f"*{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*",
        "",
        f"## Activity Summary (Last {input.hours} hours)",
        "",
    ]

    created_count = 0
    modified_count = len(objects)
    highlights: list[str] = []

    if not objects:
        lines.append("*No activity in this period.*")
    else:
        for type_name, type_objects in by_type.items():
            lines.append(f"### {type_name} ({len(type_objects)})")
            for obj in type_objects[:5]:  # Limit per type
                name = obj.get("name", "Untitled")
                lines.append(f"- {name}")
                if len(highlights) < 5:
                    highlights.append(f"{type_name}: {name}")
            if len(type_objects) > 5:
                lines.append(f"- *...and {len(type_objects) - 5} more*")
            lines.append("")

    summary = "\n".join(lines)

    logger.info(
        "Daily briefing generated",
        objects_count=len(objects),
        types_count=len(by_type),
    )

    return DailyBriefingOutput(
        summary=summary,
        modified_count=modified_count,
        created_count=created_count,
        highlights=highlights,
    )
