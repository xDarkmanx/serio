"""
Unit tests for compatibility layer.
"""

import pytest
import asyncio

from unittest.mock import patch
from serio.compat import create_stream_reader
from serio.compat import create_stream_reader_protocol


class TestCompatibility:
    """Test compatibility layer functions."""

    @pytest.mark.asyncio
    async def test_create_stream_reader_python_312_plus(self):
        """Test stream reader creation for Python 3.12+."""
        with patch('serio.compat.PYTHON_312', True):
            # Test with explicit limit
            reader = create_stream_reader(limit=8192)
            assert isinstance(reader, asyncio.StreamReader)

            # Test with default limit
            reader_default = create_stream_reader()
            assert isinstance(reader_default, asyncio.StreamReader)

            # Test with loop parameter (should be ignored in 3.12+)
            reader_with_loop = create_stream_reader(loop=asyncio.get_event_loop())
            assert isinstance(reader_with_loop, asyncio.StreamReader)

    @pytest.mark.asyncio
    async def test_create_stream_reader_python_311(self):
        """Test stream reader creation for Python 3.11."""
        with patch('serio.compat.PYTHON_312', False):
            # Test without loop
            reader = create_stream_reader(limit=8192)
            assert isinstance(reader, asyncio.StreamReader)

            # Test with loop parameter
            loop = asyncio.get_event_loop()
            reader_with_loop = create_stream_reader(limit=4096, loop=loop)
            assert isinstance(reader_with_loop, asyncio.StreamReader)

    @pytest.mark.asyncio
    async def test_create_stream_reader_protocol_python_312_plus(self):
        """Test stream reader protocol creation for Python 3.12+."""
        with patch('serio.compat.PYTHON_312', True):
            reader = create_stream_reader(limit=8192)
            protocol = create_stream_reader_protocol(reader)
            assert isinstance(protocol, asyncio.StreamReaderProtocol)

            # Test with loop parameter (should be ignored)
            protocol_with_loop = create_stream_reader_protocol(reader, loop=asyncio.get_event_loop())
            assert isinstance(protocol_with_loop, asyncio.StreamReaderProtocol)

    @pytest.mark.asyncio
    async def test_create_stream_reader_protocol_python_311(self):
        """Test stream reader protocol creation for Python 3.11."""
        with patch('serio.compat.PYTHON_312', False):
            reader = create_stream_reader(limit=8192)

            # Test without loop
            protocol = create_stream_reader_protocol(reader)
            assert isinstance(protocol, asyncio.StreamReaderProtocol)

            # Test with loop parameter
            loop = asyncio.get_event_loop()
            protocol_with_loop = create_stream_reader_protocol(reader, loop=loop)
            assert isinstance(protocol_with_loop, asyncio.StreamReaderProtocol)

    def test_compatibility_functions_parameters(self):
        """Test that compatibility functions accept expected parameters."""
        # Test various parameter combinations
        reader1 = create_stream_reader()
        reader2 = create_stream_reader(limit=4096)
        reader3 = create_stream_reader(limit=8192, loop=asyncio.get_event_loop())

        protocol1 = create_stream_reader_protocol(reader1)
        protocol2 = create_stream_reader_protocol(reader2, loop=asyncio.get_event_loop())

        # Verify all created successfully
        assert all(isinstance(r, asyncio.StreamReader) for r in [reader1, reader2, reader3])
        assert all(isinstance(p, asyncio.StreamReaderProtocol) for p in [protocol1, protocol2])
