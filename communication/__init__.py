"""
Communication module for CNC controller.

This module provides communication interfaces for connecting to CNC machines
via different protocols (USB/Serial, WiFi/TCP).
"""

from .usb_stream import USBStream
from .wifi_stream import WIFIStream, MachineDetector
from .xmodem import XMODEM, EOT, CAN

__all__ = ['USBStream', 'WIFIStream', 'MachineDetector', 'XMODEM', 'EOT', 'CAN']
