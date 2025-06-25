"""
Unit tests for CNC utility functions.

These tests verify utility functions for data conversion, file operations,
and other common tasks.
"""

import unittest
import tempfile
import os
from cnc_utils import (
    humansize, humandate, second2hour, md5_file, xfrange, translate,
    digitize_version, safe_float, safe_int, clamp, validate_gcode_line,
    parse_coordinate_string, FileWatcher
)


class TestCNCUtils(unittest.TestCase):
    """Test cases for CNC utility functions."""

    def test_humansize(self):
        """Test human-readable size formatting."""
        self.assertEqual(humansize(0), "0 B")
        self.assertEqual(humansize(1024), "1 KB")
        self.assertEqual(humansize(1536), "1.5 KB")
        self.assertEqual(humansize(1048576), "1 MB")
        self.assertEqual(humansize(1073741824), "1 GB")

    def test_humandate(self):
        """Test human-readable date formatting."""
        # Test with known timestamp
        timestamp = 1609459200  # 2021-01-01 00:00:00 UTC
        result = humandate(timestamp)
        self.assertIn("2021", result)
        self.assertIn("01", result)

    def test_second2hour(self):
        """Test time conversion."""
        self.assertEqual(second2hour(0), "0s")
        self.assertEqual(second2hour(30), "30s")
        self.assertEqual(second2hour(60), "1m0s")
        self.assertEqual(second2hour(90), "1m30s")
        self.assertEqual(second2hour(3600), "1h0m0s")
        self.assertEqual(second2hour(3661), "1h1m1s")

    def test_md5_file(self):
        """Test MD5 file hashing."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("Hello, World!")
            temp_filename = f.name
        
        try:
            # Calculate MD5
            md5_hash = md5_file(temp_filename)
            self.assertEqual(len(md5_hash), 32)  # MD5 is 32 hex characters
            self.assertIsInstance(md5_hash, str)
            
            # Test with non-existent file
            with self.assertRaises(FileNotFoundError):
                md5_file("non_existent_file.txt")
                
        finally:
            os.unlink(temp_filename)

    def test_xfrange(self):
        """Test float range generation."""
        # Test normal range
        result = list(xfrange(0, 10, 5))
        expected = [0.0, 2.5, 5.0, 7.5, 10.0]
        self.assertEqual(len(result), 5)
        for i, val in enumerate(result):
            self.assertAlmostEqual(val, expected[i], places=5)
        
        # Test single step
        result = list(xfrange(0, 10, 1))
        self.assertEqual(len(result), 0)
        
        # Test zero interval
        result = list(xfrange(5, 5, 3))
        self.assertEqual(result, [5, 5, 5])

    def test_translate(self):
        """Test value translation between ranges."""
        # Test basic translation
        result = translate(5, 0, 10, 0, 100)
        self.assertEqual(result, 50)
        
        # Test reverse translation
        result = translate(50, 0, 100, 0, 10)
        self.assertEqual(result, 5)
        
        # Test negative ranges
        result = translate(0, -10, 10, 0, 20)
        self.assertEqual(result, 10)

    def test_digitize_version(self):
        """Test version string digitization."""
        self.assertEqual(digitize_version("1.2.3"), 1002003)
        self.assertEqual(digitize_version("2.0.0"), 2000000)
        self.assertEqual(digitize_version("1.10.5"), 1010005)
        self.assertEqual(digitize_version("1.2"), 1002000)
        self.assertEqual(digitize_version("3"), 3000000)
        self.assertEqual(digitize_version(""), 0)

    def test_safe_float(self):
        """Test safe float conversion."""
        self.assertEqual(safe_float("10.5"), 10.5)
        self.assertEqual(safe_float("invalid", 0.0), 0.0)
        self.assertEqual(safe_float("", 5.0), 5.0)
        self.assertEqual(safe_float(None, 2.5), 2.5)

    def test_safe_int(self):
        """Test safe integer conversion."""
        self.assertEqual(safe_int("10"), 10)
        self.assertEqual(safe_int("invalid", 0), 0)
        self.assertEqual(safe_int("", 5), 5)
        self.assertEqual(safe_int(None, 2), 2)

    def test_clamp(self):
        """Test value clamping."""
        self.assertEqual(clamp(5, 0, 10), 5)
        self.assertEqual(clamp(-5, 0, 10), 0)
        self.assertEqual(clamp(15, 0, 10), 10)
        self.assertEqual(clamp(5.5, 0.0, 10.0), 5.5)

    def test_validate_gcode_line(self):
        """Test G-code line validation."""
        # Valid G-code
        self.assertTrue(validate_gcode_line("G0 X10 Y20"))
        self.assertTrue(validate_gcode_line("G1 X5 Y10 F1000"))
        self.assertTrue(validate_gcode_line("M3 S1000"))
        self.assertTrue(validate_gcode_line("X10"))
        self.assertTrue(validate_gcode_line("F500"))
        self.assertTrue(validate_gcode_line("(Comment)"))
        self.assertTrue(validate_gcode_line("; Comment"))
        self.assertTrue(validate_gcode_line("%"))
        
        # Invalid G-code
        self.assertFalse(validate_gcode_line(""))
        self.assertFalse(validate_gcode_line("   "))
        self.assertFalse(validate_gcode_line("INVALID COMMAND"))

    def test_parse_coordinate_string(self):
        """Test coordinate string parsing."""
        # Test basic coordinates
        coords = parse_coordinate_string("X10.5 Y20.3 Z5.0")
        self.assertEqual(coords['X'], 10.5)
        self.assertEqual(coords['Y'], 20.3)
        self.assertEqual(coords['Z'], 5.0)
        
        # Test negative coordinates
        coords = parse_coordinate_string("X-10 Y-20.5")
        self.assertEqual(coords['X'], -10.0)
        self.assertEqual(coords['Y'], -20.5)
        
        # Test mixed case
        coords = parse_coordinate_string("x5 y10 z15")
        self.assertEqual(coords['X'], 5.0)
        self.assertEqual(coords['Y'], 10.0)
        self.assertEqual(coords['Z'], 15.0)
        
        # Test empty string
        coords = parse_coordinate_string("")
        self.assertEqual(len(coords), 0)
        
        # Test invalid values
        coords = parse_coordinate_string("X Y10")
        self.assertEqual(coords['X'], 0.0)
        self.assertEqual(coords['Y'], 10.0)

    def test_file_watcher(self):
        """Test file watcher functionality."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("Initial content")
            temp_filename = f.name
        
        try:
            # Create watcher
            watcher = FileWatcher(temp_filename)
            
            # Initially should not have changed
            self.assertFalse(watcher.has_changed())
            
            # Modify file
            import time
            time.sleep(0.1)  # Ensure timestamp difference
            with open(temp_filename, 'w') as f:
                f.write("Modified content")
            
            # Should detect change
            self.assertTrue(watcher.has_changed())
            
            # Should not detect change again immediately
            self.assertFalse(watcher.has_changed())
            
        finally:
            os.unlink(temp_filename)

    def test_file_watcher_nonexistent_file(self):
        """Test file watcher with non-existent file."""
        watcher = FileWatcher("non_existent_file.txt")
        self.assertFalse(watcher.has_changed())


class TestUtilityEdgeCases(unittest.TestCase):
    """Test edge cases for utility functions."""

    def test_humansize_edge_cases(self):
        """Test edge cases for humansize function."""
        self.assertEqual(humansize(1023), "1023 B")
        self.assertEqual(humansize(1025), "1 KB")
        
    def test_translate_edge_cases(self):
        """Test edge cases for translate function."""
        # Same input and output ranges
        result = translate(5, 0, 10, 0, 10)
        self.assertEqual(result, 5)
        
        # Zero-width input range (should handle gracefully)
        try:
            result = translate(5, 5, 5, 0, 10)
            # This might raise an exception or return a specific value
        except ZeroDivisionError:
            pass  # This is acceptable behavior

    def test_xfrange_edge_cases(self):
        """Test edge cases for xfrange function."""
        # Zero steps
        result = list(xfrange(0, 10, 0))
        self.assertEqual(len(result), 0)
        
        # Negative steps
        result = list(xfrange(0, 10, -1))
        self.assertEqual(len(result), 0)

    def test_coordinate_parsing_edge_cases(self):
        """Test edge cases for coordinate parsing."""
        # Test with extra spaces
        coords = parse_coordinate_string("  X10   Y20  ")
        self.assertEqual(coords['X'], 10.0)
        self.assertEqual(coords['Y'], 20.0)
        
        # Test with other axes
        coords = parse_coordinate_string("A90 B45 C30")
        self.assertEqual(coords['A'], 90.0)
        self.assertEqual(coords['B'], 45.0)
        self.assertEqual(coords['C'], 30.0)


if __name__ == '__main__':
    unittest.main()
