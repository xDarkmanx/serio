# -*- coding: utf-8 -*-

"""
High-level Streams API for serio.
Provides easy-to-use async serial communication with StreamReader/StreamWriter.
"""
import asyncio
import serial
import logging

from typing import Optional
from typing import Tuple
from typing import Any
# from typing import Dict

from .transport import SerialTransport
from .exceptions import SerialConnectionError
from .exceptions import SerialConfigError

_DEFAULT_LIMIT = 64 * 1024  # 64KB

log = logging.getLogger('serio.streams')


async def open_serial_connection(
    *,
    url: Optional[str] = None,
    port: Optional[str] = None,
    baudrate: int = 9600,
    bytesize: int = serial.EIGHTBITS,
    parity: str = serial.PARITY_NONE,
    stopbits: float = serial.STOPBITS_ONE,
    timeout: Optional[float] = None,
    xonxoff: bool = False,
    rtscts: bool = False,
    write_timeout: Optional[float] = None,
    dsrdtr: bool = False,
    inter_byte_timeout: Optional[float] = None,
    exclusive: Optional[bool] = None,
    loop: Optional[asyncio.AbstractEventLoop] = None,
    limit: Optional[int] = None,
    **kwargs: Any
) -> Tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    """
    Open a serial connection and return StreamReader/StreamWriter pair.

    This is the main high-level API for most use cases.

    Args:
        url: Serial port URL (e.g., 'spy:///dev/ttyUSB0')
        port: Serial port name (e.g., '/dev/ttyUSB0' or 'COM3')
        baudrate: Baud rate (default: 9600)
        bytesize: Number of data bits (default: EIGHTBITS)
        parity: Parity checking (default: PARITY_NONE)
        stopbits: Number of stop bits (default: STOPBITS_ONE)
        timeout: Read timeout in seconds (default: None, non-blocking)
        xonxoff: Software flow control (default: False)
        rtscts: Hardware (RTS/CTS) flow control (default: False)
        write_timeout: Write timeout in seconds (default: None)
        dsrdtr: Hardware (DSR/DTR) flow control (default: False)
        inter_byte_timeout: Inter-character timeout (default: None)
        exclusive: Exclusive access mode (default: None)
        loop: Event loop (default: current event loop)
        **kwargs: Additional serial parameters

    Returns:
        Tuple of (StreamReader, StreamWriter)

    Raises:
        SerialConnectionError: If connection fails
        SerialConfigError: If configuration is invalid

    Example:
        >>> reader, writer = await open_serial_connection(
        ...     port='/dev/ttyUSB0',
        ...     baudrate=115200
        ... )
        >>> writer.write(b'AT\\r\\n')
        >>> response = await reader.readuntil(b'\\r\\n')
    """
    if loop is None:
        loop = asyncio.get_event_loop()

    # Validate parameters
    if not url and not port:
        raise SerialConfigError("Either 'url' or 'port' must be specified")

    # Set default limit if not provided
    if limit is None:
        limit = 64 * 1024  # 64KB default

    # Create serial instance
    serial_instance = await _create_serial_instance(
        url=url,
        port=port,
        baudrate=baudrate,
        bytesize=bytesize,
        parity=parity,
        stopbits=stopbits,
        timeout=timeout or 0,
        xonxoff=xonxoff,
        rtscts=rtscts,
        write_timeout=write_timeout or 0,
        dsrdtr=dsrdtr,
        inter_byte_timeout=inter_byte_timeout,
        exclusive=exclusive,
        **kwargs
    )

    # Create stream protocol with proper limit
    reader = asyncio.StreamReader(limit=limit)
    protocol = asyncio.StreamReaderProtocol(reader)

    # Create transport
    transport = SerialTransport(loop, protocol, serial_instance)

    # Create writer
    writer = asyncio.StreamWriter(transport, protocol, reader, loop)

    return reader, writer


async def create_serial_connection(
    loop: asyncio.AbstractEventLoop,
    protocol_factory: callable,
    url: Optional[str] = None,
    port: Optional[str] = None,
    **kwargs: Any
) -> Tuple[SerialTransport, asyncio.Protocol]:
    """
    Create a serial connection with a custom protocol.

    This is a lower-level API for custom protocol implementations.

    Args:
        loop: Event loop to use
        protocol_factory: Callable that returns a Protocol instance
        url: Serial port URL
        port: Serial port name
        **kwargs: Serial connection parameters

    Returns:
        Tuple of (SerialTransport, Protocol)

    Example:
        >>> class MyProtocol(asyncio.Protocol):
        ...     def data_received(self, data):
        ...         print(f"Received: {data}")
        ...
        >>> transport, protocol = await create_serial_connection(
        ...     loop,
        ...     MyProtocol,
        ...     port='/dev/ttyUSB0',
        ...     baudrate=115200
        ... )
    """
    # Create serial instance
    serial_instance = await _create_serial_instance(
        url=url, port=port, **kwargs
    )

    # Create protocol
    protocol = protocol_factory()

    # Create transport
    transport = SerialTransport(loop, protocol, serial_instance)

    return transport, protocol


async def _create_serial_instance(**kwargs: Any) -> serial.Serial:
    """
    Create and configure a serial port instance.

    Handles both URL-based and direct port connections.
    """
    url = kwargs.pop('url', None)
    port = kwargs.pop('port', None)

    try:
        if url:
            # URL-based connection (e.g., spy://, rfc2217://)
            def create_url_instance():
                return serial.serial_for_url(url, **kwargs)

            serial_instance = await asyncio.get_event_loop().run_in_executor(
                None, create_url_instance
            )
        else:
            # Direct port connection
            def create_direct_instance():
                return serial.Serial(port=port, **kwargs)

            serial_instance = await asyncio.get_event_loop().run_in_executor(
                None, create_direct_instance
            )

        return serial_instance

    except serial.SerialException as e:
        # Обернуть SerialException в наш SerialConnectionError
        raise SerialConnectionError(f"Failed to open serial port: {e}")
    except Exception as e:
        raise SerialConnectionError(f"Unexpected error opening serial port: {e}")


class SerialStream:
    """
    Context manager for serial stream operations.

    Provides a convenient way to work with serial streams using async context manager.
    """

    def __init__(self, **kwargs):
        self._kwargs = kwargs
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None

    async def __aenter__(self) -> Tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """Enter async context manager"""
        self._reader, self._writer = await open_serial_connection(**self._kwargs)
        return self._reader, self._writer

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager"""
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()

    @property
    def reader(self) -> asyncio.StreamReader:
        """Get the StreamReader"""
        if self._reader is None:
            raise RuntimeError("Stream not opened")
        return self._reader

    @property
    def writer(self) -> asyncio.StreamWriter:
        """Get the StreamWriter"""
        if self._writer is None:
            raise RuntimeError("Stream not opened")
        return self._writer


# Convenient aliases
open_serial = open_serial_connection
create_connection = create_serial_connection
