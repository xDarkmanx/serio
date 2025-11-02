# -*- coding: utf-8 -*-

"""
Compatibility layer for Python 3.12+
Handles StreamReader creation differences between Python versions.
"""
import asyncio
import sys

# Version checking
PYTHON_312 = sys.version_info >= (3, 12)

# Default limit from asyncio
_DEFAULT_LIMIT = 2 ** 16  # 64KB


def create_stream_reader(limit=None, loop=None):
    """
    Create a StreamReader compatible with all Python versions.
    
    In Python 3.13+, StreamReader requires a running event loop.
    This function handles the differences safely.
    """
    if limit is None:
        limit = _DEFAULT_LIMIT
    
    if PYTHON_312:
        # Python 3.12+ - try to create StreamReader safely
        try:
            # Try to get current event loop
            current_loop = asyncio.get_event_loop()
            # If we have a loop, create StreamReader normally
            return asyncio.StreamReader(limit=limit)
        except RuntimeError:
            # No running event loop - create one temporarily
            # This is safe for testing
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                reader = asyncio.StreamReader(limit=limit)
                return reader
            finally:
                loop.close()
                asyncio.set_event_loop(None)
    else:
        # Python 3.11 and below
        if loop is not None:
            return asyncio.StreamReader(limit=limit, loop=loop)
        else:
            return asyncio.StreamReader(limit=limit)


def create_stream_reader_protocol(reader, loop=None):
    """
    Create a StreamReaderProtocol compatible with all Python versions.
    """
    if PYTHON_312:
        return asyncio.StreamReaderProtocol(reader)
    else:
        if loop is not None:
            return asyncio.StreamReaderProtocol(reader, loop=loop)
        else:
            return asyncio.StreamReaderProtocol(reader)
