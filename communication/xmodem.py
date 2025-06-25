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

__author__ = 'Wijnand Modderman <maze@pyth0n.org>'
__copyright__ = ['Copyright (c) 2010 Wijnand Modderman',
                 'Copyright (c) 1981 Chuck Forsberg']
__license__ = 'MIT'
__version__ = '0.4.5'

# Protocol bytes
SOH = b'\x01'
STX = b'\x02'
EOT = b'\x04'
ACK = b'\x06'
DLE = b'\x10'
NAK = b'\x15'
CAN = b'\x16'
CRC = b'C'


class XMODEMError(Exception):
    """Base exception for XMODEM errors."""
    pass


class XMODEM:
    """
    XMODEM Protocol handler.
    
    This class implements the XMODEM file transfer protocol for sending
    and receiving files over serial connections.
    """

    def __init__(self, getc: Callable, putc: Callable, mode: str = 'xmodem8k', 
                 pad: bytes = b'\x1a'):
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
        self.log = logging.getLogger('xmodem.XMODEM')
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

    def send(self, stream: BinaryIO, md5: str = '', retry: int = 16, 
             timeout: float = 5, quiet: bool = False, 
             callback: Optional[Callable] = None) -> Optional[bool]:
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
                'xmodem': 128,
                'xmodem8k': 8192,
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
                        self.log.info('Transmission canceled: received 2xCAN.')
                        return False
                    else:
                        cancel = 1
                else:
                    self.log.debug('send error: expected NAK/CRC, got %r', char)

            error_count += 1
            if error_count > retry:
                self.log.info('send error: error_count reached %d, aborting.', retry)
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
                self.log.info('Transmission canceled by user.')
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
                self.log.debug('send: at EOF')
                break

            # Create packet
            header = self._make_send_header(packet_size, sequence)
            if is_stx == 0:
                data = b''.join([bytes([len(data) & 0xff]), data.ljust(packet_size, self.pad)])
            else:
                data = b''.join([bytes([len(data) >> 8, len(data) & 0xff]), data.ljust(packet_size, self.pad)])
            checksum = self._make_send_checksum(crc_mode, data)

            # Send packet
            while True:
                self.log.debug('send: block %d', sequence)
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
                        self.log.info('Transmission canceled: received 2xCAN.')
                        return False
                    else:
                        self.log.debug('Cancellation at Transmission.')
                        cancel = 1
                elif char == NAK:
                    self.log.debug('send error: NAK received')
                    error_count += 1
                    if error_count > retry:
                        self.log.info('send error: error_count reached %d, aborting.', retry)
                        self.abort(timeout=timeout)
                        return False
                else:
                    self.log.debug('send error: expected ACK/NAK; got %r', char)
                    error_count += 1
                    if error_count > retry:
                        self.log.info('send error: error_count reached %d, aborting.', retry)
                        self.abort(timeout=timeout)
                        return False

            sequence = (sequence + 1) % 0x100

        # Send EOT
        error_count = 0
        while True:
            self.log.debug('sending EOT, awaiting ACK')
            self.putc(EOT)

            char = self.getc(1, timeout)
            if char == ACK:
                break
            else:
                self.log.error('send error: expected ACK; got %r', char)
                error_count += 1
                if error_count > retry:
                    self.log.warning('EOT was not ACKd, aborting transfer')
                    self.abort(timeout=timeout)
                    return False

        self.log.info('Transmission successful (ACK received).')
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
        _bytes.extend([sequence, 0xff - sequence])
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
            _bytes.extend([crc >> 8, crc & 0xff])
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
                self.log.warning('recv error: checksum fail (theirs=%04x, ours=%04x)',
                               their_sum, our_sum)
        else:
            _checksum = bytearray([data[-1]])
            their_sum = _checksum[0]
            data = data[:-1]

            our_sum = self.calc_checksum(data)
            valid = their_sum == our_sum
            if not valid:
                self.log.warning('recv error: checksum fail (theirs=%02x, ours=%02x)',
                               their_sum, our_sum)
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
            tbl_idx = ((crc >> 8) ^ byte) & 0xff
            crc = ((crc << 8) ^ self.crctable[tbl_idx]) & 0xffff
        return crc & 0xffff

    def calc_checksum(self, data: bytes) -> int:
        """
        Calculate simple checksum.

        Args:
            data: Data to checksum

        Returns:
            Simple checksum
        """
        return sum(bytearray(data)) & 0xff

    # CRC16 lookup table
    crctable = [
        0x0000, 0x1021, 0x2042, 0x3063, 0x4084, 0x50a5, 0x60c6, 0x70e7,
        0x8108, 0x9129, 0xa14a, 0xb16b, 0xc18c, 0xd1ad, 0xe1ce, 0xf1ef,
        0x1231, 0x0210, 0x3273, 0x2252, 0x52b5, 0x4294, 0x72f7, 0x62d6,
        0x9339, 0x8318, 0xb37b, 0xa35a, 0xd3bd, 0xc39c, 0xf3ff, 0xe3de,
        0x2462, 0x3443, 0x0420, 0x1401, 0x64e6, 0x74c7, 0x44a4, 0x5485,
        0xa56a, 0xb54b, 0x8528, 0x9509, 0xe5ee, 0xf5cf, 0xc5ac, 0xd58d,
        0x3653, 0x2672, 0x1611, 0x0630, 0x76d7, 0x66f6, 0x5695, 0x46b4,
        0xb75b, 0xa77a, 0x9719, 0x8738, 0xf7df, 0xe7fe, 0xd79d, 0xc7bc,
        0x48c4, 0x58e5, 0x6886, 0x78a7, 0x0840, 0x1861, 0x2802, 0x3823,
        0xc9cc, 0xd9ed, 0xe98e, 0xf9af, 0x8948, 0x9969, 0xa90a, 0xb92b,
        0x5af5, 0x4ad4, 0x7ab7, 0x6a96, 0x1a71, 0x0a50, 0x3a33, 0x2a12,
        0xdbfd, 0xcbdc, 0xfbbf, 0xeb9e, 0x9b79, 0x8b58, 0xbb3b, 0xab1a,
        0x6ca6, 0x7c87, 0x4ce4, 0x5cc5, 0x2c22, 0x3c03, 0x0c60, 0x1c41,
        0xedae, 0xfd8f, 0xcdec, 0xddcd, 0xad2a, 0xbd0b, 0x8d68, 0x9d49,
        0x7e97, 0x6eb6, 0x5ed5, 0x4ef4, 0x3e13, 0x2e32, 0x1e51, 0x0e70,
        0xff9f, 0xefbe, 0xdfdd, 0xcffc, 0xbf1b, 0xaf3a, 0x9f59, 0x8f78,
        0x9188, 0x81a9, 0xb1ca, 0xa1eb, 0xd10c, 0xc12d, 0xf14e, 0xe16f,
        0x1080, 0x00a1, 0x30c2, 0x20e3, 0x5004, 0x4025, 0x7046, 0x6067,
        0x83b9, 0x9398, 0xa3fb, 0xb3da, 0xc33d, 0xd31c, 0xe37f, 0xf35e,
        0x02b1, 0x1290, 0x22f3, 0x32d2, 0x4235, 0x5214, 0x6277, 0x7256,
        0xb5ea, 0xa5cb, 0x95a8, 0x8589, 0xf56e, 0xe54f, 0xd52c, 0xc50d,
        0x34e2, 0x24c3, 0x14a0, 0x0481, 0x7466, 0x6447, 0x5424, 0x4405,
        0xa7db, 0xb7fa, 0x8799, 0x97b8, 0xe75f, 0xf77e, 0xc71d, 0xd73c,
        0x26d3, 0x36f2, 0x0691, 0x16b0, 0x6657, 0x7676, 0x4615, 0x5634,
        0xd94c, 0xc96d, 0xf90e, 0xe92f, 0x99c8, 0x89e9, 0xb98a, 0xa9ab,
        0x5844, 0x4865, 0x7806, 0x6827, 0x18c0, 0x08e1, 0x3882, 0x28a3,
        0xcb7d, 0xdb5c, 0xeb3f, 0xfb1e, 0x8bf9, 0x9bd8, 0xabbb, 0xbb9a,
        0x4a75, 0x5a54, 0x6a37, 0x7a16, 0x0af1, 0x1ad0, 0x2ab3, 0x3a92,
        0xfd2e, 0xed0f, 0xdd6c, 0xcd4d, 0xbdaa, 0xad8b, 0x9de8, 0x8dc9,
        0x7c26, 0x6c07, 0x5c64, 0x4c45, 0x3ca2, 0x2c83, 0x1ce0, 0x0cc1,
        0xef1f, 0xff3e, 0xcf5d, 0xdf7c, 0xaf9b, 0xbfba, 0x8fd9, 0x9ff8,
        0x6e17, 0x7e36, 0x4e55, 0x5e74, 0x2e93, 0x3eb2, 0x0ed1, 0x1ef0,
    ]
