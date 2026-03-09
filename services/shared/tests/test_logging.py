"""Tests for structured logging setup."""

import logging

import structlog

from services.shared.logging import get_logger, setup_logging


class TestSetupLogging:
    """Tests for logging configuration."""

    def test_setup_logging_configures_structlog(self) -> None:
        setup_logging("test-service", log_level="DEBUG")
        logger = structlog.get_logger()
        assert logger is not None

    def test_setup_logging_sets_level(self) -> None:
        setup_logging("test-service", log_level="WARNING")
        root = logging.getLogger()
        assert root.level == logging.WARNING

    def test_get_logger_returns_bound_logger(self) -> None:
        setup_logging("test-service")
        logger = get_logger("test-service", extra_key="value")
        assert logger is not None
