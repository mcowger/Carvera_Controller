#!/usr/bin/env python3
"""
Test script for GCODE response parsing functionality.

This script demonstrates the new GCODE response parsing capabilities,
including waiting for 'ok' responses with timeout handling.
"""

import logging
import time
from cnc_controller import Controller, CONN_WIFI
from cnc_core import CNC

def setup_logging():
    """Set up logging for the test."""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def test_gcode_response_parsing():
    """Test GCODE response parsing functionality."""
    print("Testing GCODE Response Parsing")
    print("=" * 40)
    
    # Create CNC and controller instances
    cnc = CNC()
    controller = Controller(cnc)
    
    # Note: This is a demonstration - you would need to connect to an actual machine
    # controller.connect("192.168.1.100:2222", CONN_WIFI)
    
    print("\n1. Testing GCODE command detection:")
    test_commands = [
        "G28",           # Home command - should be detected as GCODE
        "G0 X10 Y10",    # Rapid move - should be detected as GCODE  
        "M3 S1000",      # Spindle on - should be detected as GCODE
        "G1 X20 Y20 F1000",  # Linear move - should be detected as GCODE
        "?",             # Status query - not GCODE
        "$H",            # Home command - not GCODE
        "M5",            # Spindle off - should be detected as GCODE
    ]
    
    for cmd in test_commands:
        from cnc_controller import GCODE_PATTERN
        is_gcode = GCODE_PATTERN.match(cmd.strip())
        print(f"  '{cmd}' -> {'GCODE' if is_gcode else 'Not GCODE'}")
    
    print("\n2. Testing execute_gcode method signatures:")
    
    # Test different ways to call execute_gcode
    print("  execute_gcode('G28') - default behavior (wait for ok)")
    print("  execute_gcode('G28', wait_for_ok=True) - explicitly wait for ok")  
    print("  execute_gcode('G28', wait_for_ok=False) - don't wait for response")
    print("  execute_gcode('G28', timeout=10.0) - custom timeout")
    
    print("\n3. Testing send_command method signatures:")
    
    # Test different ways to call send_command
    print("  send_command('G28') - default behavior (no response wait)")
    print("  send_command('G28', wait_for_response=True) - wait for any response")
    print("  send_command('G28', wait_for_response=True, timeout=10.0) - custom timeout")
    
    print("\n4. Expected behavior:")
    print("  - GCODE commands (G/M codes) will wait for 'ok' response by default")
    print("  - Non-GCODE commands will not wait for responses")
    print("  - Timeout after 30 seconds by default")
    print("  - Returns 'ok' on success, None on timeout, or actual response")
    print("  - Logs warnings for timeouts and unexpected responses")
    
    print("\n5. Response handling:")
    print("  - Machine responses are captured in _parse_machine_response")
    print("  - 'ok' responses indicate successful GCODE execution")
    print("  - Error/alarm responses are logged as errors")
    print("  - Status reports update machine state")
    
    # Demonstrate the new functionality (without actual connection)
    print("\nNote: To test with actual machine:")
    print("1. Connect to your CNC machine:")
    print("   controller.connect('192.168.1.100:2222', CONN_WIFI)")
    print("2. Send GCODE commands:")
    print("   result = controller.execute_gcode('G28')")
    print("   if result == 'ok':")
    print("       print('Homing successful!')")
    print("   elif result is None:")
    print("       print('Timeout - machine may be busy')")
    print("   else:")
    print("       print(f'Unexpected response: {result}')")

if __name__ == "__main__":
    setup_logging()
    test_gcode_response_parsing()
