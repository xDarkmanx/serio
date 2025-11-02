# -*- coding: utf-8 -*-

"""
Pytest configuration and fixtures for serio tests.
"""
import pytest
import asyncio
import sys
from unittest.mock import Mock, AsyncMock, patch

# Import all fixtures from virtual_ports
from .fixtures.virtual_ports import *

@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_serial():
    """Mock serial port for testing."""
    with patch('serial.Serial') as mock:
        instance = Mock()
        instance.is_open = True
        instance.fileno.return_value = 42
        instance.in_waiting = 0
        instance.out_waiting = 0
        instance.read.return_value = b""
        instance.write.return_value = 0
        instance.close.return_value = None
        mock.return_value = instance
        yield instance

@pytest.fixture
def mock_protocol():
    """Mock asyncio protocol for testing."""
    protocol = Mock(spec=asyncio.Protocol)
    protocol.connection_made = Mock()
    protocol.connection_lost = Mock() 
    protocol.data_received = Mock()
    protocol.pause_writing = Mock()
    protocol.resume_writing = Mock()
    return protocol

@pytest.fixture
def anyio_backend():
    """AnyIO backend for tests."""
    return 'asyncio'