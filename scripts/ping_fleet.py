#!/usr/bin/env python3
"""
Fleet Health Check Script

Pings all Heart containers in the fleet and prints their status.
This is the Phase 1 deliverable verification script.

Usage:
    python scripts/ping_fleet.py
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for direct execution
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from penny_knowledge_core.config import get_settings
from penny_knowledge_core.logging import configure_logging, get_logger
from penny_knowledge_core.router import FleetRouter

logger = get_logger(__name__)


async def main() -> int:
    """Ping all containers in the fleet and report status."""
    configure_logging()
    settings = get_settings()

    print("=" * 60)
    print("PENNY Knowledge Core - Fleet Health Check")
    print("=" * 60)
    print()

    async with FleetRouter(settings) as router:
        print("Checking fleet status...")
        print()

        status = await router.get_all_profiles_status()

        all_healthy = True
        for profile, health in status.items():
            status_icon = "✅" if health["status"] == "healthy" else "❌"
            print(f"  {status_icon} {profile.upper()}")
            print(f"     URL: {settings.get_profile_url(profile)}")
            print(f"     Status: {health['status']}")

            if health["status"] != "healthy":
                all_healthy = False
                print(f"     Error: {health.get('error', 'Unknown')}")

            print()

        print("=" * 60)

        if all_healthy:
            print("✅ All containers are healthy!")
            return 0
        else:
            print("❌ Some containers are unhealthy. Check Docker logs.")
            return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
