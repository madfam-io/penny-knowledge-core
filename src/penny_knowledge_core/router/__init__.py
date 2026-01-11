"""
Profile routing for the Hydra fleet.

Manages context switching between different identity containers.
"""

from penny_knowledge_core.router.context import (
    ProfileContext,
    get_current_profile,
    set_current_profile,
)
from penny_knowledge_core.router.fleet import FleetRouter

__all__ = [
    "FleetRouter",
    "ProfileContext",
    "get_current_profile",
    "set_current_profile",
]
