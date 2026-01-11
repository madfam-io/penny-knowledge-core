"""
Context management for profile routing.

Uses Python's contextvars for thread-safe session state management.
"""

from contextvars import ContextVar
from dataclasses import dataclass
from typing import Optional

from penny_knowledge_core.config import get_settings


@dataclass
class ProfileContext:
    """
    Represents the current routing context for a session.

    Attributes:
        profile_name: The active profile (personal, work, research).
        session_id: Optional session identifier for tracking.
    """

    profile_name: str
    session_id: str | None = None


# Thread-local context variable for the active profile
_current_profile: ContextVar[ProfileContext | None] = ContextVar(
    "current_profile",
    default=None,
)


def get_current_profile() -> ProfileContext:
    """
    Get the current profile context.

    Returns:
        The current ProfileContext, or default profile if none set.
    """
    ctx = _current_profile.get()
    if ctx is None:
        settings = get_settings()
        return ProfileContext(profile_name=settings.default_profile)
    return ctx


def set_current_profile(profile_name: str, session_id: str | None = None) -> ProfileContext:
    """
    Set the current profile context.

    Args:
        profile_name: Profile to switch to (personal, work, research).
        session_id: Optional session identifier.

    Returns:
        The new ProfileContext.

    Raises:
        ValueError: If profile_name is invalid.
    """
    # Validate profile name
    valid_profiles = {"personal", "work", "research"}
    name = profile_name.lower()
    if name not in valid_profiles:
        raise ValueError(f"Invalid profile: {profile_name}. Must be one of {valid_profiles}")

    ctx = ProfileContext(profile_name=name, session_id=session_id)
    _current_profile.set(ctx)
    return ctx


def reset_profile_context() -> None:
    """Reset the profile context to None (will use default on next get)."""
    _current_profile.set(None)
