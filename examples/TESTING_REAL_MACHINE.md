# Testing CNC Controller Library with Real Machines

This directory contains test scripts for validating the CNC Controller Core Library against real Carvera machines. These scripts are designed to be **safe** and perform only non-destructive operations.

## 🚨 Safety First

**IMPORTANT SAFETY NOTES:**
- These scripts perform **MINIMAL, SAFE** operations only
- **Small axis movements** (±1mm) and brief spindle tests only
- **NO file modifications** on the machine (except temporary test files)
- **Proper dwell periods** for spindle operations (2 seconds for startup)
- Emergency stop capability is built into all scripts
- Always ensure your machine is in a safe state before testing

## 📋 Available Test Scripts

### 1. `discover_machines.py` - Machine Discovery
Discovers Carvera machines on your local network.

```bash
# Basic discovery
python discover_machines.py

# Extended discovery with connection testing
python discover_machines.py --timeout 10 --test

# Quick discovery
python discover_machines.py --timeout 3
```

**What it does:**
- Broadcasts UDP discovery packets
- Lists all found machines with their IP addresses and status
- Optionally tests basic connectivity to available machines

### 2. `quick_test.py` - Fast Validation
Quick validation of core library functionality.

```bash
# Test with specific IP
python quick_test.py 192.168.1.100

# Test with custom port
python quick_test.py 192.168.1.100 2222
```

**What it tests:**
- ✅ Connection establishment
- ✅ Keep-alive functionality (prevents 5-second timeout)
- ✅ Basic safe commands (`version`, `?`, `$#`, `ls`)
- ✅ G-code parsing (local only, not sent to machine)
- ✅ Proper disconnection

**Duration:** ~10 seconds

### 3. `test_real_machine.py` - Comprehensive Testing
Full test suite for thorough validation.

```bash
# Basic comprehensive test
python test_real_machine.py --ip 192.168.1.100

# Verbose testing with detailed logs
python test_real_machine.py --ip 192.168.1.100 --verbose

# Custom port
python test_real_machine.py --ip 192.168.1.100 --port 2222
```

**What it tests:**
- 🔌 Connection and keep-alive functionality
- 📋 Safe console commands (`version`, `model`, `time`, `ls`, `pwd`, `df`, `free`)
- 📊 Status queries (`?`, `$#`, `$$`, `$I`, `$N`)
- 📁 File operations (listing only, no modifications)
- 🎯 Safe movements (±1mm axis movements)
- 🔄 Spindle operations (brief test with 2s dwell period)
- 🔍 G-code validation and parsing (local)
- 🌐 Machine discovery functionality
- 📈 Comprehensive reporting

**Duration:** ~30-60 seconds

## 🚀 Quick Start Guide

### Step 1: Discover Your Machine
```bash
python discover_machines.py --test
```

This will find your machine and test basic connectivity.

### Step 2: Run Quick Test
```bash
python quick_test.py <your_machine_ip>
```

Replace `<your_machine_ip>` with the IP address found in Step 1.

### Step 3: Full Validation (Optional)
```bash
python test_real_machine.py --ip <your_machine_ip> --verbose
```

## 📊 Understanding Test Results

### ✅ Success Indicators
- **Connection**: Library connects to machine successfully
- **Keep-alive**: Connection maintained for 6+ seconds (prevents timeout)
- **Commands**: Safe commands execute and receive responses
- **Parsing**: G-code parsing works correctly
- **Thread Management**: Background threads start/stop properly

### ❌ Common Issues

**Connection Failed:**
- Check machine IP address
- Verify machine is powered on and connected to WiFi
- Ensure you're on the same network as the machine
- Try `discover_machines.py` to find the correct IP

**Keep-alive Failed:**
- May indicate network issues
- Check for firewall blocking connections
- Verify machine firmware is compatible

**Command Timeouts:**
- Machine may be busy with another operation
- Try again when machine is idle
- Check machine status display

## 🛡️ Safety Features

### Emergency Stop
All scripts include emergency stop functionality:
- **Ctrl+C** during any test sends emergency stop commands
- Feed hold (`!`) and soft reset (`Ctrl+X`) are sent automatically
- Scripts always disconnect cleanly

### Safe Commands Only
The test scripts only use commands that are safe:

**✅ Safe Commands Used:**
- `version` - Get firmware version
- `model` - Get machine model
- `time` - Get/set machine time
- `ls` - List files
- `pwd` - Show current directory
- `df` - Show disk usage
- `free` - Show memory usage
- `?` - Get machine status
- `$#` - Get position information
- `$$` - Get settings (read-only)

**⚠️ Limited Safe Operations:**
- Small axis movements only (±1mm for testing)
- Brief spindle operations (1000 RPM, 2s dwell, then stop)
- No large movements or high-speed operations
- No file deletion or modification
- No settings changes
- No tool changes

## 🔧 Troubleshooting

### Machine Not Found
```bash
# Try longer discovery timeout
python discover_machines.py --timeout 10

# Check machine network settings
# Ensure machine WiFi is connected
# Verify you're on same network
```

### Connection Issues
```bash
# Test with verbose logging
python quick_test.py 192.168.1.100 --verbose

# Check if machine is busy
# Look at machine display for status
# Try again when machine is idle
```

### Keep-alive Problems
```bash
# Test with comprehensive suite
python test_real_machine.py --ip 192.168.1.100 --verbose

# Check network stability
# Verify no firewall blocking
```

## 📝 Test Reports

The comprehensive test script generates detailed reports:

```
TEST SUMMARY
============================================================
✅ Connection: PASSED
✅ Keep-alive: PASSED
📋 Safe Commands: 8/8 passed
📁 File Operations: 1/1 passed
📊 Status Queries: 6/6 passed
------------------------------------------------------------
OVERALL: 24/24 tests passed
Success Rate: 100.0%
```

## 🤝 Contributing Test Cases

To add new safe test cases:

1. Ensure the command is **read-only** and **non-destructive**
2. Add to the appropriate test function
3. Include proper error handling
4. Document the expected behavior
5. Test thoroughly before submitting

## 📞 Support

If you encounter issues with the test scripts:

1. **Check the logs** - Use `--verbose` flag for detailed output
2. **Verify machine state** - Ensure machine is idle and responsive
3. **Network connectivity** - Confirm you can ping the machine IP
4. **Firewall settings** - Ensure port 2222 is not blocked
5. **Report issues** - Include full log output when reporting problems

---

**Remember: These tests are designed to be safe, but always ensure your machine is in a safe state before running any tests!**
