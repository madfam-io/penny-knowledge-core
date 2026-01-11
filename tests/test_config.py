"""
Tests for configuration management.
"""

import pytest
from pydantic import SecretStr

from penny_knowledge_core.config import Settings, FleetProfile


class TestSettings:
    """Tests for Settings class."""

    def test_default_settings(self) -> None:
        """Test that default settings are valid."""
        settings = Settings()

        assert settings.gateway_host == "0.0.0.0"
        assert settings.gateway_port == 8000
        assert settings.log_level == "INFO"
        assert settings.debug is False
        assert settings.default_profile == "personal"

    def test_log_level_validation(self) -> None:
        """Test log level validation."""
        settings = Settings(log_level="debug")
        assert settings.log_level == "DEBUG"

        with pytest.raises(ValueError):
            Settings(log_level="invalid")

    def test_profile_validation(self) -> None:
        """Test profile name validation."""
        settings = Settings(default_profile="WORK")
        assert settings.default_profile == "work"

        with pytest.raises(ValueError):
            Settings(default_profile="invalid")

    def test_fleet_config(self) -> None:
        """Test fleet configuration building."""
        settings = Settings()
        fleet = settings.get_fleet_config()

        assert "personal" in fleet
        assert "work" in fleet
        assert "research" in fleet

        assert isinstance(fleet["personal"], FleetProfile)
        assert fleet["personal"].url == settings.fleet_personal_url

    def test_get_profile_url(self) -> None:
        """Test profile URL retrieval."""
        settings = Settings(
            fleet_personal_url="http://heart-1:31009",
            fleet_work_url="http://heart-2:31009",
        )

        assert settings.get_profile_url("personal") == "http://heart-1:31009"
        assert settings.get_profile_url("work") == "http://heart-2:31009"
        assert settings.get_profile_url() == settings.get_profile_url("personal")

    def test_get_profile_url_invalid(self) -> None:
        """Test invalid profile URL retrieval."""
        settings = Settings()

        with pytest.raises(ValueError, match="Unknown profile"):
            settings.get_profile_url("invalid")

    def test_mnemonic_as_secret(self) -> None:
        """Test that mnemonics are handled as secrets."""
        settings = Settings(
            mnemonic_personal=SecretStr("word1 word2 word3 word4 word5 word6 word7 word8 word9 word10 word11 word12")
        )

        # Secret value should not appear in string representation
        assert "word1" not in str(settings)
        assert "word1" not in repr(settings)

        # But should be accessible via get_secret_value()
        assert settings.mnemonic_personal is not None
        assert "word1" in settings.mnemonic_personal.get_secret_value()
