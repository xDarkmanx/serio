# Serio: Modern Asynchronous Serial Communication Library

![Python Version](https://img.shields.io/badge/Python-3.11%20–%203.13-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Build Status](https://github.com/xDarkmanx/serio/workflows/Python%20package/badge.svg)
![Coverage](https://coveralls.io/repos/github/xDarkmanx/serio/badge.svg?branch=main)

**Serio** is a modern asynchronous serial port library for Python 3.11+ that provides efficient, native async I/O without thread pool overhead. It offers both high-level streams API and low-level transport API for serial communication.

## Features

- ✅ **True async I/O** (no thread pool overhead)
- ✅ **Python 3.11+ native support**
- ✅ **Clean, modern API** with asyncio integration
- ✅ **POSIX and Windows support**
- ✅ **High-level Streams API** (StreamReader/StreamWriter)
- ✅ **Low-level Transport API** for custom protocols
- ✅ **Platform-optimized async I/O** (polling on Windows, file descriptors on POSIX)
- ✅ **Proper flow control** with buffer management
- ✅ Comprehensive exception handling

## Installation

```bash
pip install serio
```

## Getting Started

### High-Level API Example

```python
import asyncio
from serio import open_serial_connection

async def main():
    reader, writer = await open_serial_connection(
        port='/dev/ttyUSB0',
        baudrate=115200
    )
    
    writer.write(b'AT\r\n')
    response = await reader.readuntil(b'\r\n')
    print(f"Received: {response.decode()}")

asyncio.run(main())
```

### Low-Level API Example

```python
import asyncio
from serio import create_serial_connection, SerialTransport

class MyProtocol(asyncio.Protocol):
    def connection_made(self, transport):
        print("Connection established")
        
    def data_received(self, data):
        print(f"Received: {data}")
        
    def connection_lost(self, exc):
        print("Connection closed")

async def main():
    loop = asyncio.get_running_loop()
    transport, protocol = await create_serial_connection(
        loop,
        MyProtocol,
        port='/dev/ttyUSB0',
        baudrate=115200
    )
    
    transport.write(b'AT\r\n')
    await asyncio.sleep(1)
    transport.close()

asyncio.run(main())
```

### Context Manager Example

```python
from serio import SerialStream

async def main():
    async with SerialStream(port='/dev/ttyUSB0', baudrate=115200) as (reader, writer):
        writer.write(b'AT\r\n')
        response = await reader.readuntil(b'\r\n')
        print(f"Received: {response.decode()}")

asyncio.run(main())
```

## API Reference

### High-Level API

- `open_serial_connection(**kwargs) -> (StreamReader, StreamWriter)`
- `create_serial_connection(loop, protocol_factory, **kwargs) -> (SerialTransport, Protocol)`
- `SerialStream(**kwargs)` - Context manager for serial connections

### Low-Level API

- `SerialTransport(loop, protocol, serial_instance)` - Asynchronous serial transport
- `SerialError` - Base exception class
- `SerialConnectionError` - Raised when connection fails
- `SerialConfigError` - Raised for invalid configuration
- `PlatformNotSupportedError` - Raised for unsupported platforms

## Configuration Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `port` | Serial port name (e.g., `/dev/ttyUSB0` or `COM3`) | None |
| `baudrate` | Baud rate | 9600 |
| `bytesize` | Data bits | `serial.EIGHTBITS` |
| `parity` | Parity checking | `serial.PARITY_NONE` |
| `stopbits` | Stop bits | `serial.STOPBITS_ONE` |
| `timeout` | Read timeout (seconds) | None |
| `xonxoff` | Software flow control | False |
| `rtscts` | Hardware (RTS/CTS) flow control | False |
| `write_timeout` | Write timeout (seconds) | None |
| `dsrdtr` | Hardware (DSR/DTR) flow control | False |
| `inter_byte_timeout` | Inter-character timeout | None |
| `exclusive` | Exclusive access mode | None |


## Platform Support

- **POSIX**: Uses file descriptors for true async I/O
- **Windows**: Uses efficient polling (5ms intervals)
- **Unsupported**: Other platforms will raise `PlatformNotSupportedError`

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues.

---

**Author**: Semenets V. Pavel  
**Version**: 0.1.0  
**Email**: [p.semenets@gmail.com](mailto:p.semenets@gmail.com)
