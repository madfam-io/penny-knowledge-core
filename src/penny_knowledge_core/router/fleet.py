"""
Fleet router for managing the Hydra fleet of Heart containers.

Routes requests to the appropriate container based on profile context.
"""

from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from penny_knowledge_core.config import Settings, get_settings
from penny_knowledge_core.logging import get_logger
from penny_knowledge_core.router.context import get_current_profile

logger = get_logger(__name__)


class FleetRouter:
    """
    Routes requests to the appropriate Heart container in the fleet.

    The FleetRouter maintains HTTP clients for each profile and handles
    routing based on the current context or explicit profile specification.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        """
        Initialize the fleet router.

        Args:
            settings: Optional settings instance. Uses global settings if not provided.
        """
        self._settings = settings or get_settings()
        self._clients: dict[str, httpx.AsyncClient] = {}
        self._fleet_config = self._settings.get_fleet_config()

    async def __aenter__(self) -> "FleetRouter":
        """Async context manager entry."""
        await self._init_clients()
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def _init_clients(self) -> None:
        """Initialize HTTP clients for all profiles."""
        timeout = httpx.Timeout(
            timeout=self._settings.anytype_timeout_ms / 1000,
            connect=10.0,
        )

        for name, profile in self._fleet_config.items():
            self._clients[name] = httpx.AsyncClient(
                base_url=profile.url,
                timeout=timeout,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
            logger.debug("Initialized client", profile=name, url=profile.url)

    async def close(self) -> None:
        """Close all HTTP clients."""
        for name, client in self._clients.items():
            await client.aclose()
            logger.debug("Closed client", profile=name)
        self._clients.clear()

    def _get_client(self, profile_name: str | None = None) -> httpx.AsyncClient:
        """
        Get the HTTP client for a profile.

        Args:
            profile_name: Optional profile name. Uses current context if not specified.

        Returns:
            The HTTP client for the specified profile.

        Raises:
            ValueError: If profile is invalid or client not initialized.
        """
        name = (profile_name or get_current_profile().profile_name).lower()
        if name not in self._clients:
            raise ValueError(f"No client for profile: {name}. Available: {list(self._clients.keys())}")
        return self._clients[name]

    @retry(
        retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=10),
        reraise=True,
    )
    async def request(
        self,
        method: str,
        path: str,
        profile_name: str | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """
        Make an HTTP request to a Heart container.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE).
            path: API path (e.g., "/v1/spaces").
            profile_name: Optional profile override.
            **kwargs: Additional arguments passed to httpx.

        Returns:
            The HTTP response.

        Raises:
            httpx.HTTPError: On request failure after retries.
        """
        client = self._get_client(profile_name)
        profile = profile_name or get_current_profile().profile_name

        logger.debug(
            "Fleet request",
            method=method,
            path=path,
            profile=profile,
        )

        response = await client.request(method, path, **kwargs)
        response.raise_for_status()

        logger.debug(
            "Fleet response",
            status=response.status_code,
            profile=profile,
        )

        return response

    async def get(
        self,
        path: str,
        profile_name: str | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """Make a GET request."""
        return await self.request("GET", path, profile_name, **kwargs)

    async def post(
        self,
        path: str,
        profile_name: str | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """Make a POST request."""
        return await self.request("POST", path, profile_name, **kwargs)

    async def put(
        self,
        path: str,
        profile_name: str | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """Make a PUT request."""
        return await self.request("PUT", path, profile_name, **kwargs)

    async def delete(
        self,
        path: str,
        profile_name: str | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """Make a DELETE request."""
        return await self.request("DELETE", path, profile_name, **kwargs)

    async def health_check(self, profile_name: str | None = None) -> dict[str, Any]:
        """
        Check the health of a Heart container.

        Args:
            profile_name: Optional profile to check. Checks all if not specified.

        Returns:
            Health status dictionary.
        """
        if profile_name:
            profiles = [profile_name.lower()]
        else:
            profiles = list(self._clients.keys())

        results: dict[str, Any] = {}
        for name in profiles:
            try:
                response = await self.get("/v1/health", profile_name=name)
                results[name] = {
                    "status": "healthy",
                    "response": response.json() if response.content else {},
                }
            except Exception as e:
                results[name] = {
                    "status": "unhealthy",
                    "error": str(e),
                }
                logger.warning("Health check failed", profile=name, error=str(e))

        return results

    async def get_all_profiles_status(self) -> dict[str, Any]:
        """
        Get status of all profiles in the fleet.

        Returns:
            Dictionary with status of each profile.
        """
        return await self.health_check()
