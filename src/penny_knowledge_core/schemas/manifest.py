"""
Ontology manifest schemas for schema definition.

These schemas define the structure for declaring Types and Relations
that should exist in the knowledge graph.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


# Valid relation format types in AnyType
RelationFormat = Literal[
    "shorttext",
    "longtext",
    "number",
    "select",
    "multiselect",
    "date",
    "file",
    "checkbox",
    "url",
    "email",
    "phone",
    "object",
    "tag",
    "status",
]

# Valid layout types in AnyType
LayoutType = Literal[
    "basic",
    "profile",
    "todo",
    "note",
    "bookmark",
    "set",
    "collection",
    "file",
    "image",
    "audio",
    "video",
    "pdf",
]


class SelectOption(BaseModel):
    """Option for select/multi-select relations."""

    name: str = Field(..., min_length=1, description="Option display name")
    color: str | None = Field(default=None, description="Option color (e.g., 'red', 'blue')")


class RelationDefinition(BaseModel):
    """
    Definition of a Relation (field/property) to ensure exists.

    Used in ontology manifests to declare relations that should be
    created if they don't exist.
    """

    name: str = Field(..., min_length=1, max_length=100, description="Relation name")
    key: str | None = Field(
        default=None,
        description="Optional key (auto-generated from name if not provided)",
    )
    format: RelationFormat = Field(default="shorttext", description="Relation format type")
    description: str | None = Field(default=None, max_length=500)
    max_count: int = Field(
        default=0,
        ge=0,
        alias="maxCount",
        description="Max values (0=unlimited)",
    )
    object_types: list[str] = Field(
        default_factory=list,
        alias="objectTypes",
        description="Type names for object relations",
    )
    select_options: list[SelectOption] = Field(
        default_factory=list,
        alias="selectOptions",
        description="Options for select/multiselect",
    )

    @field_validator("key", mode="before")
    @classmethod
    def generate_key(cls, v: str | None, info: Any) -> str:
        """Generate key from name if not provided."""
        if v is not None:
            return v
        # Will be set during validation
        return ""

    def model_post_init(self, __context: Any) -> None:
        """Generate key from name if not set."""
        if not self.key:
            # Convert name to snake_case key
            self.key = self.name.lower().replace(" ", "_").replace("-", "_")

    class Config:
        populate_by_name = True


class TypeDefinition(BaseModel):
    """
    Definition of an Object Type to ensure exists.

    Used in ontology manifests to declare types that should be
    created if they don't exist.
    """

    name: str = Field(..., min_length=1, max_length=100, description="Type name")
    key: str | None = Field(
        default=None,
        description="Optional key (auto-generated from name if not provided)",
    )
    description: str | None = Field(default=None, max_length=500)
    icon: str | None = Field(default=None, description="Emoji icon for the type")
    layout: LayoutType = Field(default="basic", description="Default layout")
    relations: list[str] = Field(
        default_factory=list,
        description="Relation names to attach to this type",
    )

    def model_post_init(self, __context: Any) -> None:
        """Generate key from name if not set."""
        if not self.key:
            self.key = self.name.lower().replace(" ", "_").replace("-", "_")

    class Config:
        populate_by_name = True


class OntologyManifest(BaseModel):
    """
    Complete ontology manifest for ensuring schema exists.

    Defines the Types and Relations that should exist in a space.
    The ensure_ontology tool uses this to diff against existing
    schema and create missing elements.
    """

    name: str = Field(..., description="Manifest name/identifier")
    description: str | None = Field(default=None, description="Manifest description")
    version: str = Field(default="1.0.0", description="Manifest version")
    relations: list[RelationDefinition] = Field(
        default_factory=list,
        description="Relations to ensure exist",
    )
    types: list[TypeDefinition] = Field(
        default_factory=list,
        description="Types to ensure exist",
    )

    def get_relation_by_name(self, name: str) -> RelationDefinition | None:
        """Find a relation by name (case-insensitive)."""
        name_lower = name.lower()
        for rel in self.relations:
            if rel.name.lower() == name_lower:
                return rel
        return None

    def get_type_by_name(self, name: str) -> TypeDefinition | None:
        """Find a type by name (case-insensitive)."""
        name_lower = name.lower()
        for typ in self.types:
            if typ.name.lower() == name_lower:
                return typ
        return None
