#!/usr/bin/env python3
"""
Example usage of the CNC Controller Library.

This script demonstrates how to use the refactored CNC controller library
for basic operations without any UI dependencies.
"""

import sys
import time
import logging
from cnc_controller import Controller, CONN_WIFI, CONN_USB, ConnectionError, CommandError
from cnc_core import CNC, GCodeParseError
from cnc_utils import validate_gcode_line, parse_coordinate_string
from communication.wifi_stream import MachineDetector

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def discover_machines():
    """Discover CNC machines on the network."""
    print("Discovering CNC machines on the network...")
    detector = MachineDetector()
    detector.query_for_machines()
    
    # Wait for responses
    time.sleep(3)
    
    machines = detector.check_for_responses()
    if machines:
        print(f"Found {len(machines)} machine(s):")
        for machine in machines:
            status = "BUSY" if machine['busy'] else "AVAILABLE"
            print(f"  - {machine['machine']} at {machine['ip']}:{machine['port']} ({status})")
        return machines
    else:
        print("No machines found on the network.")
        return []


def parse_gcode_example():
    """Demonstrate G-code parsing capabilities."""
    print("\n=== G-code Parsing Example ===")
    
    cnc = CNC()
    
    # Example G-code program
    gcode_lines = [
        "G90",  # Absolute positioning
        "G21",  # Millimeters
        "G0 X0 Y0 Z5",  # Rapid move to origin, Z up
        "G1 Z0 F300",  # Plunge to work surface
        "G1 X10 Y10 F1000",  # Linear move
        "G2 X20 Y10 I5 J0 F500",  # Clockwise arc
        "G1 X20 Y0",  # Linear move
        "G0 Z5",  # Retract
    ]
    
    print("Parsing G-code program:")
    for i, line in enumerate(gcode_lines, 1):
        print(f"  Line {i}: {line}")
        
        # Validate line
        if validate_gcode_line(line):
            # Parse line
            try:
                coordinates = cnc.parse_line(line, i)
                if coordinates:
                    print(f"    Generated {len(coordinates)} coordinate points")
                else:
                    print("    No movement generated")
            except GCodeParseError as e:
                print(f"    Parse error: {e}")
        else:
            print("    Invalid G-code line")
    
    # Show final state
    print(f"\nFinal position: X={cnc.x:.2f}, Y={cnc.y:.2f}, Z={cnc.z:.2f}")
    print(f"Feed rate: {cnc.feed}")
    print(f"Spindle speed: {cnc.speed}")
    
    # Show bounding box
    margins = cnc.get_margins()
    print(f"Bounding box: X({margins[0]:.2f} to {margins[3]:.2f}), "
          f"Y({margins[1]:.2f} to {margins[4]:.2f}), "
          f"Z({margins[2]:.2f} to {margins[5]:.2f})")
    
    print(f"Total coordinates generated: {len(cnc.coordinates)}")


def controller_example():
    """Demonstrate controller usage (without actual connection)."""
    print("\n=== Controller Example ===")
    
    # Create CNC and controller instances
    cnc = CNC()
    controller = Controller(cnc, logger=logger)
    
    print("Controller created successfully")
    print(f"Connection status: {'Connected' if controller.is_connected() else 'Not connected'}")
    
    # Example of command validation
    test_commands = [
        "G28",  # Home
        "G0 X10 Y20",  # Rapid move
        "?",  # Status query
        "$H",  # Home command
        "INVALID",  # Invalid command
    ]
    
    print("\nValidating commands:")
    for cmd in test_commands:
        # Just check if it's valid G-code without sending
        from cnc_utils import validate_gcode_line
        is_valid = validate_gcode_line(cmd)
        print(f"  '{cmd}': {'Valid G-code' if is_valid else 'Not G-code'}")
    
    # Show command history (empty since we're not connected)
    history = controller.get_history()
    print(f"\nCommand history: {len(history)} commands")


def coordinate_parsing_example():
    """Demonstrate coordinate string parsing."""
    print("\n=== Coordinate Parsing Example ===")
    
    coord_strings = [
        "X10.5 Y20.3 Z5.0",
        "X-15 Y25.7",
        "A90 B45",
        "F1000 S2000",
        "Invalid coordinate string",
    ]
    
    for coord_str in coord_strings:
        coords = parse_coordinate_string(coord_str)
        print(f"'{coord_str}' -> {coords}")


def simulated_connection_example():
    """Demonstrate connection handling (will fail without real hardware)."""
    print("\n=== Connection Example (Simulated) ===")

    controller = Controller()

    # Try to connect to a non-existent machine
    try:
        print("Attempting to connect to 192.168.1.100:2222...")
        controller.connect("192.168.1.100:2222", CONN_WIFI)
        print("Connected successfully!")
        print("Keep-alive thread started automatically to prevent 5-second timeout")

        # Simulate some work
        print("Simulating work for 2 seconds...")
        controller.set_running_state(True)  # Disable keep-alive during operation
        time.sleep(2)
        controller.set_running_state(False)  # Re-enable keep-alive

        # Send some commands
        controller.send_command("?")  # Status
        controller.send_command("G28")  # Home

        # Disconnect
        controller.disconnect()
        print("Disconnected successfully!")
        print("Keep-alive thread stopped automatically")

    except ConnectionError as e:
        print(f"Connection failed (expected): {e}")
    except CommandError as e:
        print(f"Command failed: {e}")


def keep_alive_demonstration():
    """Demonstrate the keep-alive functionality."""
    print("\n=== Keep-Alive Functionality Demo ===")

    print("The CNC controller automatically handles the Carvera firmware's")
    print("5-second timeout by sending status queries every 0.2 seconds.")
    print()
    print("Key features:")
    print("- Automatic background thread for keep-alive")
    print("- Smart detection of when machine is busy")
    print("- Graceful handling of connection errors")
    print("- Thread cleanup on disconnection")
    print()
    print("This prevents the common issue where the machine disconnects")
    print("after 5 seconds of inactivity, which was a critical feature")
    print("in the original Carvera Controller application.")


def main():
    """Main example function."""
    print("CNC Controller Library Example")
    print("=" * 40)
    
    # Run examples
    try:
        # Discover machines (will work if on same network as CNC machines)
        discover_machines()
        
        # Parse G-code
        parse_gcode_example()
        
        # Controller usage
        controller_example()
        
        # Coordinate parsing
        coordinate_parsing_example()
        
        # Keep-alive demonstration
        keep_alive_demonstration()

        # Simulated connection
        simulated_connection_example()
        
    except KeyboardInterrupt:
        print("\nExample interrupted by user")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        return 1
    
    print("\nExample completed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
