"""
Tool input/output schemas for MCP tools.

Strict Pydantic validation for all tool parameters and return values.
"""

from typing import Any

from pydantic import BaseModel, Field

from penny_knowledge_core.schemas.anytype import (
    AnyTypeObject,
    AnyTypeSpace,
    GraphStats,
)
from penny_knowledge_core.schemas.manifest import OntologyManifest


# =============================================================================
# Profile Management
# =============================================================================


class SwitchProfileInput(BaseModel):
    """Input for switching the active profile."""

    profile_name: str = Field(
        ...,
        description="Profile to switch to: 'personal', 'work', or 'research'",
    )


class SwitchProfileOutput(BaseModel):
    """Output after switching profile."""

    previous_profile: str = Field(..., description="Previously active profile")
    current_profile: str = Field(..., description="Now active profile")
    message: str = Field(..., description="Human-readable status message")


# =============================================================================
# Space Management
# =============================================================================


class CreateSpaceInput(BaseModel):
    """Input for creating a new space."""

    name: str = Field(..., min_length=1, max_length=100, description="Space name")
    icon: str | None = Field(default=None, description="Emoji icon for space")
    profile_name: str | None = Field(
        default=None,
        description="Target profile (defaults to active profile)",
    )


class CreateSpaceOutput(BaseModel):
    """Output after creating a space."""

    space: AnyTypeSpace = Field(..., description="Created space details")
    message: str = Field(..., description="Human-readable status message")


class ListSpacesOutput(BaseModel):
    """Output for listing spaces."""

    spaces: list[AnyTypeSpace] = Field(default_factory=list)
    profile: str = Field(..., description="Profile these spaces belong to")


# =============================================================================
# Object Management
# =============================================================================


class CreateObjectInput(BaseModel):
    """Input for creating a new object."""

    space_id: str = Field(..., description="Target space ID")
    type_id: str = Field(..., description="Object type ID")
    name: str = Field(..., min_length=1, description="Object name/title")
    fields: dict[str, Any] = Field(
        default_factory=dict,
        description="Field values keyed by relation ID or name",
    )
    icon: str | None = Field(default=None, description="Emoji icon")
    profile_name: str | None = Field(default=None, description="Target profile")


class CreateObjectOutput(BaseModel):
    """Output after creating an object."""

    object: AnyTypeObject = Field(..., description="Created object details")
    message: str = Field(..., description="Human-readable status message")


class GetObjectInput(BaseModel):
    """Input for getting an object by ID."""

    object_id: str = Field(..., description="Object ID to retrieve")
    space_id: str = Field(..., description="Space containing the object")
    profile_name: str | None = Field(default=None, description="Target profile")


class UpdateObjectInput(BaseModel):
    """Input for updating an object."""

    object_id: str = Field(..., description="Object ID to update")
    space_id: str = Field(..., description="Space containing the object")
    fields: dict[str, Any] = Field(..., description="Fields to update")
    profile_name: str | None = Field(default=None, description="Target profile")


# =============================================================================
# Search
# =============================================================================


class SearchGlobalInput(BaseModel):
    """Input for global search."""

    query: str = Field(..., min_length=1, description="Search query")
    space_id: str | None = Field(default=None, description="Limit to specific space")
    type_id: str | None = Field(default=None, description="Limit to specific type")
    limit: int = Field(default=20, ge=1, le=100, description="Max results")
    profile_name: str | None = Field(default=None, description="Target profile")


class SearchGlobalOutput(BaseModel):
    """Output from global search."""

    objects: list[AnyTypeObject] = Field(default_factory=list)
    total: int = Field(default=0)
    query: str = Field(..., description="Original query")


# =============================================================================
# Graph Statistics
# =============================================================================


class GetGraphStatsOutput(BaseModel):
    """Output for graph statistics."""

    stats: GraphStats = Field(..., description="Graph statistics")
    profile: str = Field(..., description="Profile these stats are from")


# =============================================================================
# Ontology Management (Composite Tool)
# =============================================================================


class EnsureOntologyInput(BaseModel):
    """Input for ensuring ontology exists."""

    space_id: str = Field(..., description="Target space ID")
    manifest: OntologyManifest = Field(..., description="Ontology manifest to ensure")
    profile_name: str | None = Field(default=None, description="Target profile")
    dry_run: bool = Field(
        default=False,
        description="If true, only report what would be created",
    )


class OntologyDiff(BaseModel):
    """Represents differences between manifest and existing schema."""

    missing_relations: list[str] = Field(default_factory=list)
    missing_types: list[str] = Field(default_factory=list)
    existing_relations: list[str] = Field(default_factory=list)
    existing_types: list[str] = Field(default_factory=list)


class EnsureOntologyOutput(BaseModel):
    """Output after ensuring ontology."""

    created_relations: list[str] = Field(default_factory=list)
    created_types: list[str] = Field(default_factory=list)
    skipped_relations: list[str] = Field(
        default_factory=list,
        description="Relations that already existed",
    )
    skipped_types: list[str] = Field(
        default_factory=list,
        description="Types that already existed",
    )
    diff: OntologyDiff = Field(..., description="Full diff details")
    dry_run: bool = Field(default=False)
    message: str = Field(..., description="Human-readable summary")


# =============================================================================
# Smart Ingest (Composite Tool)
# =============================================================================


class SmartIngestInput(BaseModel):
    """Input for smart content ingestion."""

    content: str = Field(..., description="Raw text, URL, or content to ingest")
    space_id: str = Field(..., description="Target space ID")
    type_hint: str | None = Field(
        default=None,
        description="Suggested type for the ingested content",
    )
    auto_link: bool = Field(
        default=True,
        description="Automatically link to related existing objects",
    )
    profile_name: str | None = Field(default=None, description="Target profile")


class SmartIngestOutput(BaseModel):
    """Output after smart ingestion."""

    created_objects: list[AnyTypeObject] = Field(default_factory=list)
    linked_objects: list[str] = Field(
        default_factory=list,
        description="IDs of existing objects linked to",
    )
    extracted_entities: list[str] = Field(
        default_factory=list,
        description="Entities extracted from content",
    )
    message: str = Field(..., description="Human-readable summary")


# =============================================================================
# Daily Briefing (Composite Tool)
# =============================================================================


class DailyBriefingInput(BaseModel):
    """Input for generating daily briefing."""

    profile_name: str | None = Field(default=None, description="Target profile")
    hours: int = Field(default=24, ge=1, le=168, description="Lookback hours")
    space_id: str | None = Field(default=None, description="Limit to specific space")


class DailyBriefingOutput(BaseModel):
    """Output for daily briefing."""

    summary: str = Field(..., description="Markdown-formatted briefing")
    modified_count: int = Field(default=0, description="Objects modified in period")
    created_count: int = Field(default=0, description="Objects created in period")
    highlights: list[str] = Field(
        default_factory=list,
        description="Key highlights",
    )
