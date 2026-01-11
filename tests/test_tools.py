"""
Tests for MCP tools.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from penny_knowledge_core.router.context import reset_profile_context
from penny_knowledge_core.schemas.tools import SwitchProfileInput
from penny_knowledge_core.tools.profile import switch_profile


class TestSwitchProfile:
    """Tests for switch_profile tool."""

    def setup_method(self) -> None:
        """Reset context before each test."""
        reset_profile_context()

    @pytest.mark.asyncio
    async def test_switch_profile_success(self) -> None:
        """Test successful profile switch."""
        result = await switch_profile(SwitchProfileInput(profile_name="work"))

        assert result.previous_profile == "personal"
        assert result.current_profile == "work"
        assert "work" in result.message

    @pytest.mark.asyncio
    async def test_switch_profile_invalid(self) -> None:
        """Test switching to invalid profile."""
        with pytest.raises(ValueError, match="Invalid profile"):
            await switch_profile(SwitchProfileInput(profile_name="invalid"))

    @pytest.mark.asyncio
    async def test_switch_profile_multiple(self) -> None:
        """Test multiple profile switches."""
        await switch_profile(SwitchProfileInput(profile_name="work"))
        result = await switch_profile(SwitchProfileInput(profile_name="research"))

        assert result.previous_profile == "work"
        assert result.current_profile == "research"


# Integration tests would go here, requiring actual Heart containers
# These are marked for integration test runs only

@pytest.mark.integration
class TestToolsIntegration:
    """Integration tests for tools requiring actual AnyType Heart."""

    @pytest.mark.asyncio
    async def test_create_space_integration(self) -> None:
        """Test creating a space against real Heart."""
        pytest.skip("Requires running Heart container")

    @pytest.mark.asyncio
    async def test_search_integration(self) -> None:
        """Test search against real Heart."""
        pytest.skip("Requires running Heart container")
