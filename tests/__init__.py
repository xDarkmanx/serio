"""
Test suite for serio - modern asynchronous serial port library.

This package contains unit tests, integration tests, and test fixtures
for verifying serio functionality across different platforms and Python versions.
"""

__version__ = "0.1.1"
__author__ = "Semenets V. Pavel"

# Import key test utilities for easier access
# from .conftest import mock_serial
# from .conftest import mock_protocol
# from .conftest import event_loop

# Test markers for categorizing tests
# import pytest


def pytest_configure(config):
    """Register custom markers for test categorization."""
    config.addinivalue_line(
        "markers",
        "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )

    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests"
    )

    config.addinivalue_line(
        "markers",
        "virtual_ports: tests requiring virtual serial ports"
    )

    config.addinivalue_line(
        "markers",
        "posix_only: tests that only work on POSIX systems"
    )

    config.addinivalue_line(
        "markers",
        "windows_only: tests that only work on Windows"
    )
