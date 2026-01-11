"""
Configuration management for PENNY Knowledge Core.

Uses Pydantic Settings for type-safe environment variable handling.
"""

from functools import lru_cache
from typing import Any

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class FleetProfile:
    """Represents a single identity container in the fleet."""

    def __init__(self, name: str, url: str, mnemonic: SecretStr | None = None) -> None:
        self.name = name
        self.url = url
        self.mnemonic = mnemonic


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    SECURITY: Mnemonics are handled as SecretStr to prevent accidental logging.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Gateway Configuration
    gateway_host: str = Field(default="0.0.0.0", description="Gateway bind host")
    gateway_port: int = Field(default=8000, description="Gateway bind port")
    log_level: str = Field(default="INFO", description="Logging level")
    debug: bool = Field(default=False, description="Enable debug mode")
    reload: bool = Field(default=False, description="Enable hot reload")

    # Fleet URLs (The Hydra)
    fleet_personal_url: str = Field(
        default="http://heart-personal:31009",
        description="Personal profile Heart URL",
    )
    fleet_work_url: str = Field(
        default="http://heart-work:31009",
        description="Work profile Heart URL",
    )
    fleet_research_url: str = Field(
        default="http://heart-research:31009",
        description="Research profile Heart URL",
    )

    # Default profile
    default_profile: str = Field(
        default="personal",
        description="Default profile when none specified",
    )

    # Mnemonics (CRITICAL SECURITY: Never log these!)
    mnemonic_personal: SecretStr | None = Field(
        default=None,
        description="Personal profile mnemonic (12 words)",
    )
    mnemonic_work: SecretStr | None = Field(
        default=None,
        description="Work profile mnemonic (12 words)",
    )
    mnemonic_research: SecretStr | None = Field(
        default=None,
        description="Research profile mnemonic (12 words)",
    )

    # Redis
    redis_url: str = Field(
        default="redis://redis:6379/0",
        description="Redis URL for distributed locking",
    )

    # AnyType API Configuration
    anytype_timeout_ms: int = Field(
        default=30000,
        description="Timeout for API calls to Heart containers (ms)",
    )
    anytype_max_retries: int = Field(
        default=3,
        description="Max retries for transient failures",
    )
    anytype_retry_delay_ms: int = Field(
        default=500,
        description="Base delay between retries (ms)",
    )
    anytype_batch_delay_ms: int = Field(
        default=50,
        description="Delay between batch operations (ms)",
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Ensure log level is valid."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper_v = v.upper()
        if upper_v not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return upper_v

    @field_validator("default_profile")
    @classmethod
    def validate_default_profile(cls, v: str) -> str:
        """Ensure default profile is valid."""
        valid_profiles = {"personal", "work", "research"}
        lower_v = v.lower()
        if lower_v not in valid_profiles:
            raise ValueError(f"Invalid profile: {v}. Must be one of {valid_profiles}")
        return lower_v

    def get_fleet_config(self) -> dict[str, FleetProfile]:
        """
        Build the fleet configuration mapping profile names to their configs.

        Returns:
            Dictionary mapping profile name to FleetProfile objects.
        """
        return {
            "personal": FleetProfile(
                name="personal",
                url=self.fleet_personal_url,
                mnemonic=self.mnemonic_personal,
            ),
            "work": FleetProfile(
                name="work",
                url=self.fleet_work_url,
                mnemonic=self.mnemonic_work,
            ),
            "research": FleetProfile(
                name="research",
                url=self.fleet_research_url,
                mnemonic=self.mnemonic_research,
            ),
        }

    def get_profile_url(self, profile_name: str | None = None) -> str:
        """
        Get the URL for a specific profile.

        Args:
            profile_name: Profile name (personal, work, research). Defaults to default_profile.

        Returns:
            The URL for the specified profile's Heart container.

        Raises:
            ValueError: If profile name is invalid.
        """
        name = (profile_name or self.default_profile).lower()
        fleet = self.get_fleet_config()
        if name not in fleet:
            raise ValueError(f"Unknown profile: {name}. Available: {list(fleet.keys())}")
        return fleet[name].url


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Uses lru_cache for singleton pattern - settings are loaded once.

    Returns:
        Settings instance.
    """
    return Settings()
