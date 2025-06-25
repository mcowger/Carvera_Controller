"""
Unit tests for CNC controller functionality.

These tests verify controller operations, command handling, and state management
without requiring actual hardware connections.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import logging
from cnc_controller import Controller, ControllerError, ConnectionError, CommandError
from cnc_controller import CONN_USB, CONN_WIFI
from cnc_core import CNC


class MockStream:
    """Mock stream for testing."""

    def __init__(self):
        self.connected = False
        self.sent_data = []
        self.received_data = b""

    def open(self, address):
        self.connected = True
        return True

    def close(self):
        self.connected = False
        return True

    def send(self, data):
        self.sent_data.append(data)
        return len(data)

    def recv(self):
        return self.received_data

    def waiting_for_recv(self):
        """Mock method for keep-alive thread."""
        return False

    def waiting_for_send(self):
        """Mock method for keep-alive thread."""
        return True

    def is_connected(self):
        return self.connected


class TestCNCController(unittest.TestCase):
    """Test cases for CNC controller functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.cnc = CNC()
        self.controller = Controller(self.cnc)

        # Mock the streams
        self.mock_usb_stream = MockStream()
        self.mock_wifi_stream = MockStream()
        self.controller.usb_stream = self.mock_usb_stream
        self.controller.wifi_stream = self.mock_wifi_stream

    def test_initialization(self):
        """Test controller initialization."""
        self.assertIsInstance(self.controller, Controller)
        self.assertIsInstance(self.controller.cnc, CNC)
        self.assertIsNotNone(self.controller.logger)
        self.assertFalse(self.controller.is_connected())

    def test_wifi_connection(self):
        """Test WiFi connection."""
        # Test successful connection
        result = self.controller.connect("192.168.1.100:2222", CONN_WIFI)
        self.assertTrue(result)
        self.assertTrue(self.controller.is_connected())
        self.assertEqual(self.controller.connection_type, CONN_WIFI)
        self.assertEqual(self.controller.stream, self.mock_wifi_stream)

    def test_usb_connection(self):
        """Test USB connection."""
        # Test successful connection
        result = self.controller.connect("/dev/ttyUSB0", CONN_USB)
        self.assertTrue(result)
        self.assertTrue(self.controller.is_connected())
        self.assertEqual(self.controller.connection_type, CONN_USB)
        self.assertEqual(self.controller.stream, self.mock_usb_stream)

    def test_connection_failure(self):
        """Test connection failure handling."""
        # Mock stream that fails to connect
        failing_stream = Mock()
        failing_stream.open.return_value = False
        self.controller.wifi_stream = failing_stream

        with self.assertRaises(ConnectionError):
            self.controller.connect("192.168.1.100:2222", CONN_WIFI)

    def test_disconnection(self):
        """Test disconnection."""
        # Connect first
        self.controller.connect("192.168.1.100:2222", CONN_WIFI)
        self.assertTrue(self.controller.is_connected())

        # Disconnect
        result = self.controller.disconnect()
        self.assertTrue(result)
        self.assertFalse(self.controller.is_connected())

    def test_send_command(self):
        """Test sending commands."""
        # Connect first
        self.controller.connect("192.168.1.100:2222", CONN_WIFI)

        # Send command
        result = self.controller.send_command("G28")
        self.assertTrue(result)

        # Check that command was sent
        self.assertEqual(len(self.mock_wifi_stream.sent_data), 1)
        self.assertEqual(self.mock_wifi_stream.sent_data[0], b"G28\n")

    def test_send_command_without_connection(self):
        """Test sending command without connection."""
        with self.assertRaises(CommandError):
            self.controller.send_command("G28")

    def test_send_command_adds_newline(self):
        """Test that commands get newline added."""
        self.controller.connect("192.168.1.100:2222", CONN_WIFI)

        # Send command without newline
        self.controller.send_command("G0 X10")
        self.assertEqual(self.mock_wifi_stream.sent_data[0], b"G0 X10\n")

        # Send command with newline
        self.controller.send_command("G0 Y10\n")
        self.assertEqual(self.mock_wifi_stream.sent_data[1], b"G0 Y10\n")

    def test_execute_gcode(self):
        """Test G-code execution."""
        self.controller.connect("192.168.1.100:2222", CONN_WIFI)

        # Valid G-code - disable response waiting for test
        result = self.controller.execute_gcode("G0 X10 Y20", wait_for_ok=False)
        self.assertTrue(result)

        # Valid special commands (these don't wait for responses anyway)
        result = self.controller.execute_gcode("?")
        self.assertTrue(result)

        result = self.controller.execute_gcode("$H")
        self.assertTrue(result)

        # Invalid G-code
        result = self.controller.execute_gcode("INVALID")
        self.assertFalse(result)

    def test_gcode_response_waiting(self):
        """Test GCODE response waiting functionality."""
        self.controller.connect("192.168.1.100:2222", CONN_WIFI)

        # Test GCODE command with response waiting (will timeout in test)
        result = self.controller.execute_gcode("G28", wait_for_ok=True, timeout=0.1)
        self.assertIsNone(result)  # Should timeout since no 'ok' response

        # Test non-GCODE command (should not wait for response)
        result = self.controller.execute_gcode("?", wait_for_ok=True)
        self.assertTrue(result)  # Non-GCODE commands return boolean

        # Test send_command with response waiting
        result = self.controller.send_command(
            "G28", wait_for_response=True, timeout=0.1
        )
        self.assertIsNone(result)  # Should timeout

    def test_command_history(self):
        """Test command history functionality."""
        self.controller.connect("192.168.1.100:2222", CONN_WIFI)

        # Send some commands
        self.controller.send_command("G28")
        self.controller.send_command("G0 X10")
        self.controller.send_command("G0 Y20")

        # Check history
        history = self.controller.get_history()
        self.assertIn("G28", history)
        self.assertIn("G0 X10", history)
        self.assertIn("G0 Y20", history)

        # Clear history
        self.controller.clear_history()
        self.assertEqual(len(self.controller.get_history()), 0)

    def test_machine_control_commands(self):
        """Test various machine control commands."""
        self.controller.connect("192.168.1.100:2222", CONN_WIFI)

        # Test various commands
        self.assertTrue(self.controller.reset())
        self.assertTrue(self.controller.home_machine())
        self.assertTrue(self.controller.get_status())
        self.assertTrue(self.controller.stop_motion())
        self.assertTrue(self.controller.resume_motion())
        self.assertTrue(self.controller.unlock_alarm())

        # Check that commands were sent
        self.assertGreater(len(self.mock_wifi_stream.sent_data), 0)

    def test_jog_commands(self):
        """Test jogging commands."""
        self.controller.connect("192.168.1.100:2222", CONN_WIFI)

        # Test single axis jog
        result = self.controller.jog(x=10)
        self.assertTrue(result)

        # Test multi-axis jog
        result = self.controller.jog(x=5, y=10, z=2)
        self.assertTrue(result)

        # Test jog with speed
        result = self.controller.jog(x=1, speed=50)
        self.assertTrue(result)

        # Test empty jog (should return False)
        result = self.controller.jog()
        self.assertFalse(result)

    def test_scale_commands(self):
        """Test scale setting commands."""
        self.controller.connect("192.168.1.100:2222", CONN_WIFI)

        # Test feed scale
        result = self.controller.set_feed_scale(150)
        self.assertTrue(result)

        # Test spindle scale
        result = self.controller.set_spindle_scale(80)
        self.assertTrue(result)

        # Test laser scale
        result = self.controller.set_laser_scale(50)
        self.assertTrue(result)

    def test_position_commands(self):
        """Test position-related commands."""
        self.controller.connect("192.168.1.100:2222", CONN_WIFI)

        # Test goto position commands
        result = self.controller.goto_position("Clearance")
        self.assertTrue(result)

        result = self.controller.goto_position("Work Origin")
        self.assertTrue(result)

        result = self.controller.goto_position("Anchor1")
        self.assertTrue(result)

        # Test invalid position
        result = self.controller.goto_position("Invalid Position")
        self.assertFalse(result)

    def test_probing_commands(self):
        """Test probing commands."""
        self.controller.connect("192.168.1.100:2222", CONN_WIFI)

        # Set up margins for auto command
        self.controller.cnc["xmin"] = 0
        self.controller.cnc["ymin"] = 0
        self.controller.cnc["xmax"] = 100
        self.controller.cnc["ymax"] = 100
        self.controller.cnc["worksize_x"] = 200
        self.controller.cnc["worksize_y"] = 200

        # Test auto command
        result = self.controller.auto_command(margin=True, zprobe=True)
        self.assertTrue(result)

        # Test XYZ probe
        result = self.controller.xyz_probe(height=10, diameter=3)
        self.assertTrue(result)

    def test_utility_commands(self):
        """Test utility commands."""
        self.controller.connect("192.168.1.100:2222", CONN_WIFI)

        # Test time sync
        result = self.controller.sync_time()
        self.assertTrue(result)

        # Test queries
        result = self.controller.query_version()
        self.assertTrue(result)

        result = self.controller.query_model()
        self.assertTrue(result)

        result = self.controller.pair_wp()
        self.assertTrue(result)

    def test_log_messages(self):
        """Test log message handling."""
        # Add some messages to the log queue
        self.controller.log.put(("INFO", "Test message 1"))
        self.controller.log.put(("ERROR", "Test message 2"))

        # Get messages
        messages = self.controller.get_log_messages()
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0], ("INFO", "Test message 1"))
        self.assertEqual(messages[1], ("ERROR", "Test message 2"))

        # Queue should be empty now
        messages = self.controller.get_log_messages()
        self.assertEqual(len(messages), 0)

    def test_spindle_control(self):
        """Test spindle control."""
        self.controller.connect("192.168.1.100:2222", CONN_WIFI)

        # Turn on spindle
        result = self.controller.set_spindle_switch(True, 1000)
        self.assertTrue(result)

        # Turn off spindle
        result = self.controller.set_spindle_switch(False)
        self.assertTrue(result)

    def test_keep_alive_functionality(self):
        """Test keep-alive thread functionality."""
        # Connect to start keep-alive thread
        self.controller.connect("192.168.1.100:2222", CONN_WIFI)

        # Check that thread is started
        self.assertIsNotNone(self.controller.thread)
        self.assertTrue(self.controller.thread.is_alive())

        # Test running state control
        self.controller.set_running_state(True)
        self.assertTrue(self.controller._running)

        self.controller.set_running_state(False)
        self.assertFalse(self.controller._running)

        # Disconnect should stop thread
        self.controller.disconnect()

        # Give thread time to stop
        import time

        time.sleep(0.1)

        # Thread should be stopped
        self.assertFalse(self.controller.is_connected())

    def test_stream_thread_management(self):
        """Test stream thread start/stop functionality."""
        # Initially no thread
        self.assertIsNone(self.controller.thread)

        # Connect starts thread
        self.controller.connect("192.168.1.100:2222", CONN_WIFI)
        self.assertIsNotNone(self.controller.thread)

        # Disconnect stops thread
        self.controller.disconnect()

        # Give thread time to stop
        import time

        time.sleep(0.1)

        # Thread should be cleaned up
        self.assertTrue(
            self.controller.thread is None or not self.controller.thread.is_alive()
        )


class TestControllerWithoutMocks(unittest.TestCase):
    """Test controller functionality without mocking streams."""

    def test_controller_creation_without_cnc(self):
        """Test creating controller without providing CNC instance."""
        controller = Controller()
        self.assertIsInstance(controller.cnc, CNC)

    def test_controller_with_custom_logger(self):
        """Test creating controller with custom logger."""
        logger = logging.getLogger("test_logger")
        controller = Controller(logger=logger)
        self.assertEqual(controller.logger, logger)

    def test_connection_without_streams(self):
        """Test connection behavior with real stream objects."""
        controller = Controller()

        # This should fail since we don't have real hardware
        with self.assertRaises(ConnectionError):
            controller.connect("invalid_address", CONN_WIFI)


if __name__ == "__main__":
    unittest.main()
