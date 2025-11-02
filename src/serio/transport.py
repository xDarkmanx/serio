# -*- coding: utf-8 -*-

"""
Modern SerialTransport for Python 3.11+
Zero dependencies beyond pyserial, pure async implementation.
"""

import asyncio
import os
import serial

from typing import Any
from typing import Optional
from typing import List

from .exceptions import PlatformNotSupportedError

class SerialTransport(asyncio.Transport):
    """
    Modern asynchronous serial transport.
    
    Features:
    - True async I/O on POSIX (using file descriptors)
    - Efficient polling on Windows (OS limitations)
    - Proper flow control with buffer limits
    - No thread pool overhead
    """

    def __init__(
            self, 
            loop: asyncio.AbstractEventLoop, 
            protocol: asyncio.Protocol,
            serial_instance: serial.Serial,
            *,
            read_buffer_size: int = 4096,
            high_water_mark: int = 65536,
            low_water_mark: int = 16384
        ):
        super().__init__()

        self._loop = loop
        self._protocol = protocol
        self._serial = serial_instance
        self._closing = False
        self._protocol_paused = False

        # Buffer configuration
        self._read_buffer_size = read_buffer_size
        self._high_water_mark = high_water_mark
        self._low_water_mark = low_water_mark
        
        # Buffers and state
        self._write_buffer: List[bytes] = []
        self._write_buffer_size = 0
        
        # Platform-specific async state
        self._reader_active = False
        self._writer_active = False
        self._poll_task: Optional[asyncio.Task] = None
        
        # Configure serial for async
        self._serial.timeout = 0
        self._serial.write_timeout = 0
        
        # Initialize async I/O
        self._setup_async_io()
        
        # Notify protocol
        self._loop.call_soon(self._protocol.connection_made, self)
    
    def _setup_async_io(self):
        """Setup platform-specific async I/O"""
        if os.name == 'posix':
            self._setup_posix_async()
        elif os.name == 'nt':
            self._setup_windows_async()
        else:
            raise PlatformNotSupportedError(
                f'Platform {os.name} not supported for async serial'
            )
    
    def _setup_posix_async(self):
        """POSIX: true async using file descriptors"""
        try:
            fd = self._serial.fileno()
            self._loop.add_reader(fd, self._read_ready)
            self._reader_active = True

        except (OSError, NotImplementedError) as e:
            raise PlatformNotSupportedError(
                f"POSIX async not supported: {e}"
            )
    
    def _setup_windows_async(self):
        """Windows: efficient polling (OS limitations)"""
        self._poll_interval = 0.005  # 5ms for responsiveness
        self._start_polling()
    
    def _start_polling(self):
        """Start polling loop for Windows"""
        if not self._closing and not self._poll_task:
            self._poll_task = asyncio.create_task(self._poll_loop())

    def _flushed(self):
        """True if the write buffer is empty, otherwise False."""
        return self.get_write_buffer_size() == 0
    
    async def _poll_loop(self):
        """Windows polling loop"""
        try:
            while not self._closing:
                # Check for incoming data
                if self._serial.in_waiting > 0:
                    self._read_ready()
                
                # Check for write readiness
                if self._write_buffer and self._serial.out_waiting < 1024:
                    self._write_ready()
                
                # Small sleep to prevent CPU spinning
                await asyncio.sleep(self._poll_interval)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            if not self._closing:
                self._fatal_error(e)
    
    def _read_ready(self):
        """Handle incoming data - called when data is available"""
        if self._closing:
            return
            
        try:
            data = self._serial.read(self._read_buffer_size)
            if data:
                self._protocol.data_received(data)
        except serial.SerialException as e:
            self._fatal_error(e)
        except OSError as e:
            # Port may have been disconnected
            self._fatal_error(e)
    
    def write(self, data: bytes):
        """
        Write data asynchronously.
        
        Data is buffered and sent when the serial port is ready.
        """
        if self._closing:
            return
            
        self._write_buffer.append(data)
        self._write_buffer_size += len(data)
        
        # Start writer if not active
        self._ensure_writer()
        
        # Check flow control
        self._check_flow_control()
    
    def _ensure_writer(self):
        """Ensure writer is active for current platform"""
        if os.name == 'posix' and not self._writer_active:
            try:
                fd = self._serial.fileno()
                self._loop.add_writer(fd, self._write_ready)
                self._writer_active = True
            except (OSError, NotImplementedError):
                # Writer will be handled by polling on Windows
                pass
    
    def _write_ready(self):
        """Handle write readiness - called when port is ready to write"""
        if not self._write_buffer or self._closing:
            self._remove_writer()
            return
            
        # Get next chunk to write
        data = self._write_buffer[0]
        
        try:
            written = self._serial.write(data)
            
            if written == len(data):
                # Full write completed
                self._write_buffer.pop(0)
                self._write_buffer_size -= len(data)
            else:
                # Partial write, update buffer
                self._write_buffer[0] = data[written:]
                self._write_buffer_size -= written
                
        except (BlockingIOError, InterruptedError):
            # Try again later
            pass
        except serial.SerialException as e:
            self._fatal_error(e)
        except OSError as e:
            self._fatal_error(e)
        
        # Check if we need to continue writing
        if not self._write_buffer:
            self._remove_writer()
        
        # Update flow control
        self._check_flow_control()
        
        # If closing and buffer empty, complete close
        if self._closing and not self._write_buffer:
            self._complete_close()

    def _remove_writer(self):
        """Remove writer from event loop (POSIX only)"""
        if os.name == 'posix' and self._writer_active:
            try:
                self._loop.remove_writer(self._serial.fileno())
                self._writer_active = False
            except (OSError, NotImplementedError):
                pass
    
    def _check_flow_control(self):
        """Manage flow control based on buffer levels"""
        if (self._protocol_paused and 
            self._write_buffer_size <= self._low_water_mark):
            # Resume protocol writing
            self._protocol_paused = False
            try:
                self._protocol.resume_writing()
            except Exception as e:
                self._loop.call_exception_handler({
                    'message': 'protocol.resume_writing() failed',
                    'exception': e,
                    'transport': self,
                    'protocol': self._protocol,
                })
        elif (not self._protocol_paused and self._write_buffer_size >= self._high_water_mark):
            # Pause protocol writing
            self._protocol_paused = True
            try:
                self._protocol.pause_writing()
            except Exception as e:
                self._loop.call_exception_handler({
                    'message': 'protocol.pause_writing() failed',
                    'exception': e,
                    'transport': self,
                    'protocol': self._protocol,
                })

    def close(self):
        """Close the transport gracefully"""
        if not self._closing:
            self._closing = True
            
            # Stop reading immediately
            self._cleanup_reader()
            
            # If write buffer empty, close immediately
            if not self._write_buffer:
                self._complete_close()
            # Otherwise, write_ready will call _complete_close when done
    
    def _complete_close(self):
        """Finalize transport closure"""
        self._cleanup_async()
        self._loop.call_soon(self._protocol.connection_lost, None)
    
    def is_closing(self) -> bool:
        return self._closing

    def abort(self):
        """Close the transport immediately, discarding buffered data"""
        self._closing = True
        self._cleanup_async()
        self._write_buffer.clear()
        self._write_buffer_size = 0
        self._loop.call_soon(self._protocol.connection_lost, None)
    
    def _cleanup_reader(self):
        """Clean up reader resources"""
        if os.name == 'posix' and self._reader_active:
            try:
                self._loop.remove_reader(self._serial.fileno())
                self._reader_active = False
            except (OSError, NotImplementedError):
                pass
    
    def _cleanup_async(self):
        """Clean up all async resources"""
        self._cleanup_reader()
        self._remove_writer()
        
        # Cancel polling task
        if self._poll_task and not self._poll_task.done():
            self._poll_task.cancel()
        
        # Close serial port
        if self._serial and self._serial.is_open:
            self._serial.close()
    
    def _fatal_error(self, exc: Exception):
        """Handle fatal errors"""
        if not self._closing:
            self._closing = True
            self._cleanup_async()
            self._loop.call_soon(self._protocol.connection_lost, exc)
    
    def pause_reading(self):
        """Pause receiving data"""
        if os.name == 'posix' and self._reader_active:
            self._loop.remove_reader(self._serial.fileno())
            self._reader_active = False
    
    def resume_reading(self):
        """Resume receiving data"""
        if os.name == 'posix' and not self._reader_active and not self._closing:
            try:
                self._loop.add_reader(self._serial.fileno(), self._read_ready)
                self._reader_active = True
            except (OSError, NotImplementedError):
                pass
    
    def get_extra_info(self, name: str, default: Any = None) -> Any:
        """Get transport information"""
        if name == 'serial':
            return self._serial
        elif name == 'write_buffer_size':
            return self._write_buffer_size
        elif name == 'closing':
            return self._closing
        return default

    def can_write_eof(self):
        """Serial ports don't support EOF"""
        return False

    def write_eof(self):
        """Serial ports don't support EOF"""
        raise NotImplementedError("Serial ports do not support EOF")
    
    def get_write_buffer_size(self) -> int:
        """Get current write buffer size"""
        return self._write_buffer_size

    def set_write_buffer_limits(self, high: Optional[int] = None, low: Optional[int] = None):
        """Set write buffer flow control limits"""
        if high is None:
            high = 65536 if low is None else 4 * low
        if low is None:
            low = high // 4
        
        if not (high >= low >= 0):
            raise ValueError(
                f"high ({high}) must be >= low ({low}) must be >= 0"
            )
        
        self._high_water_mark = high
        self._low_water_mark = low
        self._check_flow_control()

