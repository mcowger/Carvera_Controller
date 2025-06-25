"""
CNC Utilities Module - Core utility functions for CNC operations.

This module provides utility functions for file operations, data conversion,
and other common CNC-related tasks without UI dependencies.
"""

import os
import sys
import hashlib
import time
from datetime import datetime
from typing import List, Union, Optional, Iterator


def humansize(nbytes: Union[int, float]) -> str:
    """
    Convert bytes to human readable format.
    
    Args:
        nbytes: Number of bytes
        
    Returns:
        Human readable size string
    """
    suffixes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    nbytes = int(nbytes)
    i = 0
    while nbytes >= 1024 and i < len(suffixes) - 1:
        nbytes /= 1024.0
        i += 1
    f = ('%.2f' % nbytes).rstrip('0').rstrip('.')
    return f'{f} {suffixes[i]}'


def humandate(date: Union[int, float]) -> str:
    """
    Convert timestamp to human readable date.
    
    Args:
        date: Unix timestamp
        
    Returns:
        Human readable date string
    """
    return datetime.fromtimestamp(date).strftime("%Y-%m-%d %H:%M")


def second2hour(seconds: Union[int, float]) -> str:
    """
    Convert seconds to hours, minutes, seconds format.

    Args:
        seconds: Number of seconds

    Returns:
        Time string in format like "1h30m45s"
    """
    total_seconds = int(seconds)
    hour = total_seconds // 3600
    total_seconds = total_seconds % 3600
    minute = total_seconds // 60
    total_seconds = total_seconds % 60
    second = total_seconds

    ret_value = f"{second}s"
    if minute > 0 or hour > 0:  # Always show minutes if hours are present
        ret_value = f"{minute}m{ret_value}"
    if hour > 0:
        ret_value = f"{hour}h{ret_value}"
    return ret_value


def md5_file(filename: str) -> str:
    """
    Calculate MD5 hash of a file.
    
    Args:
        filename: Path to file
        
    Returns:
        MD5 hash as hexadecimal string
        
    Raises:
        FileNotFoundError: If file doesn't exist
        IOError: If file cannot be read
    """
    hash_md5 = hashlib.md5()
    try:
        with open(filename, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {filename}")
    except IOError as e:
        raise IOError(f"Cannot read file {filename}: {e}")


def xfrange(start: float, stop: float, steps: int) -> Iterator[float]:
    """
    Generate float range with specified number of steps.
    
    Args:
        start: Start value
        stop: Stop value
        steps: Number of steps
        
    Yields:
        Float values in the range
    """
    if steps <= 1:
        return
        
    interval = (stop - start) / (steps - 1)
    i = 0
    
    if interval == 0:
        for i in range(steps):
            yield start
    else:
        while start + i * interval <= stop:
            yield start + i * interval
            i += 1


def translate(value: float, left_min: float, left_max: float, 
              right_min: float, right_max: float) -> float:
    """
    Translate value from one range to another.
    
    Args:
        value: Value to translate
        left_min: Minimum of source range
        left_max: Maximum of source range
        right_min: Minimum of target range
        right_max: Maximum of target range
        
    Returns:
        Translated value
    """
    # Figure out how 'wide' each range is
    left_span = left_max - left_min
    right_span = right_max - right_min

    # Convert the left range into a 0-1 range (float)
    value_scaled = float(value - left_min) / float(left_span)

    # Convert the 0-1 range into a value in the right range
    return right_min + (value_scaled * right_span)


def digitize_version(version: str) -> int:
    """
    Convert version string to integer for comparison.

    Args:
        version: Version string like "1.2.3"

    Returns:
        Integer representation of version
    """
    if not version:
        return 0

    v_list = version.split('.')
    if len(v_list) >= 3:
        return int(v_list[0]) * 1000000 + int(v_list[1]) * 1000 + int(v_list[2])
    elif len(v_list) == 2:
        return int(v_list[0]) * 1000000 + int(v_list[1]) * 1000
    elif len(v_list) == 1 and v_list[0]:
        return int(v_list[0]) * 1000000
    else:
        return 0


def safe_float(value: str, default: float = 0.0) -> float:
    """
    Safely convert string to float.
    
    Args:
        value: String value to convert
        default: Default value if conversion fails
        
    Returns:
        Float value or default
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value: str, default: int = 0) -> int:
    """
    Safely convert string to integer.
    
    Args:
        value: String value to convert
        default: Default value if conversion fails
        
    Returns:
        Integer value or default
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def clamp(value: float, min_val: float, max_val: float) -> float:
    """
    Clamp value between minimum and maximum.
    
    Args:
        value: Value to clamp
        min_val: Minimum value
        max_val: Maximum value
        
    Returns:
        Clamped value
    """
    return max(min_val, min(value, max_val))


def find_serial_ports() -> List[str]:
    """
    Find available serial ports.
    
    Returns:
        List of available serial port names
    """
    ports = []
    
    # Try to use pyserial's list_ports if available
    try:
        import serial.tools.list_ports
        for port in serial.tools.list_ports.comports():
            ports.append(port.device)
        return ports
    except ImportError:
        pass
    
    # Fallback to manual detection
    locations = ['/dev/ttyACM', '/dev/ttyUSB', '/dev/ttyS', 'COM']
    
    for prefix in locations:
        for i in range(32):
            device = f"{prefix}{i}"
            try:
                # Check if device exists (Unix-like systems)
                if prefix.startswith('/dev/'):
                    os.stat(device)
                    ports.append(device)
                else:
                    # Windows COM ports - try to open
                    try:
                        import serial
                        s = serial.Serial(device)
                        s.close()
                        ports.append(device)
                    except:
                        pass
            except (OSError, ImportError):
                pass
    
    return ports


def validate_gcode_line(line: str) -> bool:
    """
    Validate if a line contains valid G-code.

    Args:
        line: G-code line to validate

    Returns:
        True if line appears to be valid G-code
    """
    if not line or not line.strip():
        return False

    line = line.strip().upper()

    # Skip comments
    if line.startswith('(') or line.startswith(';') or line.startswith('%'):
        return True

    # Check for G-code commands
    import re
    gcode_pattern = re.compile(r'^[GM]\d+')
    if gcode_pattern.match(line):
        return True

    # Check for coordinate commands (must have a number after the letter)
    coord_pattern = re.compile(r'^[XYZABCUVWIJK][-+]?\d+\.?\d*')
    if coord_pattern.match(line):
        return True

    # Check for other valid commands (must have a number after the letter)
    other_pattern = re.compile(r'^[FSTN]\d+')
    if other_pattern.match(line):
        return True

    # Check for special commands
    if line.startswith(('$', '?', '!', '~', '@')):
        return True

    return False


def parse_coordinate_string(coord_str: str) -> dict:
    """
    Parse coordinate string into dictionary.
    
    Args:
        coord_str: Coordinate string like "X10.5 Y20.3 Z5.0"
        
    Returns:
        Dictionary with coordinate values
    """
    coords = {}
    if not coord_str:
        return coords
        
    import re
    # Match patterns like X10.5, Y-20.3, etc.
    pattern = re.compile(r'([XYZABCUVWIJK])([-+]?\d*\.?\d*)')
    matches = pattern.findall(coord_str.upper())
    
    for axis, value in matches:
        try:
            coords[axis] = float(value)
        except ValueError:
            coords[axis] = 0.0
            
    return coords


class FileWatcher:
    """
    Simple file watcher to detect changes.
    """
    
    def __init__(self, filename: str):
        """
        Initialize file watcher.
        
        Args:
            filename: Path to file to watch
        """
        self.filename = filename
        self.last_modified = 0
        self.update_timestamp()
    
    def update_timestamp(self) -> None:
        """Update the last modified timestamp."""
        try:
            self.last_modified = os.path.getmtime(self.filename)
        except OSError:
            self.last_modified = 0
    
    def has_changed(self) -> bool:
        """
        Check if file has changed since last check.
        
        Returns:
            True if file has been modified
        """
        try:
            current_modified = os.path.getmtime(self.filename)
            if current_modified > self.last_modified:
                self.last_modified = current_modified
                return True
        except OSError:
            pass
        return False
