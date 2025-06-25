# CNC Controller Library Examples

This directory contains examples, demonstrations, and test scripts for the CNC Controller Core Library.

## 📁 Directory Contents

### 🎯 **Real Machine Testing**
Scripts for testing the library against actual Carvera machines:

- **`discover_machines.py`** - Discover CNC machines on your network
- **`quick_test.py`** - Fast validation test (10 seconds)
- **`test_real_machine.py`** - Comprehensive test suite (30-60 seconds)
- **`TESTING_REAL_MACHINE.md`** - Complete testing documentation

### 📚 **Examples and Demos**
- **`example_usage.py`** - Basic library usage examples and demonstrations

## 🚀 Quick Start

### 1. Find Your Machine
```bash
cd examples
python discover_machines.py --test
```

### 2. Quick Test
```bash
python quick_test.py 192.168.1.100
```

### 3. Full Test Suite
```bash
python test_real_machine.py --ip 192.168.1.100 --verbose
```

### 4. Run Examples
```bash
python example_usage.py
```

## 🛡️ Safety Information

**IMPORTANT:** The real machine test scripts perform minimal, safe operations:
- ✅ Small axis movements (±1mm only)
- ✅ Brief spindle tests with proper dwell periods
- ✅ Emergency stop capability
- ✅ Automatic cleanup and disconnection

Always ensure your machine is in a safe state before running tests!

## 📋 Script Details

### `discover_machines.py`
**Purpose:** Find Carvera machines on your local network
**Usage:** `python discover_machines.py [--timeout 5] [--test]`
**Safety:** Network discovery only, no machine commands

### `quick_test.py`
**Purpose:** Fast validation of core library functionality
**Usage:** `python quick_test.py <machine_ip> [port]`
**Duration:** ~10 seconds
**Operations:** Connection, keep-alive, basic commands, G-code parsing

### `test_real_machine.py`
**Purpose:** Comprehensive test suite with detailed reporting
**Usage:** `python test_real_machine.py --ip <ip> [--port 2222] [--verbose]`
**Duration:** ~30-60 seconds
**Operations:** All safe commands, movements, spindle tests, file operations

### `example_usage.py`
**Purpose:** Demonstrate library usage without hardware
**Usage:** `python example_usage.py`
**Safety:** No hardware required, local examples only

## 📊 Expected Results

### Successful Quick Test Output:
```
🔧 CNC Controller Library Quick Test
==================================================
📡 Connecting to 192.168.1.100:2222...
✅ Connected successfully
🔄 Keep-alive thread started: True

📋 Testing basic commands...
  Sending 'version' (Get firmware version)...
    ✅ Sent, got 1 responses

⏱️  Testing keep-alive (waiting 6 seconds)...
✅ Keep-alive working - connection maintained!

🎉 All tests completed successfully!
✅ Quick test PASSED - Library is working correctly!
```

### Comprehensive Test Summary:
```
TEST SUMMARY
============================================================
✅ Connection: PASSED
✅ Keep-alive: PASSED
📋 Safe Commands: 8/8 passed
📁 File Operations: 1/1 passed
📊 Status Queries: 6/6 passed
✅ Safe Movements: PASSED
✅ Spindle Operations: PASSED
------------------------------------------------------------
OVERALL: 26/26 tests passed
Success Rate: 100.0%
```

## 🔧 Troubleshooting

### Machine Not Found
- Ensure machine is powered on and WiFi connected
- Check that you're on the same network
- Try longer discovery timeout: `--timeout 10`

### Connection Failed
- Verify IP address is correct
- Check machine is not busy with another operation
- Ensure port 2222 is not blocked by firewall

### Keep-alive Issues
- Check network stability
- Verify no firewall blocking connections
- Try verbose mode for detailed logs

### Test Failures
- Check machine status display
- Ensure machine is in idle state
- Review verbose logs for specific errors

## 📝 Adding New Examples

To add new examples or tests:

1. **Safety First:** Ensure any new operations are safe and minimal
2. **Documentation:** Include clear docstrings and comments
3. **Error Handling:** Add proper exception handling
4. **Testing:** Test thoroughly before committing
5. **Documentation:** Update this README with new examples

## 🤝 Contributing

When contributing new examples:
- Follow the existing code style and structure
- Include comprehensive error handling
- Add appropriate safety checks and warnings
- Document expected behavior and results
- Test with real hardware when applicable

## 📞 Support

For help with examples or testing:
1. Check the detailed documentation in `TESTING_REAL_MACHINE.md`
2. Run tests with `--verbose` flag for detailed output
3. Ensure machine is in proper state before testing
4. Report issues with full log output

---

**Remember: Always prioritize safety when working with real CNC machines!**
