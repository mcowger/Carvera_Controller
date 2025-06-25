"""
XMODEM file transfer protocol implementation.

This module provides XMODEM protocol support for file transfers
with CNC machines.

Based on the original XMODEM implementation by Wijnand Modderman.
"""

from __future__ import division, print_function

import logging
import time
from typing import Optional, Callable, BinaryIO, Union

__author__ = "Wijnand Modderman <maze@pyth0n.org>"
__copyright__ = [
    "Copyright (c) 2010 Wijnand Modderman",
    "Copyright (c) 1981 Chuck Forsberg",
]
__license__ = "MIT"
__version__ = "0.4.5"

# Protocol bytes
SOH = b"\x01"
STX = b"\x02"
EOT = b"\x04"
ACK = b"\x06"
DLE = b"\x10"
NAK = b"\x15"
CAN = b"\x16"
CRC = b"C"


class XMODEMError(Exception):
    """Base exception for XMODEM errors."""

    pass


class XMODEM:
    """
    XMODEM Protocol handler.

    This class implements the XMODEM file transfer protocol for sending
    and receiving files over serial connections.
    """

    def __init__(
        self,
        getc: Callable,
        putc: Callable,
        mode: str = "xmodem8k",
        pad: bytes = b"\x1a",
    ):
        """
        Initialize XMODEM handler.

        Args:
            getc: Function to read bytes from stream
            putc: Function to write bytes to stream
            mode: XMODEM mode ('xmodem' for 128 bytes, 'xmodem8k' for 8192 bytes)
            pad: Padding byte for incomplete packets
        """
        self.getc = getc
        self.putc = putc
        self.mode = mode
        self.mode_set = False
        self.pad = pad
        self.log = logging.getLogger("xmodem.XMODEM")
        self.canceled = False

    def clear_mode_set(self) -> None:
        """Clear mode set flag."""
        self.mode_set = False

    def abort(self, count: int = 2, timeout: float = 60) -> None:
        """
        Send an abort sequence using CAN bytes.

        Args:
            count: Number of abort characters to send
            timeout: Timeout in seconds
        """
        for _ in range(count):
            self.putc(CAN, timeout)

    def send(
        self,
        stream: BinaryIO,
        md5: str = "",
        retry: int = 16,
        timeout: float = 5,
        quiet: bool = False,
        callback: Optional[Callable] = None,
    ) -> Optional[bool]:
        """
        Send a stream via the XMODEM protocol.

        Args:
            stream: The stream object to send data from
            md5: MD5 hash of the data
            retry: Maximum number of retries for failed packets
            timeout: Timeout in seconds
            quiet: If True, suppress transfer information
            callback: Progress callback function

        Returns:
            True on success, False on failure, None if canceled
        """
        # Determine packet size based on mode
        try:
            packet_size = {
                "xmodem": 128,
                "xmodem8k": 8192,
            }[self.mode]
        except KeyError:
            raise XMODEMError(f"Invalid mode specified: {self.mode}")

        is_stx = 1 if packet_size > 255 else 0

        # Initialize protocol
        error_count = 0
        crc_mode = 0
        cancel = 0
        sequence = 0
        total_packets = 0
        success_count = 0
        md5_sent = False

        # Wait for initial NAK or CRC
        while True:
            char = self.getc(1, timeout)
            if char:
                if char == CRC:
                    crc_mode = 1
                    break
                elif char == NAK:
                    crc_mode = 0
                    break
                elif char == CAN:
                    if cancel:
                        self.log.info("Transmission canceled: received 2xCAN.")
                        return False
                    else:
                        cancel = 1
                else:
                    self.log.debug("send error: expected NAK/CRC, got %r", char)

            error_count += 1
            if error_count > retry:
                self.log.info("send error: error_count reached %d, aborting.", retry)
                self.abort(timeout=timeout)
                return False

        # Send data packets
        while True:
            if self.canceled:
                self.putc(CAN)
                self.putc(CAN)
                self.putc(CAN)
                while self.getc(1, timeout):
                    pass
                self.log.info("Transmission canceled by user.")
                self.canceled = False
                return None

            # Read data
            data = []
            if not md5_sent and sequence == 0:
                data = md5.encode()
                md5_sent = True
            else:
                data = stream.read(packet_size)
                total_packets += 1

            if not data:
                # End of stream
                self.log.debug("send: at EOF")
                break

            # Create packet
            header = self._make_send_header(packet_size, sequence)
            if is_stx == 0:
                data = b"".join(
                    [bytes([len(data) & 0xFF]), data.ljust(packet_size, self.pad)]
                )
            else:
                data = b"".join(
                    [
                        bytes([len(data) >> 8, len(data) & 0xFF]),
                        data.ljust(packet_size, self.pad),
                    ]
                )
            checksum = self._make_send_checksum(crc_mode, data)

            # Send packet
            while True:
                self.log.debug("send: block %d", sequence)
                self.putc(header + data + checksum)
                char = self.getc(1, timeout)

                if char == ACK:
                    success_count += 1
                    if callable(callback):
                        callback(packet_size, total_packets, success_count, error_count)
                    error_count = 0
                    break
                elif char == CAN:
                    if cancel:
                        self.log.info("Transmission canceled: received 2xCAN.")
                        return False
                    else:
                        self.log.debug("Cancellation at Transmission.")
                        cancel = 1
                elif char == NAK:
                    self.log.debug("send error: NAK received")
                    error_count += 1
                    if error_count > retry:
                        self.log.info(
                            "send error: error_count reached %d, aborting.", retry
                        )
                        self.abort(timeout=timeout)
                        return False
                else:
                    self.log.debug("send error: expected ACK/NAK; got %r", char)
                    error_count += 1
                    if error_count > retry:
                        self.log.info(
                            "send error: error_count reached %d, aborting.", retry
                        )
                        self.abort(timeout=timeout)
                        return False

            sequence = (sequence + 1) % 0x100

        # Send EOT
        error_count = 0
        while True:
            self.log.debug("sending EOT, awaiting ACK")
            self.putc(EOT)

            char = self.getc(1, timeout)
            if char == ACK:
                break
            else:
                self.log.error("send error: expected ACK; got %r", char)
                error_count += 1
                if error_count > retry:
                    self.log.warning("EOT was not ACKd, aborting transfer")
                    self.abort(timeout=timeout)
                    return False

        self.log.info("Transmission successful (ACK received).")
        return True

    def _make_send_header(self, packet_size: int, sequence: int) -> bytearray:
        """
        Create packet header.

        Args:
            packet_size: Size of data packet
            sequence: Sequence number

        Returns:
            Header bytes
        """
        assert packet_size in (128, 8192), packet_size
        _bytes = []
        if packet_size == 128:
            _bytes.append(ord(SOH))
        elif packet_size == 8192:
            _bytes.append(ord(STX))
        _bytes.extend([sequence, 0xFF - sequence])
        return bytearray(_bytes)

    def _make_send_checksum(self, crc_mode: int, data: bytes) -> bytearray:
        """
        Create packet checksum.

        Args:
            crc_mode: 1 for CRC, 0 for simple checksum
            data: Data to checksum

        Returns:
            Checksum bytes
        """
        _bytes = []
        if crc_mode:
            crc = self.calc_crc(data)
            _bytes.extend([crc >> 8, crc & 0xFF])
        else:
            crc = self.calc_checksum(data)
            _bytes.append(crc)
        return bytearray(_bytes)

    def _verify_recv_checksum(self, crc_mode: int, data: bytes) -> tuple:
        """
        Verify received packet checksum.

        Args:
            crc_mode: 1 for CRC, 0 for simple checksum
            data: Data including checksum

        Returns:
            Tuple of (valid, data_without_checksum)
        """
        if crc_mode:
            _checksum = bytearray(data[-2:])
            their_sum = (_checksum[0] << 8) + _checksum[1]
            data = data[:-2]

            our_sum = self.calc_crc(data)
            valid = bool(their_sum == our_sum)
            if not valid:
                self.log.warning(
                    "recv error: checksum fail (theirs=%04x, ours=%04x)",
                    their_sum,
                    our_sum,
                )
        else:
            _checksum = bytearray([data[-1]])
            their_sum = _checksum[0]
            data = data[:-1]

            our_sum = self.calc_checksum(data)
            valid = their_sum == our_sum
            if not valid:
                self.log.warning(
                    "recv error: checksum fail (theirs=%02x, ours=%02x)",
                    their_sum,
                    our_sum,
                )
        return valid, data

    def calc_crc(self, data: bytes, crc: int = 0) -> int:
        """
        Calculate CRC16 checksum.

        Args:
            data: Data to checksum
            crc: Initial CRC value

        Returns:
            CRC16 checksum
        """
        for byte in bytearray(data):
            tbl_idx = ((crc >> 8) ^ byte) & 0xFF
            crc = ((crc << 8) ^ self.crctable[tbl_idx]) & 0xFFFF
        return crc & 0xFFFF

    def calc_checksum(self, data: bytes) -> int:
        """
        Calculate simple checksum.

        Args:
            data: Data to checksum

        Returns:
            Simple checksum
        """
        return sum(bytearray(data)) & 0xFF

    # CRC16 lookup table
    crctable = [
        0x0000,
        0x1021,
        0x2042,
        0x3063,
        0x4084,
        0x50A5,
        0x60C6,
        0x70E7,
        0x8108,
        0x9129,
        0xA14A,
        0xB16B,
        0xC18C,
        0xD1AD,
        0xE1CE,
        0xF1EF,
        0x1231,
        0x0210,
        0x3273,
        0x2252,
        0x52B5,
        0x4294,
        0x72F7,
        0x62D6,
        0x9339,
        0x8318,
        0xB37B,
        0xA35A,
        0xD3BD,
        0xC39C,
        0xF3FF,
        0xE3DE,
        0x2462,
        0x3443,
        0x0420,
        0x1401,
        0x64E6,
        0x74C7,
        0x44A4,
        0x5485,
        0xA56A,
        0xB54B,
        0x8528,
        0x9509,
        0xE5EE,
        0xF5CF,
        0xC5AC,
        0xD58D,
        0x3653,
        0x2672,
        0x1611,
        0x0630,
        0x76D7,
        0x66F6,
        0x5695,
        0x46B4,
        0xB75B,
        0xA77A,
        0x9719,
        0x8738,
        0xF7DF,
        0xE7FE,
        0xD79D,
        0xC7BC,
        0x48C4,
        0x58E5,
        0x6886,
        0x78A7,
        0x0840,
        0x1861,
        0x2802,
        0x3823,
        0xC9CC,
        0xD9ED,
        0xE98E,
        0xF9AF,
        0x8948,
        0x9969,
        0xA90A,
        0xB92B,
        0x5AF5,
        0x4AD4,
        0x7AB7,
        0x6A96,
        0x1A71,
        0x0A50,
        0x3A33,
        0x2A12,
        0xDBFD,
        0xCBDC,
        0xFBBF,
        0xEB9E,
        0x9B79,
        0x8B58,
        0xBB3B,
        0xAB1A,
        0x6CA6,
        0x7C87,
        0x4CE4,
        0x5CC5,
        0x2C22,
        0x3C03,
        0x0C60,
        0x1C41,
        0xEDAE,
        0xFD8F,
        0xCDEC,
        0xDDCD,
        0xAD2A,
        0xBD0B,
        0x8D68,
        0x9D49,
        0x7E97,
        0x6EB6,
        0x5ED5,
        0x4EF4,
        0x3E13,
        0x2E32,
        0x1E51,
        0x0E70,
        0xFF9F,
        0xEFBE,
        0xDFDD,
        0xCFFC,
        0xBF1B,
        0xAF3A,
        0x9F59,
        0x8F78,
        0x9188,
        0x81A9,
        0xB1CA,
        0xA1EB,
        0xD10C,
        0xC12D,
        0xF14E,
        0xE16F,
        0x1080,
        0x00A1,
        0x30C2,
        0x20E3,
        0x5004,
        0x4025,
        0x7046,
        0x6067,
        0x83B9,
        0x9398,
        0xA3FB,
        0xB3DA,
        0xC33D,
        0xD31C,
        0xE37F,
        0xF35E,
        0x02B1,
        0x1290,
        0x22F3,
        0x32D2,
        0x4235,
        0x5214,
        0x6277,
        0x7256,
        0xB5EA,
        0xA5CB,
        0x95A8,
        0x8589,
        0xF56E,
        0xE54F,
        0xD52C,
        0xC50D,
        0x34E2,
        0x24C3,
        0x14A0,
        0x0481,
        0x7466,
        0x6447,
        0x5424,
        0x4405,
        0xA7DB,
        0xB7FA,
        0x8799,
        0x97B8,
        0xE75F,
        0xF77E,
        0xC71D,
        0xD73C,
        0x26D3,
        0x36F2,
        0x0691,
        0x16B0,
        0x6657,
        0x7676,
        0x4615,
        0x5634,
        0xD94C,
        0xC96D,
        0xF90E,
        0xE92F,
        0x99C8,
        0x89E9,
        0xB98A,
        0xA9AB,
        0x5844,
        0x4865,
        0x7806,
        0x6827,
        0x18C0,
        0x08E1,
        0x3882,
        0x28A3,
        0xCB7D,
        0xDB5C,
        0xEB3F,
        0xFB1E,
        0x8BF9,
        0x9BD8,
        0xABBB,
        0xBB9A,
        0x4A75,
        0x5A54,
        0x6A37,
        0x7A16,
        0x0AF1,
        0x1AD0,
        0x2AB3,
        0x3A92,
        0xFD2E,
        0xED0F,
        0xDD6C,
        0xCD4D,
        0xBDAA,
        0xAD8B,
        0x9DE8,
        0x8DC9,
        0x7C26,
        0x6C07,
        0x5C64,
        0x4C45,
        0x3CA2,
        0x2C83,
        0x1CE0,
        0x0CC1,
        0xEF1F,
        0xFF3E,
        0xCF5D,
        0xDF7C,
        0xAF9B,
        0xBFBA,
        0x8FD9,
        0x9FF8,
        0x6E17,
        0x7E36,
        0x4E55,
        0x5E74,
        0x2E93,
        0x3EB2,
        0x0ED1,
        0x1EF0,
    ]
