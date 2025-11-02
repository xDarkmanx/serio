# -*- coding: utf-8 -*-

"""
Serio exceptions
"""

class SerioError(Exception):
    """Base exception for all serio errors"""
    pass

class SerialConnectionError(SerioError):
    """Failed to connect to serial port"""
    pass

class SerialConfigError(SerioError):
    """Invalid serial configuration"""
    pass

class PlatformNotSupportedError(SerioError):
    """Platform not supported for async operations"""
    pass

