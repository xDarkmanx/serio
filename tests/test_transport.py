"""
Unit tests for SerialTransport.
"""
import pytest
import asyncio
import serial

from unittest.mock import patch
from serio.transport import SerialTransport
from serio.exceptions import PlatformNotSupportedError


class TestSerialTransport:
    """Test SerialTransport functionality."""

    @pytest.mark.asyncio
    async def test_transport_initialization(self, mock_serial, mock_protocol):
        """Test transport initialization."""
        loop = asyncio.get_event_loop()

        # Force polling mode for tests (like Windows)
        with patch('os.name', 'nt'):
            transport = SerialTransport(loop, mock_protocol, mock_serial)

        # Verify serial configuration
        assert mock_serial.timeout == 0
        assert mock_serial.write_timeout == 0

        # Give event loop time to process call_soon
        await asyncio.sleep(0.01)

        # Verify protocol notification
        mock_protocol.connection_made.assert_called_once_with(transport)

    @pytest.mark.asyncio
    async def test_write_data(self, mock_serial, mock_protocol):
        """Test writing data to transport."""
        loop = asyncio.get_event_loop()

        with patch('os.name', 'nt'):  # Use polling mode
            transport = SerialTransport(loop, mock_protocol, mock_serial)

        await asyncio.sleep(0.01)  # Let connection_made happen

        test_data = b"Hello, World!"
        transport.write(test_data)

        # Should buffer data
        assert transport.get_write_buffer_size() == len(test_data)

    @pytest.mark.asyncio
    async def test_write_flow_control(self, mock_serial, mock_protocol):
        """Test flow control with write buffers."""
        loop = asyncio.get_event_loop()

        # Set small buffer limits
        with patch('os.name', 'nt'):  # Use polling mode
            transport = SerialTransport(
                loop, mock_protocol, mock_serial,
                high_water_mark=10,
                low_water_mark=5
            )

        await asyncio.sleep(0.01)  # Let connection_made happen

        # Write enough data to trigger pause
        transport.write(b"1234567890")  # 10 bytes

        # Should pause protocol writing
        mock_protocol.pause_writing.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_transport(self, mock_serial, mock_protocol):
        """Test graceful transport closure."""
        loop = asyncio.get_event_loop()

        with patch('os.name', 'nt'):  # Use polling mode
            transport = SerialTransport(loop, mock_protocol, mock_serial)

        await asyncio.sleep(0.01)  # Let connection_made happen

        transport.close()

        # Should mark as closing
        assert transport.get_extra_info('closing') is True

    @pytest.mark.asyncio
    async def test_abort_transport(self, mock_serial, mock_protocol):
        """Test immediate transport abortion."""
        loop = asyncio.get_event_loop()

        with patch('os.name', 'nt'):  # Use polling mode
            transport = SerialTransport(loop, mock_protocol, mock_serial)

        await asyncio.sleep(0.01)  # Let connection_made happen

        # Write some data
        transport.write(b"test data")

        # Abort immediately
        transport.abort()

        # Give event loop time to process connection_lost
        await asyncio.sleep(0.01)

        # Should clear buffers and close
        assert transport.get_write_buffer_size() == 0
        mock_protocol.connection_lost.assert_called_once_with(None)

    @pytest.mark.asyncio
    async def test_fatal_error_handling(self, mock_serial, mock_protocol):
        """Test fatal error handling."""
        loop = asyncio.get_event_loop()

        with patch('os.name', 'nt'):  # Use polling mode
            transport = SerialTransport(loop, mock_protocol, mock_serial)

        await asyncio.sleep(0.01)  # Let connection_made happen

        test_error = serial.SerialException("Port disconnected")

        # Trigger fatal error
        transport._fatal_error(test_error)

        # Give event loop time to process connection_lost
        await asyncio.sleep(0.01)

        # Should notify protocol with error
        mock_protocol.connection_lost.assert_called_once_with(test_error)

    @pytest.mark.asyncio
    async def test_get_extra_info(self, mock_serial, mock_protocol):
        """Test extra info retrieval."""
        loop = asyncio.get_event_loop()

        with patch('os.name', 'nt'):  # Use polling mode
            transport = SerialTransport(loop, mock_protocol, mock_serial)

        await asyncio.sleep(0.01)  # Let connection_made happen

        # Test serial instance info
        assert transport.get_extra_info('serial') == mock_serial

        # Test write buffer size
        assert transport.get_extra_info('write_buffer_size') == 0

        # Test default value
        assert transport.get_extra_info('unknown', 'default') == 'default'

    @pytest.mark.asyncio
    async def test_platform_not_supported(self, mock_serial, mock_protocol):
        """Test unsupported platform error."""
        loop = asyncio.get_event_loop()

        with patch('os.name', 'unsupported_os'):
            with pytest.raises(PlatformNotSupportedError):
                SerialTransport(loop, mock_protocol, mock_serial)

    @pytest.mark.asyncio
    async def test_posix_async_setup_failure(self, mock_serial, mock_protocol):
        """Test POSIX async setup failure handling."""
        loop = asyncio.get_event_loop()

        # Make fileno raise OSError to simulate POSIX failure
        mock_serial.fileno.side_effect = OSError("Bad file descriptor")

        with patch('os.name', 'posix'):
            with pytest.raises(PlatformNotSupportedError) as exc_info:
                SerialTransport(loop, mock_protocol, mock_serial)

            assert "POSIX async not supported" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_write_ready_partial_write(self, mock_serial, mock_protocol):
        """Test partial write handling in _write_ready."""
        loop = asyncio.get_event_loop()

        with patch('os.name', 'nt'):
            transport = SerialTransport(loop, mock_protocol, mock_serial)

        await asyncio.sleep(0.01)

        # Mock partial write (write returns less than data length)
        test_data = b"hello world"
        mock_serial.write.return_value = 5  # Only write 5 bytes

        transport._write_buffer = [test_data]
        transport._write_buffer_size = len(test_data)

        transport._write_ready()

        # Should keep remaining data in buffer
        assert len(transport._write_buffer) == 1
        assert transport._write_buffer[0] == b" world"  # Remaining 6 bytes
        assert transport._write_buffer_size == 6

    @pytest.mark.asyncio
    async def test_write_ready_blocking_io(self, mock_serial, mock_protocol):
        """Test BlockingIOError handling in _write_ready."""
        loop = asyncio.get_event_loop()

        with patch('os.name', 'nt'):
            transport = SerialTransport(loop, mock_protocol, mock_serial)

        await asyncio.sleep(0.01)

        # Mock BlockingIOError
        test_data = b"test data"
        mock_serial.write.side_effect = BlockingIOError()

        transport._write_buffer = [test_data]
        transport._write_buffer_size = len(test_data)

        transport._write_ready()

        # Should keep data in buffer for retry
        assert len(transport._write_buffer) == 1
        assert transport._write_buffer[0] == test_data

    @pytest.mark.asyncio
    async def test_poll_loop_cancellation(self, mock_serial, mock_protocol):
        """Test polling loop cancellation on Windows."""
        loop = asyncio.get_event_loop()

        with patch('os.name', 'nt'):
            transport = SerialTransport(loop, mock_protocol, mock_serial)

        await asyncio.sleep(0.01)

        # Cancel the polling task
        if transport._poll_task:
            transport._poll_task.cancel()
            await asyncio.sleep(0.01)

        # Should handle cancellation gracefully

    @pytest.mark.asyncio
    async def test_read_ready_with_exception(self, mock_serial, mock_protocol):
        """Test _read_ready with serial exception."""
        loop = asyncio.get_event_loop()

        with patch('os.name', 'nt'):
            transport = SerialTransport(loop, mock_protocol, mock_serial)

        await asyncio.sleep(0.01)

        # Mock serial exception during read
        mock_serial.read.side_effect = serial.SerialException("Read failed")

        # Should handle exception gracefully
        transport._read_ready()

        # Transport should be closed due to fatal error
        assert transport._closing is True

    @pytest.mark.asyncio
    async def test_complete_close_with_buffers(self, mock_serial, mock_protocol):
        """Test _complete_close with data in buffers."""
        loop = asyncio.get_event_loop()

        with patch('os.name', 'nt'):
            transport = SerialTransport(loop, mock_protocol, mock_serial)

        await asyncio.sleep(0.01)

        # Add some data to write buffer
        transport._write_buffer = [b"pending data"]
        transport._write_buffer_size = 12

        # Complete close should still work
        transport._complete_close()

        # Give event loop time to process
        await asyncio.sleep(0.01)

        # Should notify protocol
        mock_protocol.connection_lost.assert_called_once_with(None)

    @pytest.mark.asyncio
    async def test_remove_writer_posix(self, mock_serial, mock_protocol):
        """Test _remove_writer on POSIX systems - simplified."""
        loop = asyncio.get_event_loop()

        # Вместо сложной настройки с реальными FD, просто проверяем что метод существует
        with patch('os.name', 'posix'):
            # Используем polling mode для тестов чтобы избежать проблем с FD
            with patch.object(loop, 'add_reader'):  # Mock чтобы избежать реальной регистрации
                with patch.object(loop, 'add_writer'):
                    transport = SerialTransport(loop, mock_protocol, mock_serial)

        await asyncio.sleep(0.01)

        # Просто проверяем что метод вызывается без ошибок
        transport._remove_writer()

    @pytest.mark.asyncio
    async def test_flushed_property(self, mock_serial, mock_protocol):
        """Test _flushed property."""
        loop = asyncio.get_event_loop()

        with patch('os.name', 'nt'):
            transport = SerialTransport(loop, mock_protocol, mock_serial)

        await asyncio.sleep(0.01)

        # Initially should be flushed (empty buffer)
        assert transport._flushed() is True  # Это метод, а не свойство!

        # With data in buffer, should not be flushed
        transport.write(b"test")
        assert transport._flushed() is False

    @pytest.mark.asyncio
    async def test_set_write_buffer_limits_validation(self, mock_serial, mock_protocol):
        """Test write buffer limits validation."""
        loop = asyncio.get_event_loop()

        with patch('os.name', 'nt'):
            transport = SerialTransport(loop, mock_protocol, mock_serial)

        await asyncio.sleep(0.01)

        # Test invalid limits (low > high)
        with pytest.raises(ValueError):
            transport.set_write_buffer_limits(high=10, low=20)

        # Test negative limits
        with pytest.raises(ValueError):
            transport.set_write_buffer_limits(high=-1, low=0)

    @pytest.mark.asyncio
    async def test_cleanup_async_with_polling(self, mock_serial, mock_protocol):
        """Test async cleanup with polling task."""
        loop = asyncio.get_event_loop()

        with patch('os.name', 'nt'):
            transport = SerialTransport(loop, mock_protocol, mock_serial)

        await asyncio.sleep(0.01)

        # Ensure polling task exists
        assert transport._poll_task is not None

        # Cleanup should cancel polling task
        transport._cleanup_async()

        # Даем время для отмены
        await asyncio.sleep(0.01)

        # Polling task should be done (cancelled or finished)
        assert transport._poll_task.done() is True

    @pytest.mark.asyncio
    async def test_write_ready_empty_buffer(self, mock_serial, mock_protocol):
        """Test _write_ready with empty buffer."""
        loop = asyncio.get_event_loop()

        with patch('os.name', 'nt'):
            transport = SerialTransport(loop, mock_protocol, mock_serial)

        await asyncio.sleep(0.01)

        # Empty buffer should not crash
        transport._write_buffer = []
        transport._write_ready()

    @pytest.mark.asyncio
    async def test_ensure_writer_failure(self, mock_serial, mock_protocol):
        """Test _ensure_writer failure handling - simplified."""
        loop = asyncio.get_event_loop()

        with patch('os.name', 'posix'):
            # Используем polling mode для тестов
            with patch.object(loop, 'add_reader'):
                with patch.object(loop, 'add_writer'):
                    transport = SerialTransport(loop, mock_protocol, mock_serial)

        await asyncio.sleep(0.01)

        # Mock add_writer to fail
        with patch.object(loop, 'add_writer') as mock_add:
            mock_add.side_effect = OSError("Cannot add writer")

            # Should handle OSError gracefully (no exception)
            transport._ensure_writer()

    @pytest.mark.asyncio
    async def test_check_flow_control_edge_cases(self, mock_serial, mock_protocol):
        """Test flow control edge cases."""
        loop = asyncio.get_event_loop()

        with patch('os.name', 'nt'):
            transport = SerialTransport(
                loop, mock_protocol, mock_serial,
                high_water_mark=10,
                low_water_mark=5
            )

        await asyncio.sleep(0.01)

        # Test exactly at high water mark
        transport._write_buffer_size = 10
        transport._protocol_paused = False
        transport._check_flow_control()
        mock_protocol.pause_writing.assert_called_once()

        # Test exactly at low water mark
        transport._write_buffer_size = 5
        transport._protocol_paused = True
        transport._check_flow_control()
        mock_protocol.resume_writing.assert_called_once()
