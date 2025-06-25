#!/usr/bin/env python3
"""
Test runner for CNC Controller Library.

This script runs all unit tests for the CNC controller library.
"""

import sys
import unittest
import os

# Add parent directory to path to import the CNC library
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def run_tests():
    """Run all tests and return the result."""
    # Discover and run tests
    loader = unittest.TestLoader()
    start_dir = "tests"
    suite = loader.discover(start_dir, pattern="test_*.py")

    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Return True if all tests passed
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
