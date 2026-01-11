"""
Pydantic models representing AnyType data structures.

These schemas model the data returned from AnyType's JSON API.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AnyTypeSpace(BaseModel):
    """Represents an AnyType Space (workspace)."""

    id: str = Field(..., description="Unique space identifier")
    name: str = Field(..., description="Space name")
    icon: str | None = Field(default=None, description="Space icon emoji or URL")
    created_at: datetime | None = Field(default=None, alias="createdAt")
    is_personal: bool = Field(default=False, alias="isPersonal")

    class Config:
        populate_by_name = True


class AnyTypeRelation(BaseModel):
    """Represents an AnyType Relation (field/property definition)."""

    id: str = Field(..., description="Unique relation identifier")
    key: str = Field(..., description="Relation key (internal name)")
    name: str = Field(..., description="Human-readable relation name")
    format: str = Field(default="shorttext", description="Relation format type")
    description: str | None = Field(default=None)
    is_hidden: bool = Field(default=False, alias="isHidden")
    is_read_only: bool = Field(default=False, alias="isReadOnly")
    max_count: int = Field(default=0, alias="maxCount", description="Max values (0=unlimited)")
    object_types: list[str] = Field(
        default_factory=list,
        alias="objectTypes",
        description="Allowed object type IDs for relation format",
    )
    select_options: list[dict[str, Any]] = Field(
        default_factory=list,
        alias="selectOptions",
        description="Options for select/multi-select relations",
    )

    class Config:
        populate_by_name = True


class AnyTypeType(BaseModel):
    """Represents an AnyType Object Type."""

    id: str = Field(..., description="Unique type identifier")
    key: str = Field(..., description="Type key (internal name)")
    name: str = Field(..., description="Human-readable type name")
    description: str | None = Field(default=None)
    icon: str | None = Field(default=None, description="Type icon emoji")
    layout: str = Field(default="basic", description="Default layout for objects of this type")
    is_archived: bool = Field(default=False, alias="isArchived")
    recommended_relations: list[str] = Field(
        default_factory=list,
        alias="recommendedRelations",
        description="Relation IDs recommended for this type",
    )

    class Config:
        populate_by_name = True


class AnyTypeObject(BaseModel):
    """Represents an AnyType Object (data entity)."""

    id: str = Field(..., description="Unique object identifier")
    space_id: str = Field(..., alias="spaceId", description="Parent space ID")
    type_id: str = Field(..., alias="typeId", description="Object type ID")
    name: str = Field(default="", description="Object name/title")
    icon: str | None = Field(default=None, description="Object icon")
    snippet: str | None = Field(default=None, description="Text snippet/preview")
    layout: str = Field(default="basic", description="Object layout")
    is_archived: bool = Field(default=False, alias="isArchived")
    is_deleted: bool = Field(default=False, alias="isDeleted")
    is_favorite: bool = Field(default=False, alias="isFavorite")
    created_at: datetime | None = Field(default=None, alias="createdAt")
    updated_at: datetime | None = Field(default=None, alias="updatedAt")
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Object field values keyed by relation ID",
    )

    class Config:
        populate_by_name = True


class SearchResult(BaseModel):
    """Represents a search result from AnyType."""

    objects: list[AnyTypeObject] = Field(default_factory=list)
    total: int = Field(default=0, description="Total matching objects")
    has_more: bool = Field(default=False, alias="hasMore")

    class Config:
        populate_by_name = True


class GraphStats(BaseModel):
    """Statistics about the knowledge graph."""

    total_objects: int = Field(default=0, alias="totalObjects")
    total_types: int = Field(default=0, alias="totalTypes")
    total_relations: int = Field(default=0, alias="totalRelations")
    total_spaces: int = Field(default=0, alias="totalSpaces")
    objects_by_type: dict[str, int] = Field(
        default_factory=dict,
        alias="objectsByType",
        description="Object count per type",
    )
    storage_bytes: int = Field(default=0, alias="storageBytes")

    class Config:
        populate_by_name = True
