"""
Tests for the fleet router and context management.
"""

import pytest

from penny_knowledge_core.router.context import (
    ProfileContext,
    get_current_profile,
    reset_profile_context,
    set_current_profile,
)


class TestProfileContext:
    """Tests for profile context management."""

    def setup_method(self) -> None:
        """Reset context before each test."""
        reset_profile_context()

    def test_default_profile(self) -> None:
        """Test that default profile is returned when none is set."""
        ctx = get_current_profile()
        assert ctx.profile_name == "personal"  # default from settings

    def test_set_profile(self) -> None:
        """Test setting the active profile."""
        ctx = set_current_profile("work")

        assert ctx.profile_name == "work"
        assert get_current_profile().profile_name == "work"

    def test_set_profile_with_session(self) -> None:
        """Test setting profile with session ID."""
        ctx = set_current_profile("research", session_id="sess_123")

        assert ctx.profile_name == "research"
        assert ctx.session_id == "sess_123"

    def test_set_invalid_profile(self) -> None:
        """Test that invalid profile names are rejected."""
        with pytest.raises(ValueError, match="Invalid profile"):
            set_current_profile("invalid")

    def test_profile_case_insensitive(self) -> None:
        """Test that profile names are case-insensitive."""
        ctx = set_current_profile("WORK")
        assert ctx.profile_name == "work"

        ctx = set_current_profile("Personal")
        assert ctx.profile_name == "personal"

    def test_reset_context(self) -> None:
        """Test resetting the profile context."""
        set_current_profile("work")
        assert get_current_profile().profile_name == "work"

        reset_profile_context()
        assert get_current_profile().profile_name == "personal"  # default
