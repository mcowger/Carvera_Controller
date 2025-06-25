"""
Unit tests for CNC core functionality.

These tests verify G-code parsing, coordinate calculation, and state management
without requiring actual hardware connections.
"""

import unittest
import math
from cnc_core import CNC, CNCError, GCodeParseError


class TestCNCCore(unittest.TestCase):
    """Test cases for CNC core functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.cnc = CNC()

    def test_initialization(self):
        """Test CNC initialization."""
        self.assertIsInstance(self.cnc, CNC)
        self.assertEqual(self.cnc.x, 0)
        self.assertEqual(self.cnc.y, 0)
        self.assertEqual(self.cnc.z, 0)
        self.assertEqual(self.cnc.a, 0)
        self.assertTrue(self.cnc.absolute)
        self.assertFalse(self.cnc.arcabsolute)

    def test_variable_access(self):
        """Test CNC variable access."""
        # Test getting variables
        self.assertEqual(self.cnc["wx"], 0.0)
        self.assertEqual(self.cnc["wy"], 0.0)

        # Test setting variables
        self.cnc["wx"] = 10.5
        self.cnc["wy"] = 20.3
        self.assertEqual(self.cnc["wx"], 10.5)
        self.assertEqual(self.cnc["wy"], 20.3)

    def test_parse_empty_line(self):
        """Test parsing empty lines and comments."""
        # Empty line
        result = self.cnc.parse_line("", 1)
        self.assertIsNone(result)

        # Comment lines
        result = self.cnc.parse_line("(This is a comment)", 1)
        self.assertIsNone(result)

        result = self.cnc.parse_line("; This is also a comment", 1)
        self.assertIsNone(result)

        result = self.cnc.parse_line("% Program start", 1)
        self.assertIsNone(result)

    def test_parse_linear_move(self):
        """Test parsing linear movement commands."""
        # G0 rapid move
        result = self.cnc.parse_line("G0 X10 Y20 Z5", 1)
        self.assertIsNotNone(result)
        self.assertEqual(self.cnc.x, 10)
        self.assertEqual(self.cnc.y, 20)
        self.assertEqual(self.cnc.z, 5)

        # G1 linear move with feed rate
        result = self.cnc.parse_line("G1 X15 Y25 F1000", 2)
        self.assertIsNotNone(result)
        self.assertEqual(self.cnc.x, 15)
        self.assertEqual(self.cnc.y, 25)
        self.assertEqual(self.cnc.feed, 1000)

    def test_parse_arc_move(self):
        """Test parsing arc movement commands."""
        # Set initial position
        self.cnc.parse_line("G0 X0 Y0", 1)

        # G2 clockwise arc
        result = self.cnc.parse_line("G2 X10 Y0 I5 J0", 2)
        self.assertIsNotNone(result)
        self.assertEqual(self.cnc.x, 10)
        self.assertEqual(self.cnc.y, 0)

    def test_parse_coordinate_systems(self):
        """Test parsing coordinate system commands."""
        # G90 absolute positioning
        self.cnc.parse_line("G90", 1)
        self.assertTrue(self.cnc.absolute)

        # G91 relative positioning
        self.cnc.parse_line("G91", 2)
        self.assertFalse(self.cnc.absolute)

        # Test relative movement
        self.cnc.parse_line("G0 X0 Y0", 3)  # Set position
        self.cnc.parse_line("G91", 4)  # Relative mode
        self.cnc.parse_line("G0 X5 Y10", 5)  # Relative move
        self.assertEqual(self.cnc.x, 5)
        self.assertEqual(self.cnc.y, 10)

    def test_parse_units(self):
        """Test parsing unit commands."""
        # G20 inches
        self.cnc.parse_line("G20", 1)
        # G21 millimeters
        self.cnc.parse_line("G21", 2)

    def test_parse_plane_selection(self):
        """Test parsing plane selection commands."""
        # G17 XY plane
        self.cnc.parse_line("G17", 1)
        self.assertEqual(self.cnc.plane, 0)  # XY

        # G18 XZ plane
        self.cnc.parse_line("G18", 2)
        self.assertEqual(self.cnc.plane, 1)  # XZ

        # G19 YZ plane
        self.cnc.parse_line("G19", 3)
        self.assertEqual(self.cnc.plane, 2)  # YZ

    def test_parse_spindle_commands(self):
        """Test parsing spindle and feed commands."""
        # Spindle speed
        self.cnc.parse_line("S1000", 1)
        self.assertEqual(self.cnc.speed, 1000)

        # Feed rate
        self.cnc.parse_line("F500", 2)
        self.assertEqual(self.cnc.feed, 500)

    def test_parse_tool_commands(self):
        """Test parsing tool commands."""
        # Tool selection
        self.cnc.parse_line("T1", 1)
        self.assertEqual(self.cnc.tool, 1)

        # M321 laser tool
        self.cnc.parse_line("M321", 2)
        self.assertEqual(self.cnc.tool, 7)

    def test_parse_4th_axis(self):
        """Test parsing 4th axis (A) commands."""
        # A axis movement
        self.cnc.parse_line("G0 A90", 1)
        self.assertTrue(self.cnc.has_4axis)
        self.assertEqual(self.cnc.a, -90)  # Right-hand rule

    def test_margins_calculation(self):
        """Test bounding box margin calculations."""
        self.cnc.reset_margins()

        # Move to various positions
        self.cnc.parse_line("G0 X-10 Y-5", 1)
        self.cnc.parse_line("G1 X20 Y15 Z10", 2)
        self.cnc.parse_line("G1 X5 Y25 Z-5", 3)

        # Check margins (allow for small interpolation differences)
        margins = self.cnc.get_margins()
        self.assertAlmostEqual(margins[0], -10, places=0)  # xmin
        self.assertAlmostEqual(margins[1], -5, places=0)  # ymin
        self.assertAlmostEqual(margins[2], -5, places=0)  # zmin
        self.assertAlmostEqual(margins[3], 20, places=0)  # xmax
        self.assertAlmostEqual(margins[4], 25, places=0)  # ymax
        self.assertAlmostEqual(margins[5], 10, places=0)  # zmax

    def test_dwell_command(self):
        """Test dwell command parsing."""
        result = self.cnc.parse_line("G4 P2.5", 1)
        self.assertEqual(self.cnc.pval, 2.5)

    def test_invalid_gcode(self):
        """Test handling of invalid G-code."""
        # This should not raise an exception but may log warnings
        result = self.cnc.parse_line("INVALID COMMAND", 1)
        # Should return None or empty list for invalid commands
        self.assertTrue(result is None or result == [])

    def test_coordinate_tracking(self):
        """Test coordinate tracking during parsing."""
        # Clear coordinates
        self.cnc.coordinates = []

        # Parse some movements
        self.cnc.parse_line("G0 X0 Y0 Z0", 1)
        self.cnc.parse_line("G1 X10 Y10 Z5 F1000", 2)

        # Check that coordinates were recorded
        self.assertGreater(len(self.cnc.coordinates), 0)

        # Each coordinate should have [x, y, z, a, color, line_no, tool]
        for coord in self.cnc.coordinates:
            self.assertEqual(len(coord), 7)

    def test_motion_interpolation(self):
        """Test motion interpolation for long moves."""
        # Set initial position
        self.cnc.parse_line("G0 X0 Y0", 1)

        # Make a long move that should be interpolated
        result = self.cnc.parse_line("G1 X100 Y100", 2)

        # Should have multiple interpolated points
        if result:
            self.assertGreater(len(result), 1)


class TestCNCUtilityMethods(unittest.TestCase):
    """Test utility methods of CNC class."""

    def setUp(self):
        """Set up test fixtures."""
        self.cnc = CNC()

    def test_reset_margins(self):
        """Test margin reset functionality."""
        # Set some margins
        CNC.vars["xmin"] = -10
        CNC.vars["xmax"] = 10

        # Reset margins
        self.cnc.reset_margins()

        # Check they're reset to initial values
        self.assertEqual(CNC.vars["xmin"], 1000000.0)
        self.assertEqual(CNC.vars["xmax"], -1000000.0)

    def test_init_path(self):
        """Test path initialization."""
        # Initialize with specific values
        self.cnc.init_path(x=10, y=20, z=5, a=45)

        self.assertEqual(self.cnc.x, 10)
        self.assertEqual(self.cnc.y, 20)
        self.assertEqual(self.cnc.z, 5)
        self.assertEqual(self.cnc.a, 45)

        # Initialize with defaults
        self.cnc.init_path()

        self.assertEqual(self.cnc.x, 0)
        self.assertEqual(self.cnc.y, 0)
        self.assertEqual(self.cnc.z, 0)
        self.assertEqual(self.cnc.a, 0)


if __name__ == "__main__":
    unittest.main()
