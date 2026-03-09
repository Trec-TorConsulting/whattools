"""Structured JSON logging setup via structlog."""

import logging
import sys
from typing import Any

import structlog


def setup_logging(service_name: str, *, log_level: str = "INFO") -> None:
    """Configure structured JSON logging for a service.

    Args:
        service_name: Name of the service (included in every log entry).
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, log_level.upper()))
    root_logger.addHandler(handler)


def get_logger(service_name: str, **initial_values: Any) -> structlog.stdlib.BoundLogger:
    """Get a structured logger bound with service name and initial context.

    Args:
        service_name: Name of the service.
        **initial_values: Additional key-value pairs to bind to every log entry.

    Returns:
        A bound structlog logger.
    """
    return structlog.get_logger(service=service_name, **initial_values)
