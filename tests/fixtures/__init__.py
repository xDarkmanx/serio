"""
Test fixtures for serio testing.

Provides mock serial ports, virtual port pairs, and simulated serial devices
for comprehensive testing without hardware dependencies.
"""

from .virtual_ports import (
    virtual_serial_pair,
    mock_serial_config,
    simulated_serial_data,
    serial_echo_server,
    delayed_serial_response,
    different_baudrates,
    different_port_names,
    serial_with_preloaded_data,
)

__all__ = [
    'virtual_serial_pair',
    'mock_serial_config',
    'simulated_serial_data',
    'serial_echo_server',
    'delayed_serial_response',
    'different_baudrates',
    'different_port_names',
    'serial_with_preloaded_data',
]
