"""
WiFi/TCP communication stream for CNC machines.

This module provides WiFi/TCP communication functionality for connecting
to CNC machines over network connections.
"""

import sys
import time
import socket
import select
import logging
from typing import Optional, List, Dict, Any

from .xmodem import XMODEM

TCP_PORT = 2222
UDP_PORT = 3333
BUFFER_SIZE = 1024
SOCKET_TIMEOUT = 0.3  # seconds


class WiFiStreamError(Exception):
    """Exception raised for WiFi stream errors."""

    pass


class MachineDetector:
    """
    Machine discovery class for finding CNC machines on the network.

    This class uses UDP broadcast to discover available CNC machines
    on the local network.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize machine detector.

        Args:
            logger: Logger instance to use
        """
        self.logger = logger or logging.getLogger(__name__)
        self.machine_list = []
        self.machine_name_list = []
        self.sock = None
        self.t = None
        self.tr = None

    def is_machine_busy(self, addr: str) -> bool:
        """
        Check if machine is busy by attempting connection.

        Args:
            addr: Machine IP address

        Returns:
            True if machine is busy, False if available
        """
        try:
            with socket.create_connection((addr, TCP_PORT), timeout=1):
                return False
        except (socket.timeout, socket.error):
            return True

    def query_for_machines(self) -> None:
        """Start querying for machines on the network."""
        UDP_IP = "0.0.0.0"
        try:
            self.machine_list = []
            self.machine_name_list = []
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.settimeout(1)
            self.sock.bind((UDP_IP, UDP_PORT))
            self.t = self.tr = time.time()
            self.logger.info("Started machine discovery")
        except Exception as e:
            self.logger.error(f"Failed to start machine discovery: {e}")

    def check_for_responses(self) -> Optional[List[Dict[str, Any]]]:
        """
        Check for machine discovery responses.

        Returns:
            List of discovered machines or None if still discovering
        """
        try:
            if self.t - self.tr < 3:
                fields = []
                try:
                    data, addr = self.sock.recvfrom(128)
                    fields = data.decode("utf-8").split(",")
                except socket.timeout:
                    pass
                except Exception as e:
                    self.logger.debug(f"Discovery response error: {e}")

                if len(fields) > 3 and fields[0] not in self.machine_name_list:
                    self.machine_name_list.append(fields[0])
                    machine_info = {
                        "machine": fields[0],
                        "ip": fields[1],
                        "port": int(fields[2]),
                        "busy": fields[3] == "1",
                    }
                    self.machine_list.append(machine_info)
                    self.logger.info(f"Discovered machine: {machine_info}")

                self.t = time.time()
                return None
            else:
                self.sock.close()
                self.logger.info(
                    f"Discovery complete, found {len(self.machine_list)} machines"
                )
                return self.machine_list
        except Exception as e:
            self.logger.error(f"Discovery error: {e}")
            return []


class WIFIStream:
    """
    WiFi/TCP communication stream for CNC machines.

    This class handles TCP socket communication with CNC machines
    over WiFi/Ethernet connections.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize WiFi stream.

        Args:
            logger: Logger instance to use
        """
        self.logger = logger or logging.getLogger(__name__)
        self.socket = None
        self.modem = XMODEM(self.getc, self.putc, "xmodem8k")

        # Set up XMODEM logging
        handler = logging.StreamHandler()
        handler.setLevel(logging.WARNING)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        self.modem.log.addHandler(handler)

    def send(self, data: bytes) -> int:
        """
        Send data to the socket.

        Args:
            data: Data to send

        Returns:
            Number of bytes sent

        Raises:
            WiFiStreamError: If not connected or send fails
        """
        if not self.socket:
            self.logger.error("Attempted to send data while not connected")
            raise WiFiStreamError("Not connected")

        try:
            bytes_sent = self.socket.send(data)
            self.logger.debug(f"WiFi sent {bytes_sent} bytes: {data!r}")
            return bytes_sent
        except Exception as e:
            self.logger.error(f"WiFi send failed: {e}")
            raise WiFiStreamError(f"Failed to send data: {e}") from e

    def recv(self) -> bytes:
        """
        Receive data from the socket.

        Returns:
            Received data bytes

        Raises:
            WiFiStreamError: If not connected or receive fails
        """
        if not self.socket:
            self.logger.error("Attempted to receive data while not connected")
            raise WiFiStreamError("Not connected")

        try:
            data = self.socket.recv(BUFFER_SIZE)
            if data:
                self.logger.debug(f"WiFi received {len(data)} bytes: {data!r}")
            return data
        except Exception as e:
            self.logger.error(f"WiFi receive failed: {e}")
            raise WiFiStreamError(f"Failed to receive data: {e}") from e

    def open(self, address: str) -> bool:
        """
        Open TCP connection.

        Args:
            address: Address in format "ip:port" or just "ip" (uses default port)

        Returns:
            True if connection successful

        Raises:
            WiFiStreamError: If connection fails
        """
        try:
            self.logger.debug(f"Creating TCP socket for connection to {address}")
            self.socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
            ip_port = address.split(":")
            ip = ip_port[0]
            port = int(ip_port[1]) if len(ip_port) > 1 else TCP_PORT

            self.logger.debug(f"Connecting to {ip}:{port} with 2s timeout")
            self.socket.settimeout(2)
            self.socket.connect((ip, port))
            self.socket.settimeout(SOCKET_TIMEOUT)

            self.logger.info(f"WiFi connection established to {ip}:{port}")
            self.logger.debug(f"Socket timeout set to {SOCKET_TIMEOUT}s")
            return True

        except Exception as e:
            self.logger.error(f"WiFi connection failed to {address}: {e}")
            if self.socket:
                try:
                    self.socket.close()
                except:
                    pass
                self.socket = None
            raise WiFiStreamError(f"Failed to connect: {e}") from e

    def close(self) -> bool:
        """
        Close TCP connection.

        Returns:
            True if disconnection successful
        """
        if self.socket is None:
            return True

        try:
            self.modem.clear_mode_set()
            self.socket.close()
            self.socket = None
            self.logger.info("WiFi connection closed")
            return True
        except Exception as e:
            self.logger.error(f"Error closing WiFi connection: {e}")
            self.socket = None
            return False

    def waiting_for_send(self) -> bool:
        """
        Check if ready to send data.

        Returns:
            True if ready to send
        """
        if not self.socket:
            return False

        try:
            _, write_sockets, _ = select.select([], [self.socket], [], 0)
            return len(write_sockets) > 0
        except Exception:
            return False

    def waiting_for_recv(self) -> bool:
        """
        Check if data is available to receive.

        Returns:
            True if data available
        """
        if not self.socket:
            return False

        try:
            read_sockets, _, _ = select.select([self.socket], [], [], 0)
            return len(read_sockets) > 0
        except Exception:
            return False

    def getc(self, size: int, timeout: float = 0.5) -> Optional[bytes]:
        """
        Get characters for XMODEM protocol.

        Args:
            size: Number of bytes to read
            timeout: Timeout in seconds

        Returns:
            Read bytes or None if timeout
        """
        if not self.socket:
            return None

        t1 = time.time()
        data = bytearray()

        while len(data) < size and time.time() - t1 <= timeout:
            if self.waiting_for_recv():
                try:
                    chunk = self.socket.recv(size - len(data))
                    if chunk:
                        data.extend(chunk)
                except Exception as e:
                    self.logger.debug(f"getc error: {e}")
                    break
            else:
                time.sleep(0.0001)

        return bytes(data) if len(data) == size else None

    def putc(self, data: bytes, timeout: float = 0.5) -> Optional[int]:
        """
        Put characters for XMODEM protocol.

        Args:
            data: Data to write
            timeout: Timeout in seconds

        Returns:
            Number of bytes written or None if failed
        """
        if not self.socket:
            return None
        return self.socket.send(data) or None

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
            with open(filename, "rb") as stream:
                result = self.modem.send(
                    stream, md5=local_md5, retry=10, callback=callback
                )
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
            with open(filename, "wb") as stream:
                result = self.modem.recv(
                    stream, md5=local_md5, retry=10, callback=callback
                )
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
        return self.socket is not None
