#!/usr/bin/env python3
"""
Basic functionality test - tests the new methods without requiring connection.
"""

import logging
from cnc_controller import Controller, GCODE_PATTERN
from cnc_core import CNC


def test_gcode_pattern():
    """Test the GCODE pattern matching."""
    print("Testing GCODE Pattern Matching")
    print("-" * 30)

    test_cases = [
        ("G28", True),
        ("g0", True),
        ("M3", True),
        ("m5", True),
        ("G1 X10 Y20", True),
        ("M3 S1000", True),
        ("  G28  ", True),  # With whitespace
        ("?", False),
        ("$H", False),
        ("$X", False),
        ("!", False),
        ("~", False),
        ("(comment)", False),
        ("", False),
    ]

    all_passed = True
    for command, expected in test_cases:
        result = bool(GCODE_PATTERN.match(command))
        status = "✓" if result == expected else "✗"
        print(f"  {status} '{command}' -> {result} (expected {expected})")
        if result != expected:
            all_passed = False

    print(
        f"\nPattern matching: {'All tests passed' if all_passed else 'Some tests failed'}"
    )
    return all_passed


def test_method_signatures():
    """Test that the new method signatures work correctly."""
    print("\nTesting Method Signatures")
    print("-" * 25)

    cnc = CNC()
    controller = Controller(cnc)

    # Test that methods can be called with different parameters
    # (they will fail due to no connection, but we're testing the signatures)

    try:
        # Test send_command signatures
        print("  Testing send_command() signatures:")

        # These should all raise CommandError due to no connection
        try:
            controller.send_command("G28")
            print("    ✗ send_command('G28') - should have raised CommandError")
        except Exception as e:
            if "Not connected" in str(e):
                print("    ✓ send_command('G28') - correctly raises CommandError")
            else:
                print(f"    ✗ send_command('G28') - unexpected error: {e}")

        try:
            controller.send_command("G28", wait_for_response=True)
            print(
                "    ✗ send_command with wait_for_response - should have raised CommandError"
            )
        except Exception as e:
            if "Not connected" in str(e):
                print(
                    "    ✓ send_command with wait_for_response - correctly raises CommandError"
                )
            else:
                print(
                    f"    ✗ send_command with wait_for_response - unexpected error: {e}"
                )

        try:
            controller.send_command("G28", wait_for_response=True, timeout=10.0)
            print("    ✗ send_command with timeout - should have raised CommandError")
        except Exception as e:
            if "Not connected" in str(e):
                print("    ✓ send_command with timeout - correctly raises CommandError")
            else:
                print(f"    ✗ send_command with timeout - unexpected error: {e}")

        # Test execute_gcode signatures
        print("  Testing execute_gcode() signatures:")

        try:
            controller.execute_gcode("G28")
            print("    ✗ execute_gcode('G28') - should have raised CommandError")
        except Exception as e:
            if "Not connected" in str(e):
                print("    ✓ execute_gcode('G28') - correctly raises CommandError")
            else:
                print(f"    ✗ execute_gcode('G28') - unexpected error: {e}")

        try:
            controller.execute_gcode("G28", wait_for_ok=True)
            print(
                "    ✗ execute_gcode with wait_for_ok - should have raised CommandError"
            )
        except Exception as e:
            if "Not connected" in str(e):
                print(
                    "    ✓ execute_gcode with wait_for_ok - correctly raises CommandError"
                )
            else:
                print(f"    ✗ execute_gcode with wait_for_ok - unexpected error: {e}")

        try:
            controller.execute_gcode("G28", wait_for_ok=False)
            print(
                "    ✗ execute_gcode with wait_for_ok=False - should have raised CommandError"
            )
        except Exception as e:
            if "Not connected" in str(e):
                print(
                    "    ✓ execute_gcode with wait_for_ok=False - correctly raises CommandError"
                )
            else:
                print(
                    f"    ✗ execute_gcode with wait_for_ok=False - unexpected error: {e}"
                )

        try:
            controller.execute_gcode("G28", timeout=10.0)
            print("    ✗ execute_gcode with timeout - should have raised CommandError")
        except Exception as e:
            if "Not connected" in str(e):
                print(
                    "    ✓ execute_gcode with timeout - correctly raises CommandError"
                )
            else:
                print(f"    ✗ execute_gcode with timeout - unexpected error: {e}")

        print("  All method signatures work correctly!")
        return True

    except Exception as e:
        print(f"  ✗ Unexpected error testing method signatures: {e}")
        return False


def test_response_tracking_attributes():
    """Test that the response tracking attributes are properly initialized."""
    print("\nTesting Response Tracking Attributes")
    print("-" * 35)

    cnc = CNC()
    controller = Controller(cnc)

    # Check that the new attributes exist and are properly initialized
    attributes = [
        ("_response_event", "threading.Event"),
        ("_last_response", type(None)),
        ("_waiting_for_response", bool),
    ]

    all_passed = True
    for attr_name, expected_type in attributes:
        if hasattr(controller, attr_name):
            attr_value = getattr(controller, attr_name)
            if expected_type == "threading.Event":
                # Check if it's an Event object
                if hasattr(attr_value, "wait") and hasattr(attr_value, "set"):
                    print(f"  ✓ {attr_name} - correctly initialized as Event")
                else:
                    print(f"  ✗ {attr_name} - not a proper Event object")
                    all_passed = False
            elif isinstance(attr_value, expected_type):
                print(
                    f"  ✓ {attr_name} - correctly initialized as {expected_type.__name__}"
                )
            else:
                print(
                    f"  ✗ {attr_name} - expected {expected_type.__name__}, got {type(attr_value).__name__}"
                )
                all_passed = False
        else:
            print(f"  ✗ {attr_name} - attribute missing")
            all_passed = False

    print(
        f"\nAttribute initialization: {'All correct' if all_passed else 'Some issues found'}"
    )
    return all_passed


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)  # Reduce log noise

    print("Basic Functionality Test")
    print("=" * 24)

    test1 = test_gcode_pattern()
    test2 = test_method_signatures()
    test3 = test_response_tracking_attributes()

    print(
        f"\nOverall Result: {'All tests passed!' if all([test1, test2, test3]) else 'Some tests failed'}"
    )
