#!/usr/bin/env python3
"""
Machine Discovery Script for CNC Controller Library.

This script discovers Carvera machines on the local network and provides
information about their availability and status.

Usage:
    python discover_machines.py [--timeout 5]
"""

import sys
import time
import argparse
import os

# Add parent directory to path to import the CNC library
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from communication.wifi_stream import MachineDetector


def discover_machines(timeout: int = 5):
    """
    Discover CNC machines on the network.
    
    Args:
        timeout: Discovery timeout in seconds
        
    Returns:
        List of discovered machines
    """
    print("🔍 Discovering CNC machines on the network...")
    print("=" * 50)
    
    try:
        detector = MachineDetector()
        detector.query_for_machines()
        
        print(f"⏳ Waiting {timeout} seconds for responses...")
        
        # Show progress
        for i in range(timeout):
            time.sleep(1)
            print(f"  {i+1}/{timeout}s", end="\r")
        
        print("\n")
        
        # Get results
        machines = detector.check_for_responses()
        
        if machines:
            print(f"✅ Found {len(machines)} machine(s):")
            print()
            
            for i, machine in enumerate(machines, 1):
                status = "🔴 BUSY" if machine['busy'] else "🟢 AVAILABLE"
                print(f"  {i}. {machine['machine']}")
                print(f"     Address: {machine['ip']}:{machine['port']}")
                print(f"     Status:  {status}")
                print()
            
            return machines
        else:
            print("❌ No machines found on the network")
            print()
            print("Troubleshooting:")
            print("  - Make sure your machine is powered on")
            print("  - Check that you're on the same network as the machine")
            print("  - Verify the machine's WiFi connection")
            print("  - Try increasing the timeout with --timeout 10")
            
            return []
            
    except Exception as e:
        print(f"❌ Discovery failed: {e}")
        return []


def test_machine_connection(machine: dict):
    """
    Test connection to a discovered machine.
    
    Args:
        machine: Machine info dictionary
    """
    print(f"🔗 Testing connection to {machine['machine']}...")
    
    try:
        from cnc_controller import Controller, CONN_WIFI
        from cnc_core import CNC
        
        cnc = CNC()
        controller = Controller(cnc)
        
        address = f"{machine['ip']}:{machine['port']}"
        
        if controller.connect(address, CONN_WIFI):
            print(f"✅ Successfully connected to {machine['machine']}")
            
            # Send a quick status query
            controller.send_command("?")
            time.sleep(0.5)
            
            messages = controller.get_log_messages()
            if messages:
                print(f"📡 Machine responded with {len(messages)} message(s)")
                for msg_type, msg_content in messages[:3]:  # Show first 3
                    print(f"    {msg_content}")
            
            controller.disconnect()
            print("🔌 Disconnected")
            return True
        else:
            print(f"❌ Failed to connect to {machine['machine']}")
            return False
            
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Discover CNC machines on the network")
    parser.add_argument("--timeout", "-t", type=int, default=5, 
                       help="Discovery timeout in seconds (default: 5)")
    parser.add_argument("--test", action="store_true",
                       help="Test connection to discovered machines")
    
    args = parser.parse_args()
    
    try:
        machines = discover_machines(args.timeout)
        
        if machines and args.test:
            print("🧪 Testing connections to discovered machines...")
            print("=" * 50)
            
            for machine in machines:
                if not machine['busy']:  # Only test available machines
                    test_machine_connection(machine)
                    print()
                else:
                    print(f"⏭️  Skipping {machine['machine']} (busy)")
        
        if machines:
            print("💡 To test the library with a machine, run:")
            for machine in machines:
                if not machine['busy']:
                    print(f"   python quick_test.py {machine['ip']}")
                    break
        
        return 0 if machines else 1
        
    except KeyboardInterrupt:
        print("\n⚠️  Discovery interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Discovery failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
