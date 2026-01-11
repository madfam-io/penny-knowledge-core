"""
Server module for PENNY Knowledge Core.

Provides the FastAPI gateway and MCP server implementation.
"""

from penny_knowledge_core.server.main import app, create_app

__all__ = ["app", "create_app"]
