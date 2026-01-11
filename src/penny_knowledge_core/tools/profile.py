"""
Profile management tools for context switching.
"""

from penny_knowledge_core.logging import get_logger
from penny_knowledge_core.router.context import get_current_profile, set_current_profile
from penny_knowledge_core.schemas.tools import SwitchProfileInput, SwitchProfileOutput

logger = get_logger(__name__)


async def switch_profile(input: SwitchProfileInput) -> SwitchProfileOutput:
    """
    Switch the active profile for subsequent operations.

    This changes the routing context so all following tool calls
    will target the specified profile's Heart container.

    Args:
        input: Profile switch parameters.

    Returns:
        SwitchProfileOutput with previous and current profile.

    Raises:
        ValueError: If profile_name is invalid.
    """
    previous = get_current_profile().profile_name
    new_context = set_current_profile(input.profile_name)

    logger.info(
        "Profile switched",
        previous_profile=previous,
        new_profile=new_context.profile_name,
    )

    return SwitchProfileOutput(
        previous_profile=previous,
        current_profile=new_context.profile_name,
        message=f"Switched from '{previous}' to '{new_context.profile_name}' profile",
    )
