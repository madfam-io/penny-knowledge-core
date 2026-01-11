"""
Tests for Pydantic schemas.
"""

import pytest
from pydantic import ValidationError

from penny_knowledge_core.schemas.manifest import (
    OntologyManifest,
    RelationDefinition,
    SelectOption,
    TypeDefinition,
)
from penny_knowledge_core.schemas.tools import (
    CreateObjectInput,
    CreateSpaceInput,
    SearchGlobalInput,
)


class TestRelationDefinition:
    """Tests for RelationDefinition schema."""

    def test_basic_relation(self) -> None:
        """Test creating a basic relation definition."""
        rel = RelationDefinition(name="Status")

        assert rel.name == "Status"
        assert rel.key == "status"
        assert rel.format == "shorttext"

    def test_relation_with_key(self) -> None:
        """Test relation with explicit key."""
        rel = RelationDefinition(name="Due Date", key="due_date")

        assert rel.name == "Due Date"
        assert rel.key == "due_date"

    def test_select_relation(self) -> None:
        """Test select relation with options."""
        rel = RelationDefinition(
            name="Priority",
            format="select",
            select_options=[
                SelectOption(name="High", color="red"),
                SelectOption(name="Medium", color="yellow"),
                SelectOption(name="Low", color="green"),
            ],
        )

        assert rel.format == "select"
        assert len(rel.select_options) == 3
        assert rel.select_options[0].name == "High"

    def test_empty_name_rejected(self) -> None:
        """Test that empty names are rejected."""
        with pytest.raises(ValidationError):
            RelationDefinition(name="")


class TestTypeDefinition:
    """Tests for TypeDefinition schema."""

    def test_basic_type(self) -> None:
        """Test creating a basic type definition."""
        typ = TypeDefinition(name="Client")

        assert typ.name == "Client"
        assert typ.key == "client"
        assert typ.layout == "basic"

    def test_type_with_relations(self) -> None:
        """Test type with attached relations."""
        typ = TypeDefinition(
            name="Invoice",
            icon="💰",
            layout="basic",
            relations=["Amount", "Due Date", "Status"],
        )

        assert typ.icon == "💰"
        assert len(typ.relations) == 3

    def test_type_key_generation(self) -> None:
        """Test automatic key generation."""
        typ = TypeDefinition(name="Meeting Report")
        assert typ.key == "meeting_report"


class TestOntologyManifest:
    """Tests for OntologyManifest schema."""

    def test_complete_manifest(self) -> None:
        """Test creating a complete manifest."""
        manifest = OntologyManifest(
            name="CRM",
            description="Customer Relationship Management schema",
            relations=[
                RelationDefinition(name="Email", format="email"),
                RelationDefinition(name="Phone", format="phone"),
                RelationDefinition(
                    name="Status",
                    format="select",
                    select_options=[
                        SelectOption(name="Active"),
                        SelectOption(name="Inactive"),
                    ],
                ),
            ],
            types=[
                TypeDefinition(
                    name="Client",
                    icon="👤",
                    relations=["Email", "Phone", "Status"],
                ),
                TypeDefinition(
                    name="Invoice",
                    icon="💰",
                    relations=["Status"],
                ),
            ],
        )

        assert manifest.name == "CRM"
        assert len(manifest.relations) == 3
        assert len(manifest.types) == 2

    def test_get_relation_by_name(self) -> None:
        """Test finding relation by name."""
        manifest = OntologyManifest(
            name="Test",
            relations=[RelationDefinition(name="Status")],
        )

        found = manifest.get_relation_by_name("status")
        assert found is not None
        assert found.name == "Status"

        not_found = manifest.get_relation_by_name("missing")
        assert not_found is None

    def test_get_type_by_name(self) -> None:
        """Test finding type by name."""
        manifest = OntologyManifest(
            name="Test",
            types=[TypeDefinition(name="Client")],
        )

        found = manifest.get_type_by_name("CLIENT")
        assert found is not None
        assert found.name == "Client"


class TestToolInputSchemas:
    """Tests for tool input schemas."""

    def test_create_space_input(self) -> None:
        """Test CreateSpaceInput validation."""
        input = CreateSpaceInput(name="My Space", icon="📁")
        assert input.name == "My Space"
        assert input.icon == "📁"

    def test_create_space_empty_name_rejected(self) -> None:
        """Test that empty space names are rejected."""
        with pytest.raises(ValidationError):
            CreateSpaceInput(name="")

    def test_create_object_input(self) -> None:
        """Test CreateObjectInput validation."""
        input = CreateObjectInput(
            space_id="space_123",
            type_id="type_456",
            name="My Object",
            fields={"status": "active"},
        )

        assert input.space_id == "space_123"
        assert input.fields["status"] == "active"

    def test_search_input_limit_bounds(self) -> None:
        """Test search input limit validation."""
        # Valid limits
        SearchGlobalInput(query="test", limit=1)
        SearchGlobalInput(query="test", limit=100)

        # Invalid limits
        with pytest.raises(ValidationError):
            SearchGlobalInput(query="test", limit=0)

        with pytest.raises(ValidationError):
            SearchGlobalInput(query="test", limit=101)
