"""
Structured logging configuration for PENNY Knowledge Core.

Uses structlog for JSON-formatted, context-rich logging.
SECURITY: Configured to filter out sensitive data like mnemonics.
"""

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor

from penny_knowledge_core.config import get_settings


# Sensitive keys that should never be logged
SENSITIVE_KEYS = frozenset({
    "mnemonic",
    "mnemonic_personal",
    "mnemonic_work",
    "mnemonic_research",
    "auth_token",
    "authorization",
    "password",
    "secret",
    "api_key",
})


def filter_sensitive_data(
    logger: logging.Logger,
    method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """
    Processor that filters sensitive data from log events.

    SECURITY: Prevents accidental logging of mnemonics, tokens, and other secrets.
    """
    for key in list(event_dict.keys()):
        key_lower = key.lower()
        if any(sensitive in key_lower for sensitive in SENSITIVE_KEYS):
            event_dict[key] = "[REDACTED]"
        elif isinstance(event_dict[key], dict):
            # Recursively filter nested dicts
            for nested_key in list(event_dict[key].keys()):
                if any(sensitive in nested_key.lower() for sensitive in SENSITIVE_KEYS):
                    event_dict[key][nested_key] = "[REDACTED]"
    return event_dict


def add_service_context(
    logger: logging.Logger,
    method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """Add service-level context to all log events."""
    event_dict["service"] = "penny-knowledge-core"
    return event_dict


def configure_logging() -> None:
    """
    Configure structured logging for the application.

    Sets up structlog with:
    - JSON output for production
    - Console output for development
    - Sensitive data filtering
    - Request context propagation
    """
    settings = get_settings()

    # Determine log level
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # Define processors
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        filter_sensitive_data,
        add_service_context,
    ]

    if settings.debug:
        # Development: colored console output
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    else:
        # Production: JSON output
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """
    Get a configured logger instance.

    Args:
        name: Optional logger name. Defaults to caller's module.

    Returns:
        Configured structlog logger.
    """
    return structlog.get_logger(name)
