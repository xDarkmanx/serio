# -*- coding: utf-8 -*-

"""
Unit tests for Streams API.
"""
import pytest
import asyncio
import serial

from unittest.mock import Mock
from unittest.mock import patch
from unittest.mock import AsyncMock

from serio.streams import open_serial_connection
from serio.streams import create_serial_connection
from serio.streams import SerialStream
from serio.streams import SerialConnectionError
from serio.streams import SerialConfigError


class TestStreamsAPI:
    """Test high-level Streams API."""

    @pytest.mark.asyncio
    async def test_open_serial_connection_success(self):
        """Test successful serial connection."""
        with patch('serio.streams._create_serial_instance') as mock_create:
            mock_serial = Mock()
            mock_create.return_value = mock_serial

            # Force polling mode for tests
            with patch('os.name', 'nt'):
                reader, writer = await open_serial_connection(
                    port='/dev/ttyTEST0',
                    baudrate=115200
                )

            # Should return reader/writer pair
            assert isinstance(reader, asyncio.StreamReader)
            assert isinstance(writer, asyncio.StreamWriter)

            # Should create serial instance with correct parameters
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_open_serial_connection_missing_params(self):
        """Test connection with missing required parameters."""
        with pytest.raises(SerialConfigError):
            await open_serial_connection()  # No port or url

    @pytest.mark.asyncio
    async def test_open_serial_connection_failure(self):
        """Test connection failure handling."""
        # Вместо мока _create_serial_instance, мокаем serial.Serial чтобы он выбрасывал исключение
        with patch('serial.Serial') as mock_serial:
            mock_serial.side_effect = serial.SerialException("Port not found")

            with pytest.raises(SerialConnectionError):
                await open_serial_connection(port='/dev/ttyINVALID')

    @pytest.mark.asyncio
    async def test_create_serial_connection_custom_protocol(self):
        """Test custom protocol connection."""
        with patch('serio.streams._create_serial_instance') as mock_create:
            mock_serial = Mock()
            mock_create.return_value = mock_serial

            class TestProtocol(asyncio.Protocol):
                def data_received(self, data):
                    pass

            loop = asyncio.get_event_loop()

            # Force polling mode for tests
            with patch('os.name', 'nt'):
                transport, protocol = await create_serial_connection(
                    loop, TestProtocol, port='/dev/ttyTEST0'
                )

            # Should return transport and protocol
            assert transport is not None
            assert isinstance(protocol, TestProtocol)

    @pytest.mark.asyncio
    async def test_serial_stream_context_manager(self):
        """Test SerialStream context manager."""
        with patch('serio.streams.open_serial_connection') as mock_open:
            mock_reader = AsyncMock(spec=asyncio.StreamReader)
            mock_writer = AsyncMock(spec=asyncio.StreamWriter)
            mock_writer.close = Mock()
            mock_writer.wait_closed = AsyncMock()

            mock_open.return_value = (mock_reader, mock_writer)

            async with SerialStream(port='/dev/ttyTEST0') as (reader, writer):
                assert reader == mock_reader
                assert writer == mock_writer

            # Should close writer on exit
            mock_writer.close.assert_called_once()
            mock_writer.wait_closed.assert_called_once()

    @pytest.mark.asyncio
    async def test_serial_stream_properties(self):
        """Test SerialStream property access."""
        with patch('serio.streams.open_serial_connection') as mock_open:
            mock_reader = AsyncMock(spec=asyncio.StreamReader)
            mock_writer = AsyncMock(spec=asyncio.StreamWriter)
            mock_open.return_value = (mock_reader, mock_writer)

            stream = SerialStream(port='/dev/ttyTEST0')

            # Should raise before opening
            with pytest.raises(RuntimeError):
                _ = stream.reader

            with pytest.raises(RuntimeError):
                _ = stream.writer

            # Should work after opening
            async with stream as (reader, writer):
                assert stream.reader == mock_reader
                assert stream.writer == mock_writer


class TestSerialInstanceCreation:
    """Test serial instance creation utilities."""

    @pytest.mark.asyncio
    async def test_create_serial_instance_direct_port(self):
        """Test direct port instance creation."""
        with patch('serial.Serial') as mock_serial_class:
            mock_instance = Mock()
            mock_serial_class.return_value = mock_instance

            from serio.streams import _create_serial_instance

            result = await _create_serial_instance(
                port='/dev/ttyTEST0',
                baudrate=115200
            )

            # Should create Serial instance with correct parameters
            mock_serial_class.assert_called_once_with(
                port='/dev/ttyTEST0',
                baudrate=115200
            )
            assert result == mock_instance

    @pytest.mark.asyncio
    async def test_create_serial_instance_url(self):
        """Test URL-based instance creation."""
        with patch('serial.serial_for_url') as mock_url_creator:
            mock_instance = Mock()
            mock_url_creator.return_value = mock_instance

            from serio.streams import _create_serial_instance

            result = await _create_serial_instance(
                url='spy:///dev/ttyTEST0',
                baudrate=115200
            )

            # Should use serial_for_url for URL connections
            # Fix: serial_for_url takes url and then **kwargs
            mock_url_creator.assert_called_once_with(
                'spy:///dev/ttyTEST0',
                baudrate=115200  # This should be passed as keyword argument
            )
            assert result == mock_instance
