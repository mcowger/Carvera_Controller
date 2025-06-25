# Carvera Controller Core Library

**UI-free CNC controller library for Carvera machines**

This repository contains a completely refactored, UI-free core library extracted from the community-developed Carvera Controller. The library provides all the essential CNC control functionality without any user interface dependencies.

## 🎯 Purpose

This core library enables developers to:
- **Build custom user interfaces** for Carvera machines using any framework
- **Create automated CNC control applications** for production workflows
- **Integrate Carvera control** into existing manufacturing systems
- **Develop headless CNC operations** for remote or automated control

## 🏗️ Architecture

The library is organized into clean, focused modules:

### **Core Modules**
- **`cnc_core.py`** - G-code parser and CNC state management
- **`cnc_controller.py`** - Main controller for machine communication
- **`cnc_utils.py`** - Utility functions for common operations

### **Communication Module**
- **`communication/usb_stream.py`** - USB/Serial communication
- **`communication/wifi_stream.py`** - WiFi/TCP communication and machine discovery
- **`communication/xmodem.py`** - XMODEM file transfer protocol

### **Testing & Examples**
- **`tests/`** - Comprehensive unit tests (59 tests)
- **`examples/`** - Real machine testing and usage demonstrations

## 🚀 Quick Start

### **Basic Usage**

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

### **G-code Parsing**

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

### **Machine Discovery**

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

### **Advanced Operations**

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

## 📋 Supported G-codes

The library supports standard G-codes and Carvera-specific extensions:

### **Motion Commands**
- `G0` - Rapid positioning
- `G1` - Linear interpolation
- `G2` - Clockwise circular interpolation
- `G3` - Counter-clockwise circular interpolation
- `G4` - Dwell

### **Coordinate Systems**
- `G17/G18/G19` - Plane selection (XY/XZ/YZ)
- `G20/G21` - Units (inches/millimeters)
- `G90/G91` - Absolute/relative positioning
- `G54-G59` - Work coordinate systems

### **Canned Cycles**
- `G81/G82/G83` - Drilling cycles
- `G85/G86/G89` - Boring cycles

### **Carvera-Specific Commands**
- `M495` - Auto-leveling and probing
- `M496.x` - Position commands (Clearance, Work Origin, Anchors)
- `M321` - Laser mode
- `M471` - Workpiece pairing

## ✨ Key Features

### **Core Functionality**
- **Complete G-code Support** - Standard commands and Carvera-specific extensions
- **Machine State Management** - Comprehensive CNC machine state tracking
- **Path Calculation** - Real-time tool path calculation and coordinate interpolation
- **4-Axis Support** - Full rotary axis functionality with proper kinematics

### **Communication**
- **Multiple Protocols** - USB/Serial and WiFi/TCP connections
- **Keep-Alive Functionality** - Prevents 5-second firmware timeout disconnections
- **Machine Discovery** - Network discovery of available CNC machines
- **File Transfer** - XMODEM protocol support for file uploads/downloads

### **Advanced Features**
- **Auto-leveling & Probing** - Complete probing operations and mesh leveling
- **Coordinate Systems** - Support for multiple work coordinate systems
- **Tool Management** - Tool change operations and tool offset handling
- **Emergency Controls** - Feed hold, soft reset, and alarm management

### **Developer Experience**
- **Zero UI Dependencies** - No Kivy, Qt, or GUI framework requirements
- **Modern Python** - Type hints, proper error handling, PEP 257 documentation
- **Comprehensive Testing** - 59 unit tests covering all functionality
- **Real Machine Testing** - Safe validation scripts for actual hardware

## 📦 Installation

### **As a Python Package**

```bash
# Clone the repository
git clone https://github.com/mcowger/Carvera_Controller.git
cd Carvera_Controller

# Switch to the core library branch
git checkout mcowger/NoMoKivy

# Install dependencies
pip install pyserial

# Run tests
python tests/run_tests.py

# Try the examples
cd examples
python quick_test.py 192.168.1.100
```

### **Using Poetry**

```bash
# Install with poetry
poetry install

# Run tests
poetry run python tests/run_tests.py
```

### **Dependencies**

**Runtime:**
- Python 3.9+
- pyserial (for USB/Serial communication)

**Development:**
- pytest (for testing)
- pytest-cov (for coverage)

## 🌐 Communication Protocols

### **WiFi/TCP Connection**
```python
# Connect to machine via WiFi
controller.connect("192.168.1.100:2222", CONN_WIFI)
```

### **USB/Serial Connection**
```python
# Connect to machine via USB
controller.connect("/dev/ttyUSB0", CONN_USB)  # Linux
controller.connect("COM3", CONN_USB)          # Windows
```

### **Keep-Alive Functionality**

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

## 🧪 Testing

### **Unit Tests**
The library includes comprehensive unit tests:

```bash
# Run all tests
python tests/run_tests.py

# Or with pytest
pytest tests/

# Run with coverage
pytest --cov=. tests/
```

**Test Coverage:**
- 59 unit tests covering all core functionality
- G-code parsing and validation
- Machine communication (mocked)
- Utility functions and edge cases
- Keep-alive functionality
- Error handling scenarios

### **Real Machine Testing**
Test scripts for validating against actual Carvera machines:

```bash
cd examples

# Discover machines on network
python discover_machines.py --test

# Quick validation test
python quick_test.py 192.168.1.100

# Comprehensive test suite
python test_real_machine.py --ip 192.168.1.100 --verbose
```

**Safety Features:**
- Only minimal, safe operations (±1mm movements, brief spindle tests)
- Proper dwell periods for spindle operations
- Emergency stop capability
- Automatic connection cleanup

See [examples/TESTING_REAL_MACHINE.md](examples/TESTING_REAL_MACHINE.md) for detailed testing guide.

## 📋 Examples

See the `examples/` directory for:
- **Real machine testing scripts** - Safe validation against actual hardware
- **Usage demonstrations** - Working code examples
- **Machine discovery tools** - Network discovery utilities
- **Comprehensive test suites** - Full functionality validation

Quick start:
```bash
cd examples
python discover_machines.py --test    # Find your machine
python quick_test.py 192.168.1.100   # Quick validation
```

## 🖥️ Supported Systems

The core library works on any system that supports Python 3.9+:

- **Windows** 7 x64 or newer
- **macOS** 10.15 or newer (Intel and Apple Silicon)
- **Linux** with Python 3.9+ (x64, ARM64, Raspberry Pi)
- **Any Python environment** with network or serial port access

## 🔌 Integration

The core library is designed for easy integration:

```python
# Basic CNC operations
from cnc_core import CNC
cnc = CNC()
coordinates = cnc.parse_line("G1 X10 Y20 F1000", 1)

# Machine communication
from cnc_controller import Controller
controller = Controller()
controller.connect("192.168.1.100:2222")

# Utility functions
from cnc_utils import validate_gcode_line, parse_coordinate_string
is_valid = validate_gcode_line("G0 X10 Y20")
coords = parse_coordinate_string("X10.5 Y20.3 Z5.0")
```

## 🤝 Contributing

We welcome contributions to the CNC Controller Core Library! Here's how to get started:

### Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/mcowger/Carvera_Controller.git
   cd Carvera_Controller
   git checkout mcowger/NoMoKivy
   ```

2. **Install dependencies:**
   ```bash
   # Using pip
   pip install -e .
   pip install pytest pytest-cov

   # Or using poetry
   poetry install
   ```

3. **Run tests:**
   ```bash
   python tests/run_tests.py
   ```

### Contributing Guidelines

- **Code Style:** Follow PEP 8 and include type hints
- **Documentation:** Add docstrings following PEP 257
- **Testing:** Write tests for new functionality
- **Commits:** Use clear, descriptive commit messages

### Development Focus Areas

- **New UI Frameworks:** Build modern UIs on top of this core
- **Automation Tools:** Create automated CNC workflows
- **Protocol Extensions:** Add support for new machine features
- **Performance:** Optimize G-code parsing and communication
- **Testing:** Expand test coverage and add integration tests

## 🔗 Related Projects

- **Original Carvera Controller:** The UI-based community controller (archived)
- **Makera Official Software:** The original manufacturer software
- **OpenCNCPilot:** Alternative CNC control software
- **Universal G-Code Sender:** Java-based CNC control platform

## 📄 License

This project is licensed under the GPL-2.0 License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Carvera Community:** For the original community controller development
- **Makera:** For creating the Carvera CNC machine
- **Contributors:** All developers who contributed to the original project
- **Testers:** Community members who helped test and improve the software

## 📞 Support

- **Examples:** See `examples/` directory for working code examples and testing tools
- **Issues:** Report bugs and feature requests via GitHub Issues
- **Discussions:** Use GitHub Discussions for questions and ideas
- **Testing:** Use `examples/quick_test.py` to validate your setup

## 🚀 Future Roadmap

- **Web UI:** Browser-based interface using the core library
- **REST API:** HTTP API for remote CNC control
- **Plugin System:** Extensible architecture for custom functionality
- **Advanced Probing:** Enhanced probing operations and workflows
- **Machine Learning:** Intelligent feed rate and path optimization

---

**Note:** This is a complete refactoring of the original Carvera Controller to create a UI-free core library. The original UI-based application has been archived in favor of this modular approach that enables building modern, custom interfaces on top of a solid foundation.