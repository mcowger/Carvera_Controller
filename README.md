# Carvera Controller Core Library

**UI-free CNC controller library for Carvera machines**

This repository contains a completely refactored, UI-free core library extracted from the community-developed Carvera Controller. The library provides all the essential CNC control functionality without any user interface dependencies.

## 🎯 Purpose

This core library enables developers to:
- Build custom user interfaces for Carvera machines
- Create automated CNC control applications
- Integrate Carvera control into existing workflows
- Develop headless CNC operations

## 📚 Documentation

For complete API documentation, examples, and usage guides, see:
**[📖 CNC Core Library Documentation](README_CNC_CORE.md)**

## 🚀 Quick Start

```python
from cnc_controller import Controller, CONN_WIFI
from cnc_core import CNC

# Create instances
cnc = CNC()
controller = Controller(cnc)

# Connect and control
controller.connect("192.168.1.100:2222", CONN_WIFI)
controller.send_command("G28")  # Home
controller.send_command("G0 X10 Y10")  # Move
controller.disconnect()
```

## ✨ Key Features

- **Complete UI Elimination** - No Kivy or GUI dependencies
- **Keep-Alive Functionality** - Prevents 5-second firmware timeout
- **Full G-code Support** - Standard and Carvera-specific commands
- **Multiple Communication** - USB/Serial and WiFi/TCP
- **Machine Discovery** - Network discovery of available machines
- **Auto-leveling & Probing** - Complete probing operations support
- **4-Axis Support** - Full rotary axis functionality
- **Comprehensive Testing** - 59 unit tests, all passing
- **Modern Python** - Type hints, proper error handling, PEP 257 docs

## 🏗️ Original Community Controller Features

The original UI-based community controller (now archived) included:
* **3-axis** and advanced **probing** UI screens for various geometries (**corners**, **axis**, **bore/pocket**, **angles**) for use with a [true 3D touch probe](https://www.instructables.com/Carvera-Touch-Probe-Modifications/) (not the included XYZ probe block)
* Options to **reduce** the **autolevel** probe **area** to avoid probing obstacles
* **Tooltip support** for user guidance with over 110 tips and counting
* **Background images** for bolt hole positions in probe/start screens; users can add their own too
* Support for setting/changing to **custom tool numbers** beyond 1-6
* Keyboard button based **jog movement** controls
* **No dial-home** back to Makera
* **Single portable binary** for Windows and Linux
* **Laser Safety** prompt to **remind** operators to put on **safety glasses**
* **Multiple developers** with their own **Carvera** machines _"drinking their own [software] champagne"_ daily and working to improve the machine's capabilities.
* Various **Quality-of-life** improvements:
   * **Controller config settings** (UI Density, screensaver disable, Allow MDI while machine running, virtual keyboard)
   * **Enclosure light** and **External Ouput** switch toggle in the center control panel
   * Machine **reconnect** functionality with stored last used **machine network address**
   * **Set Origin** Screen pre-populated with **current** offset values
   * **Collet Clamp/Unclamp** buttons in Tool Changer menu for the original Carvera
   * Better file browser **upload-and-select** workflow
   * **Previous** file browsing location is **reopened** and **previously** used locations stored to **quick access list**
   * **Greater speed/feed** override scaling range from **10%** and up to **300%**
   * **Improved** 3D gcode visualisations, including **correct rendering** of movements around the **A axis**


## 🔧 Installation

### As a Python Package

```bash
# Clone the repository
git clone https://github.com/mcowger/Carvera_Controller.git
cd Carvera_Controller

# Switch to the core library branch
git checkout mcowger/NoMoKivy

# Install dependencies
pip install pyserial

# Run tests
python run_tests.py

# Try the example
python example_usage.py
```

### Using Poetry

```bash
# Install with poetry
poetry install

# Run tests
poetry run python run_tests.py
```

## 🖥️ Supported Systems

The core library works on any system that supports Python 3.9+:

- **Windows** 7 x64 or newer
- **macOS** 10.15 or newer (Intel and Apple Silicon)
- **Linux** with Python 3.9+ (x64, ARM64, Raspberry Pi)
- **Any Python environment** with network or serial port access

## 📦 Dependencies

**Runtime:**
- Python 3.9+
- pyserial (for USB/Serial communication)

**Development:**
- pytest (for testing)
- pytest-cov (for coverage)

## 🧪 Testing

The library includes comprehensive unit tests:

```bash
# Run all tests
python run_tests.py

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

## 📋 Examples

See `example_usage.py` for working examples of:
- Machine discovery
- G-code parsing
- Controller operations
- Keep-alive functionality
- Error handling

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
   python run_tests.py
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

- **Documentation:** [CNC Core Library Docs](README_CNC_CORE.md)
- **Examples:** See `example_usage.py` for working code examples
- **Issues:** Report bugs and feature requests via GitHub Issues
- **Discussions:** Use GitHub Discussions for questions and ideas

## 🚀 Future Roadmap

- **Web UI:** Browser-based interface using the core library
- **REST API:** HTTP API for remote CNC control
- **Plugin System:** Extensible architecture for custom functionality
- **Advanced Probing:** Enhanced probing operations and workflows
- **Machine Learning:** Intelligent feed rate and path optimization

---

**Note:** This is a complete refactoring of the original Carvera Controller to create a UI-free core library. The original UI-based application has been archived in favor of this modular approach that enables building modern, custom interfaces on top of a solid foundation.