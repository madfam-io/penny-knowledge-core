#!/usr/bin/env python3
"""
Ontology Demo Script

Demonstrates the ensure_ontology tool by creating a CRM schema.
This is the Phase 3 deliverable verification script.

Usage:
    python scripts/demo_ontology.py --space-id <space_id>
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Add src to path for direct execution
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from penny_knowledge_core.config import get_settings
from penny_knowledge_core.logging import configure_logging, get_logger
from penny_knowledge_core.router import FleetRouter
from penny_knowledge_core.schemas.manifest import OntologyManifest, RelationDefinition, SelectOption, TypeDefinition
from penny_knowledge_core.schemas.tools import EnsureOntologyInput
from penny_knowledge_core.tools import primitive
from penny_knowledge_core.tools.composite import ensure_ontology

logger = get_logger(__name__)


# Example CRM Manifest
CRM_MANIFEST = OntologyManifest(
    name="CRM",
    description="Customer Relationship Management schema for agency work",
    version="1.0.0",
    relations=[
        RelationDefinition(
            name="Email",
            format="email",
            description="Contact email address",
        ),
        RelationDefinition(
            name="Phone",
            format="phone",
            description="Contact phone number",
        ),
        RelationDefinition(
            name="Website",
            format="url",
            description="Company website",
        ),
        RelationDefinition(
            name="Status",
            format="select",
            description="Current status",
            select_options=[
                SelectOption(name="Active", color="green"),
                SelectOption(name="Pending", color="yellow"),
                SelectOption(name="Inactive", color="grey"),
            ],
        ),
        RelationDefinition(
            name="Rate",
            format="number",
            description="Hourly or project rate",
        ),
        RelationDefinition(
            name="Due Date",
            format="date",
            description="Payment or delivery due date",
        ),
        RelationDefinition(
            name="Amount",
            format="number",
            description="Invoice amount",
        ),
        RelationDefinition(
            name="Paid",
            format="checkbox",
            description="Whether invoice is paid",
        ),
    ],
    types=[
        TypeDefinition(
            name="Client",
            icon="👤",
            layout="profile",
            description="A client or customer",
            relations=["Email", "Phone", "Website", "Status"],
        ),
        TypeDefinition(
            name="Project",
            icon="📁",
            layout="basic",
            description="A client project",
            relations=["Status", "Rate", "Due Date"],
        ),
        TypeDefinition(
            name="Invoice",
            icon="💰",
            layout="basic",
            description="An invoice for services",
            relations=["Amount", "Due Date", "Status", "Paid"],
        ),
    ],
)


async def main(space_id: str, dry_run: bool = False, profile: str = "personal") -> int:
    """Run the ontology demo."""
    configure_logging()
    settings = get_settings()

    print("=" * 60)
    print("PENNY Knowledge Core - Ontology Demo")
    print("=" * 60)
    print()
    print(f"Space ID: {space_id}")
    print(f"Profile: {profile}")
    print(f"Dry Run: {dry_run}")
    print()

    print("Manifest to apply:")
    print("-" * 40)
    print(f"Name: {CRM_MANIFEST.name}")
    print(f"Relations: {[r.name for r in CRM_MANIFEST.relations]}")
    print(f"Types: {[t.name for t in CRM_MANIFEST.types]}")
    print()

    async with FleetRouter(settings) as router:
        primitive.set_router(router)

        print("Applying ontology...")
        print()

        try:
            result = await ensure_ontology(
                EnsureOntologyInput(
                    space_id=space_id,
                    manifest=CRM_MANIFEST,
                    dry_run=dry_run,
                    profile_name=profile,
                )
            )

            print("=" * 60)
            print("RESULT")
            print("=" * 60)
            print()
            print(result.message)
            print()

            if result.created_relations:
                print(f"Created Relations: {', '.join(result.created_relations)}")
            if result.created_types:
                print(f"Created Types: {', '.join(result.created_types)}")
            if result.skipped_relations:
                print(f"Existing Relations: {', '.join(result.skipped_relations)}")
            if result.skipped_types:
                print(f"Existing Types: {', '.join(result.skipped_types)}")

            print()
            print("✅ Ontology applied successfully!")
            return 0

        except Exception as e:
            print(f"❌ Error: {e}")
            logger.exception("Ontology application failed")
            return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Demo ontology creation")
    parser.add_argument("--space-id", required=True, help="Target space ID")
    parser.add_argument("--profile", default="personal", help="Target profile")
    parser.add_argument("--dry-run", action="store_true", help="Only show what would be created")

    args = parser.parse_args()

    exit_code = asyncio.run(main(args.space_id, args.dry_run, args.profile))
    sys.exit(exit_code)
