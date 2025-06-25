"""
CNC Controller Library - Core CNC machine control without UI dependencies.

This library provides core functionality for controlling CNC machines,
including G-code parsing, machine communication, and state management.

Main Components:
- CNC: G-code parser and machine state management
- Controller: Main controller for machine communication
- Communication: USB/Serial and WiFi/TCP communication modules
- Utils: Utility functions for common operations

Example Usage:
    from cnc_controller import Controller
    from cnc_core import CNC
    
    # Create CNC instance
    cnc = CNC()
    
    # Create controller
    controller = Controller(cnc)
    
    # Connect to machine
    controller.connect("192.168.1.100:2222", CONN_WIFI)
    
    # Send commands
    controller.send_command("G28")  # Home
    controller.send_command("G0 X10 Y10")  # Move
    
    # Disconnect
    controller.disconnect()
"""

from .cnc_core import CNC, CNCError, GCodeParseError
from .cnc_controller import Controller, ControllerError, ConnectionError, CommandError
from .cnc_controller import CONN_USB, CONN_WIFI, MSG_NORMAL, MSG_ERROR, MSG_INTERIOR
from .cnc_utils import (
    humansize, humandate, second2hour, md5_file, xfrange, translate,
    digitize_version, safe_float, safe_int, clamp, find_serial_ports,
    validate_gcode_line, parse_coordinate_string, FileWatcher
)

# Import communication modules
try:
    from .communication import USBStream, WIFIStream, MachineDetector, XMODEM, EOT, CAN
except ImportError:
    # Fallback for development/testing
    USBStream = None
    WIFIStream = None
    MachineDetector = None
    XMODEM = None
    EOT = None
    CAN = None

__version__ = "1.0.0"
__author__ = "CNC Controller Community"
__license__ = "GPL-2.0"

__all__ = [
    # Core classes
    'CNC', 'Controller',
    
    # Exceptions
    'CNCError', 'GCodeParseError', 'ControllerError', 'ConnectionError', 'CommandError',
    
    # Constants
    'CONN_USB', 'CONN_WIFI', 'MSG_NORMAL', 'MSG_ERROR', 'MSG_INTERIOR',
    
    # Communication
    'USBStream', 'WIFIStream', 'MachineDetector', 'XMODEM', 'EOT', 'CAN',
    
    # Utilities
    'humansize', 'humandate', 'second2hour', 'md5_file', 'xfrange', 'translate',
    'digitize_version', 'safe_float', 'safe_int', 'clamp', 'find_serial_ports',
    'validate_gcode_line', 'parse_coordinate_string', 'FileWatcher'
]
