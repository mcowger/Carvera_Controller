"""
USB/Serial communication stream for CNC machines.

This module provides USB/Serial communication functionality for connecting
to CNC machines via serial ports.
"""

import time
import logging
from typing import Optional

try:
    import serial
except ImportError:
    serial = None

from .xmodem import XMODEM

SERIAL_TIMEOUT = 0.3  # seconds


class USBStreamError(Exception):
    """Exception raised for USB stream errors."""
    pass


class USBStream:
    """
    USB/Serial communication stream for CNC machines.
    
    This class handles USB/Serial communication with CNC machines using
    the pyserial library.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize USB stream.
        
        Args:
            logger: Logger instance to use
        """
        self.logger = logger or logging.getLogger(__name__)
        self.serial = None
        self.modem = XMODEM(self.getc, self.putc, 'xmodem')
        
        # Set up XMODEM logging
        handler = logging.StreamHandler()
        handler.setLevel(logging.WARNING)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.modem.log.addHandler(handler)

    def send(self, data: bytes) -> int:
        """
        Send data to the serial port.
        
        Args:
            data: Data to send
            
        Returns:
            Number of bytes sent
            
        Raises:
            USBStreamError: If not connected or send fails
        """
        if not self.serial:
            raise USBStreamError("Not connected")
            
        try:
            return self.serial.write(data)
        except Exception as e:
            raise USBStreamError(f"Failed to send data: {e}") from e

    def recv(self) -> bytes:
        """
        Receive data from the serial port.
        
        Returns:
            Received data bytes
            
        Raises:
            USBStreamError: If not connected or receive fails
        """
        if not self.serial:
            raise USBStreamError("Not connected")
            
        try:
            return self.serial.read()
        except Exception as e:
            raise USBStreamError(f"Failed to receive data: {e}") from e

    def open(self, address: str) -> bool:
        """
        Open serial connection.
        
        Args:
            address: Serial port address (e.g., '/dev/ttyUSB0', 'COM3')
            
        Returns:
            True if connection successful
            
        Raises:
            USBStreamError: If serial library not available or connection fails
        """
        if serial is None:
            raise USBStreamError("pyserial library not available")
            
        try:
            self.serial = serial.serial_for_url(
                address.replace('\\', '\\\\'),  # Escape for Windows
                115200,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=SERIAL_TIMEOUT,
                write_timeout=SERIAL_TIMEOUT,
                xonxoff=False,
                rtscts=False
            )
            
            # Toggle DTR to reset Arduino
            try:
                self.serial.setDTR(0)
            except IOError:
                pass
            time.sleep(0.5)

            self.serial.flushInput()
            try:
                self.serial.setDTR(1)
            except IOError:
                pass
            time.sleep(0.5)

            self.logger.info(f"Connected to USB device at {address}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to {address}: {e}")
            raise USBStreamError(f"Failed to connect: {e}") from e

    def close(self) -> bool:
        """
        Close serial connection.
        
        Returns:
            True if disconnection successful
        """
        if self.serial is None:
            return True
            
        try:
            time.sleep(0.5)
            self.modem.clear_mode_set()
            self.serial.close()
            self.serial = None
            self.logger.info("USB connection closed")
            return True
        except Exception as e:
            self.logger.error(f"Error closing USB connection: {e}")
            self.serial = None
            return False

    def waiting_for_send(self) -> bool:
        """
        Check if ready to send data.
        
        Returns:
            True if ready to send
        """
        if not self.serial:
            return False
        return self.serial.out_waiting < 1

    def waiting_for_recv(self) -> bool:
        """
        Check if data is available to receive.
        
        Returns:
            True if data available
        """
        if not self.serial:
            return False
        return self.serial.in_waiting > 0

    def getc(self, size: int, timeout: float = 1) -> Optional[bytes]:
        """
        Get characters for XMODEM protocol.
        
        Args:
            size: Number of bytes to read
            timeout: Timeout in seconds
            
        Returns:
            Read bytes or None if timeout
        """
        if not self.serial:
            return None
        return self.serial.read(size) or None

    def putc(self, data: bytes, timeout: float = 1) -> Optional[int]:
        """
        Put characters for XMODEM protocol.
        
        Args:
            data: Data to write
            timeout: Timeout in seconds
            
        Returns:
            Number of bytes written or None if failed
        """
        if not self.serial:
            return None
        return self.serial.write(data) or None

    def upload(self, filename: str, local_md5: str, callback=None) -> bool:
        """
        Upload file using XMODEM protocol.
        
        Args:
            filename: Path to file to upload
            local_md5: MD5 hash of local file
            callback: Progress callback function
            
        Returns:
            True if upload successful
        """
        try:
            with open(filename, 'rb') as stream:
                result = self.modem.send(stream, md5=local_md5, retry=10, callback=callback)
            return result
        except Exception as e:
            self.logger.error(f"Upload failed: {e}")
            return False

    def download(self, filename: str, local_md5: str, callback=None) -> bool:
        """
        Download file using XMODEM protocol.
        
        Args:
            filename: Path to save downloaded file
            local_md5: Expected MD5 hash
            callback: Progress callback function
            
        Returns:
            True if download successful
        """
        try:
            with open(filename, 'wb') as stream:
                result = self.modem.recv(stream, md5=local_md5, retry=10, callback=callback)
            return result
        except Exception as e:
            self.logger.error(f"Download failed: {e}")
            return False

    def cancel_process(self) -> None:
        """Cancel current XMODEM transfer."""
        self.modem.canceled = True

    def is_connected(self) -> bool:
        """
        Check if connected.
        
        Returns:
            True if connected
        """
        return self.serial is not None and self.serial.is_open
