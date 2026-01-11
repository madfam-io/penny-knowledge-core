"""
MCP Tools for PENNY Knowledge Core.

Exposes both primitive and composite tools to the LLM.
"""

from penny_knowledge_core.tools.primitive import (
    create_object,
    create_space,
    get_graph_stats,
    list_spaces,
    search_global,
)
from penny_knowledge_core.tools.composite import (
    ensure_ontology,
    smart_ingest,
    daily_briefing,
)
from penny_knowledge_core.tools.profile import switch_profile

__all__ = [
    # Primitive tools
    "create_object",
    "create_space",
    "get_graph_stats",
    "list_spaces",
    "search_global",
    # Composite tools
    "ensure_ontology",
    "smart_ingest",
    "daily_briefing",
    # Profile management
    "switch_profile",
]
