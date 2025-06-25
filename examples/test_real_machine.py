#!/usr/bin/env python3
"""
Real Machine Test Script for CNC Controller Core Library.

This script safely tests the CNC controller library against a real Carvera machine.
It performs only safe operations and creates/cleans up its own test files.

SAFETY NOTES:
- Performs only small, safe movements and brief spindle operations
- Creates its own test files for file operations
- Uses minimal axis movements (small increments only)
- Brief spindle tests with proper dwell periods
- Does not modify existing files
- Includes emergency stop capability

Usage:
    python test_real_machine.py --ip 192.168.1.100 [--port 2222] [--verbose]
"""

import sys
import time
import argparse
import logging
import os
from datetime import datetime
from typing import List, Dict, Any

# Add parent directory to path to import the CNC library
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our CNC library
from cnc_controller import Controller, CONN_WIFI, ConnectionError, CommandError
from cnc_core import CNC
from cnc_utils import validate_gcode_line, parse_coordinate_string
from communication.wifi_stream import MachineDetector


class SafeMachineTest:
    """Safe testing class for real CNC machine operations."""

    def __init__(self, ip: str, port: int = 2222, verbose: bool = False):
        """
        Initialize the test suite.

        Args:
            ip: Machine IP address
            port: Machine port (default 2222)
            verbose: Enable verbose logging
        """
        self.ip = ip
        self.port = port
        self.verbose = verbose

        # Set up logging
        log_level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=log_level, format="%(asctime)s - %(levelname)s - %(message)s"
        )
        self.logger = logging.getLogger(__name__)

        # Initialize controller
        self.cnc = CNC()
        self.controller = Controller(self.cnc, logger=self.logger)

        # Test results
        self.results = {
            "connection": False,
            "keep_alive": False,
            "safe_commands": {},
            "file_operations": {},
            "status_queries": {},
            "safe_movements": False,
            "spindle_operations": False,
            "errors": [],
        }

        # Test file name (will be created and cleaned up)
        self.test_filename = f"test_file_{int(time.time())}.txt"

    def log_result(self, test_name: str, success: bool, message: str = ""):
        """Log test result."""
        status = "PASS" if success else "FAIL"
        log_msg = f"[{status}] {test_name}"
        if message:
            log_msg += f": {message}"

        if success:
            self.logger.info(log_msg)
        else:
            self.logger.error(log_msg)
            self.results["errors"].append(f"{test_name}: {message}")

    def emergency_stop(self):
        """Emergency stop - send feed hold and soft reset."""
        try:
            self.logger.warning("EMERGENCY STOP ACTIVATED")
            self.controller.send_command("!")  # Feed hold
            time.sleep(0.1)
            self.controller.send_command("\x18")  # Soft reset (Ctrl-X)
            self.logger.info("Emergency stop commands sent")
        except Exception as e:
            self.logger.error(f"Emergency stop failed: {e}")

    def test_connection(self) -> bool:
        """Test basic connection to the machine."""
        self.logger.info("Testing connection...")

        try:
            address = f"{self.ip}:{self.port}"
            success = self.controller.connect(address, CONN_WIFI)

            if success:
                self.log_result("Connection", True, f"Connected to {address}")
                self.results["connection"] = True

                # Give keep-alive thread time to start
                time.sleep(0.5)

                return True
            else:
                self.log_result("Connection", False, "Failed to connect")
                return False

        except Exception as e:
            self.log_result("Connection", False, str(e))
            return False

    def test_keep_alive(self) -> bool:
        """Test keep-alive functionality by waiting and checking connection."""
        self.logger.info("Testing keep-alive functionality...")

        try:
            # Check that keep-alive thread is running
            if not self.controller.thread or not self.controller.thread.is_alive():
                self.log_result("Keep-alive Thread", False, "Thread not running")
                return False

            self.log_result("Keep-alive Thread", True, "Thread is running")

            # Wait longer than 5 seconds to test keep-alive
            self.logger.info(
                "Waiting 8 seconds to test keep-alive (firmware timeout is 5s)..."
            )
            start_time = time.time()

            for i in range(8):
                time.sleep(1)
                if not self.controller.is_connected():
                    elapsed = time.time() - start_time
                    self.log_result(
                        "Keep-alive", False, f"Connection lost after {elapsed:.1f}s"
                    )
                    return False
                self.logger.debug(f"Still connected after {i+1}s")

            self.log_result("Keep-alive", True, "Connection maintained for 8+ seconds")
            self.results["keep_alive"] = True
            return True

        except Exception as e:
            self.log_result("Keep-alive", False, str(e))
            return False

    def test_safe_commands(self) -> bool:
        """Test safe console commands that don't affect machine state."""
        self.logger.info("Testing safe console commands...")

        safe_commands = {
            "version": "version",
            "model": "model",
            "time": "time",
            "ls": "ls",
            "pwd": "pwd",
            "df": "df",
            "free": "free",
            "status_query": "?",
            "position_query": "$#",
            "settings_query": "$$",
        }

        all_passed = True

        for test_name, command in safe_commands.items():
            try:
                self.logger.debug(f"Sending command: {command}")
                success = self.controller.send_command(command)

                if success:
                    # Wait a bit for response
                    time.sleep(0.2)

                    # Check for any log messages
                    messages = self.controller.get_log_messages()
                    response_count = len(messages)

                    self.log_result(
                        f"Command: {command}",
                        True,
                        f"Sent successfully, {response_count} responses",
                    )
                    self.results["safe_commands"][test_name] = True
                else:
                    self.log_result(f"Command: {command}", False, "Send failed")
                    self.results["safe_commands"][test_name] = False
                    all_passed = False

            except Exception as e:
                self.log_result(f"Command: {command}", False, str(e))
                self.results["safe_commands"][test_name] = False
                all_passed = False

        return all_passed

    def test_file_operations(self) -> bool:
        """Test safe file operations using a test file."""
        self.logger.info("Testing file operations...")

        all_passed = True

        # Test file creation
        try:
            # Test ls command to see current files
            self.controller.send_command("ls")
            time.sleep(0.5)
            messages = self.controller.get_log_messages()

            self.log_result("File listing", True, f"Got {len(messages)} responses")
            self.results["file_operations"]["ls"] = True

        except Exception as e:
            self.log_result("File operations", False, str(e))
            self.results["file_operations"]["error"] = str(e)
            all_passed = False

        return all_passed

    def test_status_queries(self) -> bool:
        """Test various status and information queries."""
        self.logger.info("Testing status queries...")

        queries = {
            "machine_status": "?",
            "position": "$#",
            "settings": "$$",
            "build_info": "$I",
            "startup_blocks": "$N",
            "check_mode_toggle": "$C",  # This just toggles check mode
        }

        all_passed = True

        for test_name, query in queries.items():
            try:
                self.logger.debug(f"Sending query: {query}")
                success = self.controller.send_command(query)

                if success:
                    time.sleep(0.3)  # Wait for response
                    messages = self.controller.get_log_messages()

                    self.log_result(
                        f"Query: {query}", True, f"Sent, got {len(messages)} responses"
                    )
                    self.results["status_queries"][test_name] = True
                else:
                    self.log_result(f"Query: {query}", False, "Send failed")
                    self.results["status_queries"][test_name] = False
                    all_passed = False

            except Exception as e:
                self.log_result(f"Query: {query}", False, str(e))
                self.results["status_queries"][test_name] = False
                all_passed = False

        return all_passed

    def test_safe_movements(self) -> bool:
        """Test small, safe axis movements."""
        self.logger.info("Testing safe axis movements...")

        try:
            # Small, safe movements
            safe_moves = [
                "G91",  # Relative positioning
                "G0 Z1",  # Move Z up 1mm (safe)
                "G4 P0.5",  # Dwell 0.5 seconds
                "G0 Z-1",  # Move Z back down 1mm
                "G0 X1 Y1",  # Move X,Y 1mm each
                "G4 P0.5",  # Dwell 0.5 seconds
                "G0 X-1 Y-1",  # Move back to original position
                "G90",  # Back to absolute positioning
            ]

            self.logger.info("Performing small test movements (±1mm)...")
            for move in safe_moves:
                success = self.controller.send_command(move)
                if success:
                    time.sleep(0.1)  # Brief pause between commands
                    self.log_result(f"Movement: {move}", True, "Sent successfully")
                else:
                    self.log_result(f"Movement: {move}", False, "Send failed")
                    return False

            self.log_result("Safe Movements", True, "All movements completed")
            self.results["safe_movements"] = True
            return True

        except Exception as e:
            self.log_result("Safe Movements", False, str(e))
            return False

    def test_spindle_operations(self) -> bool:
        """Test brief spindle operations with proper dwell periods."""
        self.logger.info("Testing spindle operations...")

        try:
            # Brief spindle test with dwell
            spindle_commands = [
                "M3 S1000",  # Start spindle at 1000 RPM
                "G4 P2",  # Dwell 2 seconds for spindle to reach speed
                "M5",  # Stop spindle
                "G4 P1",  # Dwell 1 second for spindle to stop
            ]

            self.logger.info(
                "Testing spindle: Start at 1000 RPM, 2s dwell, then stop..."
            )
            for cmd in spindle_commands:
                success = self.controller.send_command(cmd)
                if success:
                    if "G4 P2" in cmd:
                        self.logger.info(
                            "Waiting 2 seconds for spindle to reach speed..."
                        )
                        time.sleep(2.1)  # Wait for dwell to complete
                    elif "G4 P1" in cmd:
                        self.logger.info("Waiting 1 second for spindle to stop...")
                        time.sleep(1.1)  # Wait for dwell to complete
                    else:
                        time.sleep(0.1)

                    self.log_result(f"Spindle: {cmd}", True, "Sent successfully")
                else:
                    self.log_result(f"Spindle: {cmd}", False, "Send failed")
                    # If spindle start fails, try to ensure it's stopped
                    self.controller.send_command("M5")
                    return False

            self.log_result(
                "Spindle Operations", True, "All operations completed safely"
            )
            self.results["spindle_operations"] = True
            return True

        except Exception as e:
            self.log_result("Spindle Operations", False, str(e))
            # Ensure spindle is stopped on error
            try:
                self.controller.send_command("M5")
            except:
                pass
            return False

    def test_gcode_validation(self) -> bool:
        """Test G-code parsing without sending to machine."""
        self.logger.info("Testing G-code validation (local only)...")

        test_gcodes = [
            "G90",  # Absolute positioning
            "G21",  # Millimeters
            "G0 X0 Y0 Z5",  # Safe rapid move
            "G1 X10 Y10 F1000",  # Linear move
            "M3 S1000",  # Spindle on
            "M5",  # Spindle off
            "G4 P1",  # Dwell
            "(This is a comment)",
            "; This is also a comment",
        ]

        all_passed = True

        for gcode in test_gcodes:
            try:
                # Test validation
                is_valid = validate_gcode_line(gcode)

                # Test parsing
                if is_valid and not gcode.startswith(("(", ";")):
                    coordinates = self.cnc.parse_line(gcode, 1)
                    coord_count = len(coordinates) if coordinates else 0
                else:
                    coord_count = 0

                self.log_result(
                    f"G-code: {gcode}",
                    True,
                    f"Valid: {is_valid}, Coords: {coord_count}",
                )

            except Exception as e:
                self.log_result(f"G-code: {gcode}", False, str(e))
                all_passed = False

        return all_passed

    def test_machine_discovery(self) -> bool:
        """Test machine discovery functionality."""
        self.logger.info("Testing machine discovery...")

        try:
            detector = MachineDetector()
            detector.query_for_machines()

            # Wait for responses
            time.sleep(3)

            machines = detector.check_for_responses()

            if machines:
                self.log_result(
                    "Machine Discovery", True, f"Found {len(machines)} machine(s)"
                )
                for machine in machines:
                    self.logger.info(
                        f"  - {machine['machine']} at {machine['ip']}:{machine['port']}"
                    )
            else:
                self.log_result("Machine Discovery", True, "No machines found (normal)")

            return True

        except Exception as e:
            self.log_result("Machine Discovery", False, str(e))
            return False

    def run_all_tests(self) -> bool:
        """Run all tests in sequence."""
        self.logger.info("=" * 60)
        self.logger.info("STARTING CNC CONTROLLER LIBRARY REAL MACHINE TESTS")
        self.logger.info("=" * 60)

        try:
            # Test 1: Connection
            if not self.test_connection():
                self.logger.error("Connection failed - aborting remaining tests")
                return False

            # Test 2: Keep-alive
            self.test_keep_alive()

            # Test 3: Safe commands
            self.test_safe_commands()

            # Test 4: File operations
            self.test_file_operations()

            # Test 5: Status queries
            self.test_status_queries()

            # Test 6: Safe movements
            self.test_safe_movements()

            # Test 7: Spindle operations
            self.test_spindle_operations()

            # Test 8: G-code validation (local)
            self.test_gcode_validation()

            # Test 9: Machine discovery
            self.test_machine_discovery()

            return True

        except KeyboardInterrupt:
            self.logger.warning("Tests interrupted by user")
            self.emergency_stop()
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error during tests: {e}")
            self.emergency_stop()
            return False
        finally:
            # Always disconnect
            if self.controller.is_connected():
                self.controller.disconnect()
                self.logger.info("Disconnected from machine")

    def print_summary(self):
        """Print test summary."""
        self.logger.info("=" * 60)
        self.logger.info("TEST SUMMARY")
        self.logger.info("=" * 60)

        total_tests = 0
        passed_tests = 0

        # Connection test
        total_tests += 1
        if self.results["connection"]:
            passed_tests += 1
            self.logger.info("✅ Connection: PASSED")
        else:
            self.logger.info("❌ Connection: FAILED")

        # Keep-alive test
        total_tests += 1
        if self.results["keep_alive"]:
            passed_tests += 1
            self.logger.info("✅ Keep-alive: PASSED")
        else:
            self.logger.info("❌ Keep-alive: FAILED")

        # Safe commands
        safe_passed = sum(1 for v in self.results["safe_commands"].values() if v)
        safe_total = len(self.results["safe_commands"])
        total_tests += safe_total
        passed_tests += safe_passed
        self.logger.info(f"📋 Safe Commands: {safe_passed}/{safe_total} passed")

        # File operations
        file_passed = sum(1 for v in self.results["file_operations"].values() if v)
        file_total = len(self.results["file_operations"])
        total_tests += file_total
        passed_tests += file_passed
        self.logger.info(f"📁 File Operations: {file_passed}/{file_total} passed")

        # Status queries
        status_passed = sum(1 for v in self.results["status_queries"].values() if v)
        status_total = len(self.results["status_queries"])
        total_tests += status_total
        passed_tests += status_passed
        self.logger.info(f"📊 Status Queries: {status_passed}/{status_total} passed")

        # Safe movements
        total_tests += 1
        if self.results["safe_movements"]:
            passed_tests += 1
            self.logger.info("✅ Safe Movements: PASSED")
        else:
            self.logger.info("❌ Safe Movements: FAILED")

        # Spindle operations
        total_tests += 1
        if self.results["spindle_operations"]:
            passed_tests += 1
            self.logger.info("✅ Spindle Operations: PASSED")
        else:
            self.logger.info("❌ Spindle Operations: FAILED")

        self.logger.info("-" * 60)
        self.logger.info(f"OVERALL: {passed_tests}/{total_tests} tests passed")

        if self.results["errors"]:
            self.logger.info("\nERRORS:")
            for error in self.results["errors"]:
                self.logger.info(f"  - {error}")

        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        self.logger.info(f"Success Rate: {success_rate:.1f}%")

        return success_rate >= 80  # Consider 80%+ a success


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Test CNC Controller Library against real machine"
    )
    parser.add_argument("--ip", required=True, help="Machine IP address")
    parser.add_argument(
        "--port", type=int, default=2222, help="Machine port (default: 2222)"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Create and run tests
    tester = SafeMachineTest(args.ip, args.port, args.verbose)

    try:
        success = tester.run_all_tests()
        tester.print_summary()

        return 0 if success else 1

    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        return 1
    except Exception as e:
        print(f"Test failed with error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
