"""
CNC Controller Module - Main controller for CNC machine communication.

This module provides the main controller class that manages communication
with CNC machines, handles command queuing, and processes responses.
"""

import re
import sys
import time
import threading
import logging
from datetime import datetime
from typing import Optional, Union, List
from queue import Queue, Empty
from threading import Event

from cnc_core import CNC

# Import communication modules
try:
    from communication.usb_stream import USBStream
    from communication.wifi_stream import WIFIStream
    from communication.xmodem import EOT, CAN
except ImportError:
    # Fallback for development
    from carveracontroller.USBStream import USBStream
    from carveracontroller.WIFIStream import WIFIStream
    from carveracontroller.XMODEM import EOT, CAN

# Constants
STREAM_POLL = 0.2  # seconds
DIAGNOSE_POLL = 0.5  # seconds
RX_BUFFER_SIZE = 128

# Regular expressions for parsing responses
GPAT = re.compile(r"[A-Za-z]\s*[-+]?\d+.*")
FEEDPAT = re.compile(r"^(.*)[fF](\d+\.?\d+)(.*)$")
STATUSPAT = re.compile(
    r"^<(\w*?),MPos:([+\-]?\d*\.\d*),([+\-]?\d*\.\d*),([+\-]?\d*\.\d*),WPos:([+\-]?\d*\.\d*),([+\-]?\d*\.\d*),([+\-]?\d*\.\d*),?(.*)>$"
)
POSPAT = re.compile(
    r"^\[(...):([+\-]?\d*\.\d*),([+\-]?\d*\.\d*),([+\-]?\d*\.\d*):?(\d*)\]$"
)
TLOPAT = re.compile(r"^\[(...):([+\-]?\d*\.\d*)\]$")

# Pattern to detect GCODE commands (G or M commands)
GCODE_PATTERN = re.compile(r"^\s*[GM]\d+", re.IGNORECASE)
DOLLARPAT = re.compile(r"^\[G\d* .*\]$")
SPLITPAT = re.compile(r"[:,]")
VARPAT = re.compile(r"^\$(\d+)=(\d*\.?\d*) *\(?.*")

# Connection types
CONN_USB = 0
CONN_WIFI = 1

# Message types
MSG_NORMAL = 0
MSG_ERROR = 1
MSG_INTERIOR = 2

# State colors (for reference, not used in core)
CONNECTED = "Wait"
NOT_CONNECTED = "N/A"


class ControllerError(Exception):
    """Base exception for controller errors."""

    pass


class ConnectionError(ControllerError):
    """Exception raised when connection fails."""

    pass


class CommandError(ControllerError):
    """Exception raised when command execution fails."""

    pass


class Controller:
    """
    Main CNC controller class.

    This class manages communication with CNC machines, handles command queuing,
    processes responses, and maintains machine state.
    """

    def __init__(
        self, cnc: Optional[CNC] = None, logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the controller.

        Args:
            cnc: CNC instance to use, creates new one if None
            logger: Logger instance to use, creates new one if None
        """
        # Set up logging
        self.logger = logger or logging.getLogger(__name__)

        # Initialize CNC
        self.cnc = cnc or CNC()

        # Initialize communication streams
        self.usb_stream = USBStream()
        self.wifi_stream = WIFIStream()
        self.stream = None
        self.modem = None
        self.connection_type = CONN_WIFI

        # Command history
        self.history = []
        self._history_pos = None

        # Communication queues
        self.log = Queue()  # Log queue returned from machine
        self.queue = Queue()  # Command queue to be sent to machine
        self.load_buffer = Queue()
        self.load_buffer_size = 0
        self.total_buffer_size = 0

        # Loading state
        self.load_num = 0
        self.load_eof = False
        self.load_err = False
        self.load_cancel = False
        self.load_cancel_sent = False

        # Sending state
        self.send_num = 0
        self.send_eof = False
        self.send_cancel = False

        # Threading
        self.thread = None
        self.stop_event = threading.Event()

        # Keep-alive functionality
        self._last_status_time = 0
        self._last_diagnose_time = 0
        self._running = False  # True when sending/loading commands

        # Update flags
        self.pos_update = False
        self.diagnose_update = False
        self._probe_update = False
        self._g_update = False
        self._update = None

        # Response tracking for GCODE commands
        self._response_event = Event()
        self._last_response = None
        self._waiting_for_response = False

        # Control flags
        self.clean_after = False
        self._run_lines = 0
        self._quit = 0
        self._stop = False
        self._pause = False
        self._alarm = True
        self._msg = None
        self._sumcline = 0
        self._last_feed = 0
        self._new_feed = 0

        # Event handlers
        self._on_start = ""
        self._on_stop = ""

        # State flags
        self.paused = False
        self.pausing = False
        self.diagnosing = False

    def connect(self, address: str, connection_type: int = CONN_WIFI) -> bool:
        """
        Connect to CNC machine.

        Args:
            address: Connection address (IP:port for WiFi, device path for USB)
            connection_type: CONN_WIFI or CONN_USB

        Returns:
            True if connection successful, False otherwise

        Raises:
            ConnectionError: If connection fails
        """
        try:
            self.connection_type = connection_type
            conn_type_str = "WiFi" if connection_type == CONN_WIFI else "USB"
            self.logger.info(f"Attempting {conn_type_str} connection to {address}")

            if connection_type == CONN_WIFI:
                self.stream = self.wifi_stream
                success = self.wifi_stream.open(address)
            else:
                self.stream = self.usb_stream
                success = self.usb_stream.open(address)

            if success:
                self.logger.info(f"Successfully connected to CNC machine at {address}")
                self.logger.debug(
                    f"Connection details: type={conn_type_str}, stream={type(self.stream).__name__}"
                )
                # Start the keep-alive thread
                self._start_stream_thread()
                return True
            else:
                self.logger.error(f"Connection attempt failed to {address}")
                raise ConnectionError(f"Failed to connect to {address}")

        except Exception as e:
            self.logger.error(f"Connection failed with exception: {e}")
            raise ConnectionError(f"Connection failed: {e}") from e

    def disconnect(self) -> bool:
        """
        Disconnect from CNC machine.

        Returns:
            True if disconnection successful
        """
        try:
            # Stop the keep-alive thread first
            self._stop_stream_thread()

            if self.stream:
                self.stream.close()
                self.stream = None
                self.logger.info("Disconnected from CNC machine")
            return True
        except Exception as e:
            self.logger.error(f"Disconnection error: {e}")
            return False

    def is_connected(self) -> bool:
        """
        Check if connected to CNC machine.

        Returns:
            True if connected, False otherwise
        """
        return self.stream is not None

    def send_command(
        self, command: str, wait_for_response: bool = False, timeout: float = 30.0
    ) -> Union[bool, str]:
        """
        Send a command to the CNC machine.

        Args:
            command: Command string to send
            wait_for_response: Whether to wait for a response
            timeout: Timeout in seconds for response (default 30.0)

        Returns:
            If wait_for_response is False: True if command was sent successfully
            If wait_for_response is True: Response string or None if timeout

        Raises:
            CommandError: If command sending fails
        """
        if not self.is_connected():
            raise CommandError("Not connected to CNC machine")

        try:
            if command and self.stream:
                if not command.endswith("\n"):
                    command += "\n"

                # Set up response waiting if requested
                if wait_for_response:
                    self._response_event.clear()
                    self._last_response = None
                    self._waiting_for_response = True

                encoded_command = command.encode()
                self.stream.send(encoded_command)
                self.logger.info(f"Executing command: {command.strip()}")
                self.logger.debug(
                    f"Raw data sent: {encoded_command!r} ({len(encoded_command)} bytes)"
                )

                # Add to history
                if command.strip() and command.strip() not in self.history:
                    self.history.append(command.strip())
                    if len(self.history) > 100:  # Limit history size
                        self.history.pop(0)

                # Wait for response if requested
                if wait_for_response:
                    if self._response_event.wait(timeout):
                        response = self._last_response
                        self._waiting_for_response = False
                        return response
                    else:
                        self._waiting_for_response = False
                        self.logger.warning(
                            f"Timeout waiting for response to command: {command.strip()}"
                        )
                        return None

                return True

        except Exception as e:
            self._waiting_for_response = False
            self.logger.error(f"Failed to send command '{command}': {e}")
            raise CommandError(f"Failed to send command: {e}") from e

        return False

    def execute_gcode(
        self, line: str, wait_for_ok: bool = True, timeout: float = 30.0
    ) -> Union[bool, str]:
        """
        Execute a line as G-code if pattern matches.

        Args:
            line: G-code line to execute
            wait_for_ok: Whether to wait for 'ok' response for GCODE commands
            timeout: Timeout in seconds for response (default 30.0)

        Returns:
            If wait_for_ok is False: True on success, False otherwise
            If wait_for_ok is True: 'ok' if successful, None if timeout, False if not GCODE
        """
        if (
            isinstance(line, tuple)
            or line[0] in ("$", "!", "~", "?", "(", "@")
            or GPAT.match(line)
        ):
            # Check if this is a GCODE command that should wait for 'ok'
            is_gcode = GCODE_PATTERN.match(line.strip())

            if is_gcode and wait_for_ok:
                response = self.send_command(
                    line, wait_for_response=True, timeout=timeout
                )
                if response is None:
                    self.logger.warning(
                        f"Timeout waiting for response to GCODE: {line.strip()}"
                    )
                    return None
                elif response.strip().lower() == "ok":
                    self.logger.debug(f"GCODE command successful: {line.strip()}")
                    return "ok"
                else:
                    self.logger.warning(
                        f"Unexpected response to GCODE '{line.strip()}': {response}"
                    )
                    return response
            else:
                # Non-GCODE command or not waiting for response
                return self.send_command(line)
        return False

    def auto_command(
        self,
        margin: bool = False,
        zprobe: bool = False,
        zprobe_abs: bool = False,
        leveling: bool = False,
        goto_origin: bool = False,
        z_probe_offset_x: float = 0,
        z_probe_offset_y: float = 0,
        i: int = 3,
        j: int = 3,
        h: int = 5,
        buffer: bool = False,
        auto_level_offsets: List[float] = None,
    ) -> bool:
        """
        Execute automatic commands like margin detection, probing, and leveling.

        Args:
            margin: Enable margin detection
            zprobe: Enable Z probing
            zprobe_abs: Use absolute Z probe positioning
            leveling: Enable auto-leveling
            goto_origin: Go to origin after operation
            z_probe_offset_x: X offset for Z probe
            z_probe_offset_y: Y offset for Z probe
            i: Grid points in X direction
            j: Grid points in Y direction
            h: Height parameter
            buffer: Use buffered commands
            auto_level_offsets: List of auto-level offsets [x1, x2, y1, y2]

        Returns:
            True if commands were sent successfully
        """
        if auto_level_offsets is None:
            auto_level_offsets = [0, 0, 0, 0]

        if not (margin or zprobe or leveling or goto_origin):
            return False

        if (
            abs(self.cnc["xmin"]) > self.cnc["worksize_x"]
            or abs(self.cnc["ymin"]) > self.cnc["worksize_y"]
        ):
            return False

        cmd = f"M495 X{self.cnc['xmin']:g}Y{self.cnc['ymin']:g}"

        if margin:
            cmd = cmd + f"C{self.cnc['xmax']:g}D{self.cnc['ymax']:g}"
            if buffer:
                cmd = "buffer " + cmd
            self.send_command(cmd)

        # Reinitialize command with any autolevel offsets
        cmd = f"M495 X{self.cnc['xmin'] + auto_level_offsets[0]:g}Y{self.cnc['ymin'] + auto_level_offsets[2]:g}"

        if zprobe:
            if zprobe_abs:
                cmd = f"M495 X{self.cnc['xmin']:g}Y{self.cnc['ymin']:g}"
                cmd = cmd + "O0"
            else:
                cmd = cmd + f"O{z_probe_offset_x:g}F{z_probe_offset_y:g}"

        if leveling:
            width = self.cnc["xmax"] - (
                self.cnc["xmin"] + auto_level_offsets[1] + auto_level_offsets[0]
            )
            height = self.cnc["ymax"] - (
                self.cnc["ymin"] + auto_level_offsets[3] + auto_level_offsets[2]
            )
            cmd = cmd + f"A{width:g}B{height:g}I{i:d}J{j:d}H{h:d}"

        if goto_origin:
            cmd = cmd + "P1"

        if buffer:
            cmd = "buffer " + cmd

        return self.send_command(cmd)

    def xyz_probe(
        self, height: float = 9.0, diameter: float = 3.175, buffer: bool = False
    ) -> bool:
        """
        Execute XYZ probe command.

        Args:
            height: Probe height
            diameter: Probe diameter
            buffer: Use buffered command

        Returns:
            True if command was sent successfully
        """
        cmd = f"M495.3 H{height:g} D{diameter:g}"
        if buffer:
            cmd = "buffer " + cmd
        return self.send_command(cmd)

    def pair_wp(self) -> bool:
        """
        Pair workpiece command.

        Returns:
            True if command was sent successfully
        """
        return self.send_command("M471")

    def sync_time(self) -> bool:
        """
        Synchronize time with machine.

        Returns:
            True if command was sent successfully
        """
        import time

        timestamp = str(int(time.time()) - time.timezone)
        return self.send_command(f"time {timestamp}")

    def query_time(self) -> bool:
        """Query machine time."""
        return self.send_command("time")

    def query_version(self) -> bool:
        """Query machine version."""
        return self.send_command("version")

    def query_model(self) -> bool:
        """Query machine model."""
        return self.send_command("model")

    def query_ftype(self) -> bool:
        """Query file type support."""
        return self.send_command("ftype")

    def goto_position(self, position: str, buffer: bool = False) -> bool:
        """
        Go to a predefined position.

        Args:
            position: Position name ("Clearance", "Work Origin", "Anchor1", "Anchor2", "Path Origin")
            buffer: Use buffered command

        Returns:
            True if command was sent successfully
        """
        cmd = ""
        if position == "Clearance":
            cmd = "M496.1"
        elif position == "Work Origin":
            cmd = "M496.2"
        elif position == "Anchor1":
            cmd = "M496.3"
        elif position == "Anchor2":
            cmd = "M496.4"
        elif position == "Path Origin":
            if (
                abs(self.cnc["xmin"]) <= self.cnc["worksize_x"]
                and abs(self.cnc["ymin"]) <= self.cnc["worksize_y"]
            ):
                cmd = f"M496.5 X{self.cnc['xmin']:g}Y{self.cnc['ymin']:g}"

        if cmd:
            if buffer:
                cmd = "buffer " + cmd
            return self.send_command(cmd)
        return False

    def reset(self) -> bool:
        """Reset the machine."""
        return self.send_command("reset")

    def change_tool(self) -> bool:
        """Initiate tool change."""
        return self.send_command("M490.2")

    def set_feed_scale(self, scale: int) -> bool:
        """
        Set feed rate scale.

        Args:
            scale: Feed rate scale percentage (0-200)
        """
        return self.send_command(f"M220 S{scale:d}")

    def set_laser_scale(self, scale: int) -> bool:
        """
        Set laser power scale.

        Args:
            scale: Laser power scale percentage (0-100)
        """
        return self.send_command(f"M325 S{scale:d}")

    def set_spindle_scale(self, scale: int) -> bool:
        """
        Set spindle speed scale.

        Args:
            scale: Spindle speed scale percentage (0-200)
        """
        return self.send_command(f"M223 S{scale:d}")

    def clear_auto_leveling(self) -> bool:
        """Clear auto-leveling data."""
        return self.send_command("M370")

    def set_spindle_switch(self, switch: bool, rpm: int = 0) -> bool:
        """
        Control spindle on/off.

        Args:
            switch: True to turn on, False to turn off
            rpm: RPM when turning on
        """
        if switch:
            return self.send_command(f"M3 S{rpm:d}")
        else:
            return self.send_command("M5")

    def home_machine(self) -> bool:
        """Home all axes."""
        return self.send_command("$H")

    def get_status(self) -> bool:
        """Request machine status."""
        return self.send_command("?")

    def get_position(self) -> bool:
        """Request current position."""
        return self.send_command("$#")

    def jog(
        self,
        x: Optional[float] = None,
        y: Optional[float] = None,
        z: Optional[float] = None,
        a: Optional[float] = None,
        speed: Optional[float] = None,
    ) -> bool:
        """
        Jog machine axes.

        Args:
            x: X axis movement
            y: Y axis movement
            z: Z axis movement
            a: A axis movement
            speed: Jog speed scale

        Returns:
            True if jog command was sent successfully
        """
        cmd = "$J"
        if x is not None:
            cmd += f" X{x:g}"
        if y is not None:
            cmd += f" Y{y:g}"
        if z is not None:
            cmd += f" Z{z:g}"
        if a is not None:
            cmd += f" A{a:g}"
        if speed is not None:
            cmd += f" S{speed:g}"

        if len(cmd) > 2:  # More than just "$J"
            return self.send_command(cmd)
        return False

    def stop_motion(self) -> bool:
        """Stop current motion (feed hold)."""
        return self.send_command("!")

    def resume_motion(self) -> bool:
        """Resume motion after feed hold."""
        return self.send_command("~")

    def soft_reset(self) -> bool:
        """Send soft reset (Ctrl-X)."""
        return self.send_command("\x18")  # Ctrl-X

    def unlock_alarm(self) -> bool:
        """Unlock alarm state."""
        return self.send_command("$X")

    def get_log_messages(self) -> List[tuple]:
        """
        Get pending log messages from the queue.

        Returns:
            List of (message_type, message) tuples
        """
        messages = []
        try:
            while True:
                message = self.log.get_nowait()
                messages.append(message)
        except Empty:
            pass
        return messages

    def add_to_history(self, command: str) -> None:
        """
        Add command to history.

        Args:
            command: Command to add to history
        """
        if command and command not in self.history:
            self.history.append(command)
            if len(self.history) > 100:
                self.history.pop(0)

    def get_history(self) -> List[str]:
        """
        Get command history.

        Returns:
            List of historical commands
        """
        return self.history.copy()

    def clear_history(self) -> None:
        """Clear command history."""
        self.history.clear()
        self._history_pos = None

    def _start_stream_thread(self) -> None:
        """Start the background stream I/O thread for keep-alive functionality."""
        if self.thread is None or not self.thread.is_alive():
            self.stop_event.clear()
            self.thread = threading.Thread(target=self._stream_io_loop, daemon=True)
            self.thread.start()
            self.logger.debug("Started stream I/O thread")

    def _stop_stream_thread(self) -> None:
        """Stop the background stream I/O thread."""
        if self.thread and self.thread.is_alive():
            self.stop_event.set()
            self.thread.join(timeout=2.0)
            self.thread = None
            self.logger.debug("Stopped stream I/O thread")

    def _stream_io_loop(self) -> None:
        """
        Background thread loop for stream I/O and keep-alive functionality.

        This method runs continuously while connected and:
        1. Sends periodic status queries to prevent 5-second timeout disconnection
        2. Processes incoming data from the machine
        3. Handles diagnostic queries when enabled
        """
        self._last_status_time = time.time()
        self._last_diagnose_time = time.time()
        line_buffer = b""

        self.logger.debug("Stream I/O loop started")

        while not self.stop_event.is_set():
            if not self.stream or self.paused:
                time.sleep(0.1)
                continue

            current_time = time.time()

            try:
                # Determine if machine is running (sending/loading commands)
                running = (
                    self.send_num > 0
                    or self.load_num > 0
                    or self.pausing
                    or self._running
                )

                # Send keep-alive status queries when not running
                if not running:
                    # Send status query every STREAM_POLL seconds (0.2s)
                    if current_time - self._last_status_time > STREAM_POLL:
                        self._send_status_query()
                        self._last_status_time = current_time

                    # Send diagnostic query if enabled
                    if (
                        self.diagnosing
                        and current_time - self._last_diagnose_time > DIAGNOSE_POLL
                    ):
                        self._send_diagnose_query()
                        self._last_diagnose_time = current_time
                else:
                    # Reset timers when running
                    self._last_status_time = current_time
                    self._last_diagnose_time = current_time

                # Process incoming data
                if self.stream.waiting_for_recv():
                    try:
                        received_data = self.stream.recv()
                        if received_data:
                            line_buffer = self._process_received_data(
                                received_data, line_buffer
                            )
                    except Exception as e:
                        self.logger.debug(f"Error receiving data: {e}")

                # Small delay to prevent excessive CPU usage
                time.sleep(0.01)

            except Exception as e:
                self.logger.error(f"Stream I/O error: {e}")
                time.sleep(0.1)

        self.logger.debug("Stream I/O loop ended")

    def _send_status_query(self) -> None:
        """Send status query to machine for keep-alive."""
        try:
            if self.stream:
                query_data = b"?"
                self.stream.send(query_data)
                self.logger.debug(f"Keep-alive: sent status query {query_data!r}")
        except Exception as e:
            self.logger.warning(f"Keep-alive failed to send status query: {e}")

    def _send_diagnose_query(self) -> None:
        """Send diagnostic query to machine."""
        try:
            if self.stream:
                self.stream.send(b"diagnose\n")
                self.logger.debug("Sent diagnostic query")
        except Exception as e:
            self.logger.debug(f"Failed to send diagnostic query: {e}")

    def _process_received_data(self, data: bytes, line_buffer: bytes) -> bytes:
        """
        Process received data from the machine.

        Args:
            data: Raw bytes received from machine
            line_buffer: Current line buffer

        Returns:
            Updated line buffer
        """
        for byte_val in data:
            byte_char = bytes([byte_val])

            if byte_char in (EOT, CAN):
                # Handle file transfer completion/cancellation
                if line_buffer:
                    try:
                        line_str = line_buffer.decode("utf-8", errors="ignore")
                        self.log.put((MSG_NORMAL, line_str))
                    except Exception as e:
                        self.logger.debug(f"Error decoding line: {e}")
                line_buffer = b""

                if byte_char == EOT:
                    self.load_eof = True
                else:
                    self.load_err = True

            elif byte_char == b"\n":
                # Process complete line
                if line_buffer:
                    try:
                        line_str = line_buffer.decode("utf-8", errors="ignore")
                        self._parse_machine_response(line_str)
                    except Exception as e:
                        self.logger.debug(f"Error processing line: {e}")
                line_buffer = b""

            else:
                # Add to line buffer
                line_buffer += byte_char

        return line_buffer

    def _parse_machine_response(self, line: str) -> None:
        """
        Parse response line from machine.

        Args:
            line: Response line from machine
        """
        line = line.strip()
        if not line:
            return

        self.logger.debug(f"Raw response received: {line!r}")

        # Add to log queue for external processing
        self.log.put((MSG_NORMAL, line))

        # Check if we're waiting for a response
        if self._waiting_for_response:
            self._last_response = line
            self._response_event.set()
            self.logger.debug(f"Response matched waiting command: {line}")

        # Update machine state based on response
        # This is a simplified version - full implementation would parse
        # status reports, position updates, etc.
        if line.startswith("<") and line.endswith(">"):
            # Status report - could parse and update CNC state here
            self.pos_update = True
            self.logger.debug(f"Status report parsed: {line}")
        elif line.startswith("[") and line.endswith("]"):
            # Position or setting report
            self._g_update = True
            self.logger.debug(f"Position/setting report parsed: {line}")
        elif "error" in line.lower() or "alarm" in line.lower():
            # Error or alarm
            self.log.put((MSG_ERROR, line))
            self.logger.error(f"Machine error/alarm received: {line}")
        else:
            self.logger.info(f"Machine response: {line}")

    def set_running_state(self, running: bool) -> None:
        """
        Set the running state to control keep-alive behavior.

        Args:
            running: True if machine is actively running commands
        """
        self._running = running
