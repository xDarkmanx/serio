# -*- coding: utf-8 -*-

"""
Serio - Modern asynchronous serial port library for Python 3.13+

Features:
- True async I/O (no thread pool overhead)
- Python 3.13+ native support  
- Clean, modern API
- POSIX and Windows support
- High-level Streams API and low-level Transport API
"""

from .transport import SerialTransport
from .streams import open_serial_connection

from .streams import create_serial_connection
from .streams import SerialStream
from .streams import open_serial
from .streams import create_connection

from .exceptions import SerioError
from .exceptions import SerialConnectionError
from .exceptions import SerialConfigError
from .exceptions import PlatformNotSupportedError

__version__ = "0.1.0"
__author__ = "Semenets V. Pavel" 
__license__ = "MIT"

__all__ = [
    # Transports
    'SerialTransport',
    
    # High-level API
    'open_serial_connection',
    'create_serial_connection', 
    'SerialStream',
    'open_serial',
    'create_connection',
    
    # Exceptions
    'SerioError',
    'SerialConnectionError',
    'SerialConfigError', 
    'PlatformNotSupportedError',
]
