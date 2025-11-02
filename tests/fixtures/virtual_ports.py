"""
Fixtures for virtual serial port testing.
Provides mock and virtual serial ports for reliable testing.
"""
import pytest
import os
import tempfile
from unittest.mock import Mock, MagicMock
from typing import Tuple, Generator

try:
    import pyvirtualserial
    HAS_VIRTUAL_SERIAL = True
except ImportError:
    HAS_VIRTUAL_SERIAL = False

@pytest.fixture
def virtual_serial_pair() -> Generator[Tuple[str, str], None, None]:
    """
    Create a pair of virtual serial ports connected to each other.
    
    Returns:
        Tuple of (port1, port2) port names
    """
    if not HAS_VIRTUAL_SERIAL or os.name != 'posix':
        pytest.skip("Virtual serial ports not supported on this platform")
    
    # On Linux, use socat to create virtual serial pair
    import subprocess
    import time
    
    # Create temporary PTY devices
    result1 = subprocess.run([
        'socat', '-d', '-d', 'pty,raw,echo=0', 'pty,raw,echo=0'], capture_output=True, text=True)
    
    # Parse output to get PTY device names
    lines = result1.stderr.split('\n')
    pty1 = None
    pty2 = None
    
    for line in lines:
        if 'N PTY is' in line:
            if pty1 is None:
                pty1 = line.split('N PTY is ')[1].strip()
            else:
                pty2 = line.split('N PTY is ')[1].strip()
    
    if pty1 and pty2:
        # Wait for devices to be created
        time.sleep(0.1)
        yield pty1, pty2
        
        # Cleanup
        try:
            subprocess.run(['pkill', '-f', f'socat.*{pty1}'])
        except:
            pass
    else:
        pytest.skip("Failed to create virtual serial ports")

@pytest.fixture
def mock_serial_config():
    """
    Provide standard mock serial configuration.
    """
    return {
        'port': '/dev/ttyTEST0',
        'baudrate': 115200,
        'bytesize': 8,
        'parity': 'N',
        'stopbits': 1,
        'timeout': 0,
        'write_timeout': 0,
        'xonxoff': False,
        'rtscts': False
    }

@pytest.fixture
def simulated_serial_data():
    """
    Provide simulated serial data for testing.
    """
    return {
        'simple_response': b"OK\r\n",
        'multiline_response': b"Line 1\r\nLine 2\r\nLine 3\r\n",
        'binary_data': bytes(range(256)),
        'large_data': b"X" * 4096,
        'error_response': b"ERROR: Invalid command\r\n"
    }

@pytest.fixture
def serial_echo_server():
    """
    Mock serial port that echoes back received data.
    Useful for testing read/write operations.
    """
    class EchoSerial(Mock):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._input_buffer = bytearray()
            self._output_buffer = bytearray()
            self.is_open = True
            self.in_waiting = 0
            self.out_waiting = 0
            
        def write(self, data):
            # Echo data back to input buffer
            self._input_buffer.extend(data)
            self.in_waiting = len(self._input_buffer)
            return len(data)
            
        def read(self, size=1):
            if not self._input_buffer:
                return b""
                
            # Return data from input buffer
            data = bytes(self._input_buffer[:size])
            self._input_buffer = self._input_buffer[size:]
            self.in_waiting = len(self._input_buffer)
            return data
            
        def flush(self):
            self._input_buffer.clear()
            self._output_buffer.clear()
            self.in_waiting = 0
            self.out_waiting = 0
            
        def close(self):
            self.is_open = False
            self.flush()
    
    return EchoSerial()

@pytest.fixture
def delayed_serial_response():
    """
    Mock serial with delayed responses for testing async timeouts.
    """
    class DelayedSerial(Mock):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._response_delay = 0.1  # 100ms delay
            self._response_data = b"DELAYED_RESPONSE\r\n"
            self.is_open = True
            self.in_waiting = 0
            
        async def read(self, size=1):
            # Simulate delayed response
            import asyncio
            await asyncio.sleep(self._response_delay)
            self.in_waiting = 0
            return self._response_data
            
        def write(self, data):
            # Trigger response availability after write
            self.in_waiting = len(self._response_data)
            return len(data)
    
    return DelayedSerial()

@pytest.fixture(params=[9600, 115200, 230400, 460800, 921600])
def different_baudrates(request):
    """
    Parametrized fixture for testing different baud rates.
    """
    return request.param

@pytest.fixture(params=['/dev/ttyUSB0', '/dev/ttyACM0', 'COM1', 'COM3'])
def different_port_names(request):
    """
    Parametrized fixture for testing different port names.
    """
    return request.param

@pytest.fixture
def serial_with_preloaded_data():
    """
    Mock serial port with preloaded data in buffer.
    """
    class PreloadedSerial(Mock):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._buffer = bytearray(b"PRELOADED_DATA:12345\r\n")
            self.is_open = True
            self.in_waiting = len(self._buffer)
            
        def read(self, size=1):
            if not self._buffer:
                return b""
                
            data = bytes(self._buffer[:size])
            self._buffer = self._buffer[size:]
            self.in_waiting = len(self._buffer)
            return data
            
        def write(self, data):
            # Ignore writes, just return success
            return len(data)
    
    return PreloadedSerial()
