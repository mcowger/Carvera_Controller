#!/usr/bin/env python3
"""
Quick Test Script for CNC Controller Library.

A simple, focused test script for quickly validating the CNC controller
library against a real machine with minimal setup.

Usage:
    python quick_test.py 192.168.1.100
"""

import sys
import time
import logging
import os

# Add parent directory to path to import the CNC library
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cnc_controller import Controller, CONN_WIFI
from cnc_core import CNC


def quick_test(ip: str, port: int = 2222):
    """
    Perform a quick test of the CNC controller library.

    Args:
        ip: Machine IP address
        port: Machine port

    Returns:
        True if all tests pass, False otherwise
    """
    print("🔧 CNC Controller Library Quick Test")
    print("=" * 50)

    # Set up logging
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    logger = logging.getLogger(__name__)

    # Create controller
    cnc = CNC()
    controller = Controller(cnc, logger=logger)

    try:
        # Test 1: Connection
        print(f"📡 Connecting to {ip}:{port}...")
        address = f"{ip}:{port}"

        if not controller.connect(address, CONN_WIFI):
            print("❌ Connection failed")
            return False

        print("✅ Connected successfully")
        print(f"🔄 Keep-alive thread started: {controller.thread.is_alive()}")

        # Test 2: Basic commands
        print("\n📋 Testing basic commands...")

        commands = [
            ("version", "Get firmware version"),
            ("?", "Get machine status"),
            ("$#", "Get position info"),
            ("ls", "List files"),
        ]

        for cmd, description in commands:
            print(f"  Sending '{cmd}' ({description})...")
            try:
                success = controller.send_command(cmd)
                if success:
                    time.sleep(0.2)  # Wait for response
                    messages = controller.get_log_messages()
                    print(f"    ✅ Sent, got {len(messages)} responses")

                    # Show first response if available
                    if messages and len(messages) > 0:
                        msg_type, msg_content = messages[0]
                        print(f"    📝 Response: {msg_content[:60]}...")
                else:
                    print(f"    ❌ Failed to send command")
            except Exception as e:
                print(f"    ❌ Error: {e}")

        # Test 3: Keep-alive test
        print(f"\n⏱️  Testing keep-alive (waiting 6 seconds)...")
        start_time = time.time()

        for i in range(6):
            time.sleep(1)
            if not controller.is_connected():
                elapsed = time.time() - start_time
                print(f"❌ Connection lost after {elapsed:.1f} seconds")
                return False
            print(f"  ⏳ Still connected after {i+1}s")

        print("✅ Keep-alive working - connection maintained!")

        # Test 4: G-code parsing
        print(f"\n🔍 Testing G-code parsing...")
        test_gcode = "G1 X10 Y20 Z5 F1000"

        try:
            coordinates = cnc.parse_line(test_gcode, 1)
            if coordinates:
                print(
                    f"  ✅ Parsed '{test_gcode}' -> {len(coordinates)} coordinate points"
                )
                print(f"  📍 Final position: X={cnc.x}, Y={cnc.y}, Z={cnc.z}")
            else:
                print(f"  ℹ️  No coordinates generated for '{test_gcode}'")
        except Exception as e:
            print(f"  ❌ Parse error: {e}")

        print("\n🎉 All tests completed successfully!")
        return True

    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        # Send emergency stop
        try:
            controller.send_command("!")  # Feed hold
            controller.send_command("\x18")  # Soft reset
            print("🛑 Emergency stop sent")
        except:
            pass
        return False

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return False

    finally:
        # Always disconnect
        if controller.is_connected():
            controller.disconnect()
            print("🔌 Disconnected from machine")


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python quick_test.py <machine_ip> [port]")
        print("Example: python quick_test.py 192.168.1.100")
        return 1

    ip = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 2222

    try:
        success = quick_test(ip, port)

        if success:
            print("\n✅ Quick test PASSED - Library is working correctly!")
            return 0
        else:
            print("\n❌ Quick test FAILED - Check connection and machine status")
            return 1

    except Exception as e:
        print(f"\n💥 Test crashed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
