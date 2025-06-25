#!/usr/bin/env python3
"""
Example: Using GCODE Response Parsing

This example demonstrates how to use the new GCODE response parsing
functionality to send commands and verify they complete successfully.
"""

import logging
import time
from cnc_controller import Controller, CONN_WIFI
from cnc_core import CNC

def setup_logging():
    """Set up logging to see debug information."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def safe_gcode_execution(controller, command, description=""):
    """
    Safely execute a GCODE command with proper error handling.
    
    Args:
        controller: CNC controller instance
        command: GCODE command to execute
        description: Human-readable description of the command
    
    Returns:
        True if successful, False otherwise
    """
    print(f"Executing: {command}" + (f" ({description})" if description else ""))
    
    try:
        result = controller.execute_gcode(command, wait_for_ok=True, timeout=30.0)
        
        if result == 'ok':
            print(f"  ✓ Success: {command}")
            return True
        elif result is None:
            print(f"  ✗ Timeout: {command} - Machine may be busy or disconnected")
            return False
        else:
            print(f"  ⚠ Unexpected response to {command}: {result}")
            return False
            
    except Exception as e:
        print(f"  ✗ Error executing {command}: {e}")
        return False

def example_cnc_sequence():
    """
    Example CNC operation sequence with response validation.
    
    This demonstrates a typical workflow:
    1. Home the machine
    2. Move to a safe position
    3. Set spindle speed
    4. Perform some movements
    5. Stop spindle
    6. Return to home
    """
    print("CNC Operation Sequence with Response Validation")
    print("=" * 50)
    
    # Create controller
    cnc = CNC()
    controller = Controller(cnc)
    
    # Note: Uncomment the next line to connect to actual machine
    # if not controller.connect("192.168.1.100:2222", CONN_WIFI):
    #     print("Failed to connect to CNC machine")
    #     return False
    
    print("Note: This example shows the commands that would be sent.")
    print("To run with actual machine, uncomment the connect() line above.\n")
    
    # Sequence of operations
    operations = [
        ("G28", "Home all axes"),
        ("G90", "Set absolute positioning"),
        ("G0 Z5", "Move to safe Z height"),
        ("G0 X10 Y10", "Move to starting position"),
        ("M3 S1000", "Start spindle at 1000 RPM"),
        ("G4 P2", "Dwell for 2 seconds"),
        ("G1 X20 Y20 F500", "Linear move to (20,20) at 500 mm/min"),
        ("G1 X30 Y10 F500", "Linear move to (30,10)"),
        ("G1 X10 Y10 F500", "Return to starting position"),
        ("M5", "Stop spindle"),
        ("G0 Z25", "Move to safe Z height"),
        ("G28", "Return to home"),
    ]
    
    success_count = 0
    total_count = len(operations)
    
    for command, description in operations:
        if safe_gcode_execution(controller, command, description):
            success_count += 1
        time.sleep(0.1)  # Small delay between commands
    
    print(f"\nOperation Summary:")
    print(f"  Successful: {success_count}/{total_count}")
    print(f"  Success Rate: {success_count/total_count*100:.1f}%")
    
    if success_count == total_count:
        print("  ✓ All operations completed successfully!")
    else:
        print("  ⚠ Some operations failed - check machine status")
    
    return success_count == total_count

def example_mixed_commands():
    """
    Example showing mixed GCODE and non-GCODE commands.
    """
    print("\nMixed Command Types Example")
    print("=" * 30)
    
    cnc = CNC()
    controller = Controller(cnc)
    
    # Different types of commands
    commands = [
        ("G28", True, "GCODE - will wait for 'ok'"),
        ("?", False, "Status query - no response wait"),
        ("$H", False, "System command - no response wait"),
        ("M3 S1000", True, "GCODE - will wait for 'ok'"),
        ("$X", False, "Unlock command - no response wait"),
        ("G0 X0 Y0", True, "GCODE - will wait for 'ok'"),
    ]
    
    for command, is_gcode, description in commands:
        print(f"Command: {command:12} | {description}")
        
        if is_gcode:
            # This will automatically wait for 'ok' response
            result = controller.execute_gcode(command)
            print(f"  Expected result type: str ('ok' or error message)")
        else:
            # This will not wait for response
            result = controller.send_command(command)
            print(f"  Expected result type: bool (True if sent successfully)")
        
        print(f"  (Would return: {type(result).__name__})\n")

if __name__ == "__main__":
    setup_logging()
    
    # Run the examples
    example_cnc_sequence()
    example_mixed_commands()
    
    print("\nKey Points:")
    print("- GCODE commands (G/M codes) automatically wait for 'ok' responses")
    print("- Non-GCODE commands are sent without waiting for responses")
    print("- Timeouts prevent hanging if machine doesn't respond")
    print("- Proper error handling ensures robust operation")
    print("- All responses are logged for debugging")
