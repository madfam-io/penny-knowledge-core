"""
Pydantic schemas for PENNY Knowledge Core.

Strict type validation for all MCP tool inputs and outputs.
"""

from penny_knowledge_core.schemas.anytype import (
    AnyTypeObject,
    AnyTypeRelation,
    AnyTypeSpace,
    AnyTypeType,
    GraphStats,
    SearchResult,
)
from penny_knowledge_core.schemas.manifest import (
    OntologyManifest,
    RelationDefinition,
    TypeDefinition,
)
from penny_knowledge_core.schemas.tools import (
    CreateObjectInput,
    CreateObjectOutput,
    CreateSpaceInput,
    CreateSpaceOutput,
    EnsureOntologyInput,
    EnsureOntologyOutput,
    GetGraphStatsOutput,
    SearchGlobalInput,
    SearchGlobalOutput,
    SwitchProfileInput,
    SwitchProfileOutput,
)

__all__ = [
    # AnyType schemas
    "AnyTypeObject",
    "AnyTypeRelation",
    "AnyTypeSpace",
    "AnyTypeType",
    "GraphStats",
    "SearchResult",
    # Manifest schemas
    "OntologyManifest",
    "RelationDefinition",
    "TypeDefinition",
    # Tool I/O schemas
    "CreateObjectInput",
    "CreateObjectOutput",
    "CreateSpaceInput",
    "CreateSpaceOutput",
    "EnsureOntologyInput",
    "EnsureOntologyOutput",
    "GetGraphStatsOutput",
    "SearchGlobalInput",
    "SearchGlobalOutput",
    "SwitchProfileInput",
    "SwitchProfileOutput",
]
