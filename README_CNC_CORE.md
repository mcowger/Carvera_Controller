# CNC Controller Core Library

A clean, UI-free CNC controller library extracted from the Carvera Controller application. This library provides core functionality for controlling CNC machines without any user interface dependencies.

## Features

- **G-code Parsing**: Complete G-code parser supporting standard commands and Carvera-specific extensions
- **Machine Communication**: Support for both USB/Serial and WiFi/TCP connections
- **State Management**: Comprehensive CNC machine state tracking
- **File Transfer**: XMODEM protocol support for file uploads/downloads
- **Machine Discovery**: Network discovery of available CNC machines
- **Keep-Alive**: Automatic keep-alive functionality to prevent 5-second timeout disconnections
- **Coordinate Systems**: Support for multiple coordinate systems and 4-axis machines
- **Path Calculation**: Real-time tool path calculation and visualization data
- **Well Documented**: Comprehensive docstrings following PEP 257
- **Fully Tested**: Unit tests covering core functionality

## Architecture

The library is organized into several key modules:

### Core Modules

- **`cnc_core.py`**: G-code parser and CNC state management
- **`cnc_controller.py`**: Main controller for machine communication
- **`cnc_utils.py`**: Utility functions for common operations

### Communication Module

- **`communication/usb_stream.py`**: USB/Serial communication
- **`communication/wifi_stream.py`**: WiFi/TCP communication and machine discovery
- **`communication/xmodem.py`**: XMODEM file transfer protocol

### Testing

- **`tests/`**: Comprehensive unit tests
- **`run_tests.py`**: Test runner script

## Installation

Since this is a refactored library, you can use it by copying the files to your project or installing dependencies:

```bash
# Required dependencies
pip install pyserial  # For USB/Serial communication
```

## Quick Start

### Basic Usage

```python
from cnc_controller import Controller, CONN_WIFI
from cnc_core import CNC

# Create CNC instance
cnc = CNC()

# Create controller
controller = Controller(cnc)

# Connect to machine via WiFi
controller.connect("192.168.1.100:2222", CONN_WIFI)

# Send basic commands
controller.send_command("G28")  # Home all axes
controller.send_command("G0 X10 Y10")  # Rapid move
controller.send_command("G1 X20 Y20 F1000")  # Linear move with feed rate

# Get machine status
controller.get_status()

# Disconnect
controller.disconnect()
```

### G-code Parsing

```python
from cnc_core import CNC

cnc = CNC()

# Parse G-code lines
coordinates = cnc.parse_line("G1 X10 Y20 Z5 F1000", line_number=1)
if coordinates:
    print(f"Generated {len(coordinates)} coordinate points")

# Access machine state
print(f"Current position: X={cnc.x}, Y={cnc.y}, Z={cnc.z}")
print(f"Feed rate: {cnc.feed}")
print(f"Spindle speed: {cnc.speed}")

# Get bounding box
margins = cnc.get_margins()
print(f"Bounding box: {margins}")
```

### Machine Discovery

```python
from communication.wifi_stream import MachineDetector

detector = MachineDetector()
detector.query_for_machines()

# Wait for responses
import time
time.sleep(3)

machines = detector.check_for_responses()
if machines:
    for machine in machines:
        print(f"Found: {machine['machine']} at {machine['ip']}:{machine['port']}")
```

### Advanced Operations

```python
# Auto-leveling and probing
controller.auto_command(
    margin=True,
    zprobe=True,
    leveling=True,
    i=5, j=5,  # 5x5 grid
    goto_origin=True
)

# XYZ probe
controller.xyz_probe(height=10.0, diameter=3.175)

# Jog machine
controller.jog(x=1, y=1, speed=50)

# Set overrides
controller.set_feed_scale(150)  # 150% feed rate
controller.set_spindle_scale(80)  # 80% spindle speed
```

## Supported G-codes

The library supports standard G-codes and Carvera-specific extensions:

### Motion Commands
- `G0` - Rapid positioning
- `G1` - Linear interpolation
- `G2` - Clockwise circular interpolation
- `G3` - Counter-clockwise circular interpolation
- `G4` - Dwell

### Coordinate Systems
- `G17/G18/G19` - Plane selection (XY/XZ/YZ)
- `G20/G21` - Units (inches/millimeters)
- `G90/G91` - Absolute/relative positioning
- `G54-G59` - Work coordinate systems

### Canned Cycles
- `G81/G82/G83` - Drilling cycles
- `G85/G86/G89` - Boring cycles

### Carvera-Specific Commands
- `M495` - Auto-leveling and probing
- `M496.x` - Position commands
- `M321` - Laser mode
- `M471` - Workpiece pairing

## Communication Protocols

### WiFi/TCP Connection
```python
# Connect to machine via WiFi
controller.connect("192.168.1.100:2222", CONN_WIFI)
```

### USB/Serial Connection
```python
# Connect to machine via USB
controller.connect("/dev/ttyUSB0", CONN_USB)  # Linux
controller.connect("COM3", CONN_USB)          # Windows
```

### Keep-Alive Functionality

The library automatically handles the Carvera firmware's 5-second timeout by:

- **Automatic Status Queries**: Sends `?` commands every 0.2 seconds when idle
- **Background Thread**: Runs keep-alive in a separate thread
- **Smart Detection**: Only sends keep-alive when not actively running commands
- **Diagnostic Support**: Optional diagnostic queries for troubleshooting

```python
# Keep-alive is automatic, but you can control the running state
controller.set_running_state(True)   # Disable keep-alive during long operations
controller.set_running_state(False)  # Re-enable keep-alive when idle
```

## Error Handling

The library provides comprehensive error handling:

```python
from cnc_controller import ConnectionError, CommandError
from cnc_core import GCodeParseError

try:
    controller.connect("invalid_address", CONN_WIFI)
except ConnectionError as e:
    print(f"Connection failed: {e}")

try:
    controller.send_command("INVALID_COMMAND")
except CommandError as e:
    print(f"Command failed: {e}")

try:
    cnc.parse_line("INVALID GCODE", 1)
except GCodeParseError as e:
    print(f"Parse error: {e}")
```

## Testing

Run the test suite to verify functionality:

```bash
python run_tests.py
```

The tests cover:
- G-code parsing and validation
- Coordinate calculations
- Machine state management
- Communication protocols (mocked)
- Utility functions
- Error handling

## API Reference

### CNC Class

The core G-code parser and state manager.

**Key Methods:**
- `parse_line(line, line_no)` - Parse a G-code line
- `init_path(x, y, z, a)` - Initialize path tracking
- `reset_margins()` - Reset bounding box
- `get_margins()` - Get current bounding box

**Key Properties:**
- `x, y, z, a` - Current position
- `feed` - Current feed rate
- `speed` - Current spindle speed
- `coordinates` - List of calculated coordinates

### Controller Class

Main controller for machine communication.

**Key Methods:**
- `connect(address, type)` - Connect to machine
- `disconnect()` - Disconnect from machine
- `send_command(cmd)` - Send command to machine
- `execute_gcode(line)` - Execute G-code line
- `home_machine()` - Home all axes
- `jog(x, y, z, a, speed)` - Jog machine
- `get_status()` - Get machine status

## Dependencies

- **Python 3.6+**
- **pyserial** - For USB/Serial communication
- **Standard library only** - No other external dependencies

## License

This library maintains the same license as the original Carvera Controller project (GPL-2.0).

## Contributing

This is a refactored library extracted from the original Carvera Controller. For contributions to the main project, please refer to the original repository.

## Changelog

### Version 1.0.0
- Initial extraction from Carvera Controller
- Complete UI removal
- Added comprehensive documentation
- Added unit tests
- Organized into clean module structure
- Added proper error handling
- Added type hints where appropriate
