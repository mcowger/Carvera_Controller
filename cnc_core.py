"""
CNC Core Module - G-code parsing and CNC state management.

This module provides the core functionality for parsing G-code commands,
managing CNC machine state, and calculating tool paths.
"""

import math
import re
import logging
from typing import List, Tuple, Optional, Dict, Any, Union

# Regular expressions for G-code parsing
PARENPAT = re.compile(r"(\(.*?\))")
SEMIPAT = re.compile(r"(;.*)")
CMDPAT = re.compile(r"([A-Za-z]+)")

# Plane constants
XY = 0
XZ = 1
YZ = 2


class CNCError(Exception):
    """Base exception class for CNC-related errors."""

    pass


class GCodeParseError(CNCError):
    """Exception raised when G-code parsing fails."""

    pass


class CNC:
    """
    CNC machine state and G-code parser.

    This class manages the state of a CNC machine and provides functionality
    to parse G-code commands and calculate tool paths.
    """

    # Machine configuration
    has_4axis = False
    inch = False
    travel_x = 340
    travel_y = 240
    travel_z = 140
    feedmax_x = 3000
    feedmax_y = 3000
    feedmax_z = 2000
    feedmax_a = 2000
    accuracy = 0.01  # sagitta error during arc conversion
    digits = 4
    startup = "G90"
    stdexpr = False  # standard way of defining expressions with []
    comment = ""  # last parsed comment
    developer = False
    drozeropad = 0
    curr_tool = 0
    coordinates = []  # list of coordinates

    # Laser module offsets
    laser_names = ["laser_module_offset_x", "laser_module_offset_y"]

    # Coordinate system names
    coord_names = [
        "anchor1_x",
        "anchor1_y",
        "anchor2_offset_x",
        "anchor2_offset_y",
        "anchor_width",
        "anchor_length",
        "worksize_x",
        "worksize_y",
        "rotation_offset_x",
        "rotation_offset_y",
    ]

    # Machine variables and state
    vars: Dict[str, Union[float, int, str, List]] = {
        # Probe variables
        "prbx": 0.0,
        "prby": 0.0,
        "prbz": 0.0,
        "prbcmd": "G38.2",
        "prbfeed": 10.0,
        "errline": "",
        # Work coordinates
        "wx": 0.0,
        "wy": 0.0,
        "wz": 0.0,
        "wa": 0.0,
        # Machine coordinates
        "mx": 0.0,
        "my": 0.0,
        "mz": 0.0,
        "ma": 0.0,
        # Work coordinate offsets
        "wcox": 0.0,
        "wcoy": 0.0,
        "wcoz": 0.0,
        # Feed and spindle
        "curfeed": 0.0,
        "curspindle": 0.0,
        "spindletemp": 0.0,
        "tarfeed": 0.0,
        "tarspindle": 0.0,
        # Laser settings
        "lasermode": 0,
        "laserstate": 0,
        "lasertesting": 0,
        "laserpower": 0.0,
        "laserscale": 0.0,
        "laser_module_offset_x": -37.3,
        "laser_module_offset_y": 4.8,
        # Motion settings
        "max_delta": 0.0,
        "_camwx": 0.0,
        "_camwy": 0.0,
        "G": [],
        "motion": "G0",
        "WCS": "G54",
        "plane": "G17",
        "feedmode": "G94",
        "distance": "G90",
        "arc": "G91.1",
        "units": "G20",
        "cutter": "",
        "tlo": 0.0,
        "target_tool": -1,
        "program": "M0",
        "spindle": "M5",
        "coolant": "M9",
        # Playback status
        "playedlines": 0,
        "playedpercent": 0,
        "playedseconds": 0,
        # Tool changer
        "atc_state": 0,
        "tool": 0,
        "feed": 0.0,
        "rpm": 0.0,
        # System status
        "wpvoltage": 0.0,
        "halt_reason": 1,
        "planner": 0,
        "rxbytes": 0,
        # Override settings
        "OvFeed": 100,
        "OvRapid": 100,
        "OvSpindle": 100,
        "vacuummode": 0,
        "_OvChanged": False,
        "_OvFeed": 100,
        "_OvRapid": 100,
        "_OvSpindle": 100,
        # System info
        "version": "",
        "running": False,
        # Basic coordinates
        "anchor1_x": -360.158,
        "anchor1_y": -234.568,
        "anchor2_offset_x": 90.0,
        "anchor2_offset_y": 45,
        "anchor_width": 15.0,
        "anchor_length": 100.0,
        "worksize_x": 340.0,
        "worksize_y": 240.0,
        "clearance_x": -75.0,
        "clearance_y": -3.0,
        "clearance_z": -3.0,
        # Rotation coordinates
        "rotation_base_width": 330.0,
        "rotation_base_height": 102.5,
        "rotation_head_width": 7.0,
        "rotation_head_height": 102.5,
        "rotation_chuck_dia": 50.0,
        "rotation_chuck_interval": 4.0,
        "rotation_chuck_width": 40.0,
        "rotation_tail_width": 70.0,
        "rotation_tail_height": 30.0,
        "rotation_offset_x": -8.0,
        "rotation_offset_y": 37.5,
        "rotation_offset_z": 22.5,
        # Diagnostic states - switches
        "sw_spindle": 0,
        "sw_spindlefan": 0,
        "sw_vacuum": 0,
        "sw_light": 0,
        "sw_tool_sensor_pwr": 0,
        "sw_air": 0,
        "sw_wp_charge_pwr": 0,
        # Diagnostic states - sensors/lights
        "sl_spindle": 0,
        "sl_spindlefan": 0,
        "sl_vacuum": 0,
        "sl_laser": 0,
        # Diagnostic states - status
        "st_x_min": 0,
        "st_x_max": 0,
        "st_y_min": 0,
        "st_y_max": 0,
        "st_z_max": 0,
        "st_atc_home": 0,
        "st_probe": 0,
        "st_calibrate": 0,
        "st_cover": 0,
        "st_tool_sensor": 0,
        "st_e_stop": 0,
    }

    def __init__(self):
        """Initialize CNC instance."""
        self.logger = logging.getLogger(__name__)
        self.init()

    def __getitem__(self, name: str) -> Any:
        """Get a CNC variable value."""
        return CNC.vars[name]

    def __setitem__(self, name: str, value: Any) -> None:
        """Set a CNC variable value."""
        CNC.vars[name] = value

    def init_path(
        self,
        x: Optional[float] = None,
        y: Optional[float] = None,
        z: Optional[float] = None,
        a: Optional[float] = None,
    ) -> None:
        """
        Initialize path tracking variables.

        Args:
            x: Initial X position
            y: Initial Y position
            z: Initial Z position
            a: Initial A (rotary) position
        """
        self.x = self.xval = 0 if x is None else x
        self.y = self.yval = 0 if y is None else y
        self.z = self.zval = 0 if z is None else z
        self.a = self.aval = 0 if a is None else a
        self.ival = self.jval = self.kval = 0.0
        self.uval = self.vval = self.wval = 0.0
        self.dx = self.dy = self.dz = self.da = 0.0
        self.di = self.dj = self.dk = 0.0
        self.rval = 0.0
        self.pval = 0.0
        self.qval = 0.0
        self.unit = 1.0
        self.mval = 0
        self.lval = 1
        self.tool = 0

        self.absolute = True  # G90/G91 absolute/relative motion
        self.arcabsolute = False  # G90.1/G91.1 absolute/relative arc
        self.retractz = True  # G98/G99 retract to Z or R
        self.gcode = None
        self.plane = XY
        self.feed = 0  # Actual gcode feed rate
        self.speed = 0  # Spindle RPM
        self.totalLength = 0.0
        self.totalTime = 0.0
        self.coordinates = []
        self.last_xyz = (-10000, -10000, -10000)

    def reset_margins(self) -> None:
        """Reset the bounding box margins to initial values."""
        CNC.vars["xmin"] = CNC.vars["ymin"] = CNC.vars["zmin"] = 1000000.0
        CNC.vars["xmax"] = CNC.vars["ymax"] = CNC.vars["zmax"] = -1000000.0

    def init(self, filename: Optional[str] = None) -> None:
        """
        Initialize CNC state.

        Args:
            filename: Optional filename for initialization context
        """
        self.has_4axis = False
        self.init_path()
        self.reset_margins()

    def parse_line(
        self, line: str, line_no: int
    ) -> Optional[List[Tuple[float, float, float, float]]]:
        """
        Parse a single line of G-code and return the resulting coordinates.

        Args:
            line: G-code line to parse
            line_no: Line number for tracking

        Returns:
            List of coordinate tuples (x, y, z, a) or None if line is empty/comment

        Raises:
            GCodeParseError: If parsing fails
        """
        # Skip empty lines and comments
        if len(line) == 0 or line[0] in ("%", "(", "#", ";"):
            self.logger.debug(f"Line {line_no}: Skipping comment/empty line: {line!r}")
            return None

        try:
            original_line = line
            self.logger.debug(f"Line {line_no}: Parsing G-code: {original_line!r}")

            # Remove comments
            line = PARENPAT.sub("", line)
            line = SEMIPAT.sub("", line)
            # Remove spaces
            line = line.replace(" ", "")
            # Insert space before each command
            line = CMDPAT.sub(r" \1", line).lstrip()
            cmds = line.split()
            if not cmds:
                self.logger.debug(f"Line {line_no}: No commands after preprocessing")
                return None

            self.logger.debug(f"Line {line_no}: Parsed commands: {cmds}")

            # Start motion
            self._motion_start(cmds)

            # Calculate path
            xyzs = self._motion_path()

            if len(xyzs) > 0:
                self.logger.debug(
                    f"Line {line_no}: Generated {len(xyzs)} coordinate points"
                )
                for xyz in xyzs:
                    if xyz != self.last_xyz:
                        self.last_xyz = xyz
                        self.coordinates.append(
                            [
                                xyz[0],
                                xyz[1],
                                xyz[2],
                                xyz[3],
                                0 if self.gcode == 0 or self.speed < 0.001 else 1,
                                line_no,
                                self.tool,
                            ]
                        )

                if self.gcode != 0:
                    self._path_margins(xyzs)
            else:
                self.logger.debug(f"Line {line_no}: No coordinate points generated")

            # End motion
            self._motion_end()

            self.logger.info(f"Line {line_no}: Successfully parsed G-code command")
            return xyzs

        except Exception as e:
            # For invalid G-code, return empty list instead of raising exception
            # This allows the system to continue processing other lines
            self.logger.error(
                f"Line {line_no}: G-code parsing failed for '{original_line}': {e}"
            )
            return []

    def _motion_start(self, cmds: List[str]) -> None:
        """
        Process motion commands and update internal state.

        Args:
            cmds: List of G-code commands
        """
        self.mval = 0  # reset m command
        for cmd in cmds:
            c = cmd[0].upper()
            try:
                value = float(cmd[1:])
            except (ValueError, IndexError):
                value = 0

            if c == "X":
                self.xval = value * self.unit
                if not self.absolute:
                    self.xval += self.x
                self.dx = self.xval - self.x

            elif c == "Y":
                self.yval = value * self.unit
                if not self.absolute:
                    self.yval += self.y
                self.dy = self.yval - self.y

            elif c == "Z":
                self.zval = value * self.unit
                if not self.absolute:
                    self.zval += self.z
                self.dz = self.zval - self.z

            elif c == "A":
                self.has_4axis = True
                # Right Hand Rule rotation. A+ movement when looking at rotary jaws is CCW rotation
                self.aval = value * self.unit * -1
                if not self.absolute:
                    self.aval += self.a
                self.da = self.aval - self.a

            elif c == "F":
                self.feed = value * self.unit

            elif c == "S":
                self.speed = value

            elif c == "G":
                self._process_g_code(int(value), value)

            elif c == "I":
                self.ival = value * self.unit
                if self.arcabsolute:
                    self.ival -= self.x

            elif c == "J":
                self.jval = value * self.unit
                if self.arcabsolute:
                    self.jval -= self.y

            elif c == "K":
                self.kval = value * self.unit
                if self.arcabsolute:
                    self.kval -= self.z

            elif c == "L":
                self.lval = int(value)

            elif c == "M":
                self.mval = int(value)
                if self.mval == 321:
                    self.tool = 7  # laser is 7

            elif c == "N":
                pass  # Line number, ignore

            elif c == "P":
                self.pval = value

            elif c == "Q":
                self.qval = value * self.unit

            elif c == "R":
                self.rval = value * self.unit

            elif c == "T":
                self.tool = int(value)

            elif c in ("U", "V", "W"):
                # Additional axis values
                if c == "U":
                    self.uval = value * self.unit
                elif c == "V":
                    self.vval = value * self.unit
                elif c == "W":
                    self.wval = value * self.unit

    def _process_g_code(self, gcode: int, value: float) -> None:
        """
        Process G-code commands.

        Args:
            gcode: G-code number
            value: Full G-code value (for decimal processing)
        """
        decimal = int(round((value - gcode) * 10))

        # Execute immediately
        if gcode in (4, 10, 53, 54, 55, 56, 57, 58, 59):
            pass  # do nothing but don't record to motion
        elif gcode == 17:
            self.plane = XY
        elif gcode == 18:
            self.plane = XZ
        elif gcode == 19:
            self.plane = YZ
        elif gcode == 20:  # Switch to inches
            if CNC.inch:
                self.unit = 1.0
            else:
                self.unit = 25.4
        elif gcode == 21:  # Switch to mm
            if CNC.inch:
                self.unit = 1.0 / 25.4
            else:
                self.unit = 1.0
        elif gcode == 80:
            # turn off canned cycles
            self.gcode = None
            self.dz = 0
            self.zval = self.z
        elif gcode == 90:
            if decimal == 0:
                self.absolute = True
            elif decimal == 1:
                self.arcabsolute = True
        elif gcode == 91:
            if decimal == 0:
                self.absolute = False
            elif decimal == 1:
                self.arcabsolute = False
        elif gcode in (93, 94, 95):
            CNC.vars["feedmode"] = gcode
        elif gcode == 98:
            self.retractz = True
        elif gcode == 99:
            self.retractz = False
        else:
            self.gcode = gcode

    def _motion_center(self) -> Tuple[float, float]:
        """
        Calculate center coordinates for arc motions (G02/G03).

        Returns:
            Tuple of center coordinates (x, y)
        """
        if self.rval > 0.0:
            if self.plane == XY:
                x, y = self.x, self.y
                xv, yv = self.xval, self.yval
            elif self.plane == XZ:
                x, y = self.x, self.z
                xv, yv = self.xval, self.zval
            else:
                x, y = self.y, self.z
                xv, yv = self.yval, self.zval

            ABx = xv - x
            ABy = yv - y
            Cx = 0.5 * (x + xv)
            Cy = 0.5 * (y + yv)
            AB = math.sqrt(ABx**2 + ABy**2)
            try:
                OC = math.sqrt(self.rval**2 - AB**2 / 4.0)
            except ValueError:
                OC = 0.0
            if self.gcode == 2:
                OC = -OC  # CW
            if AB != 0.0:
                return Cx - OC * ABy / AB, Cy + OC * ABx / AB
            else:
                # Error case
                return x, y
        else:
            # Center using I, J, K values
            xc = self.x + self.ival
            yc = self.y + self.jval
            zc = self.z + self.kval
            self.rval = math.sqrt(self.ival**2 + self.jval**2 + self.kval**2)

            if self.plane == XY:
                return xc, yc
            elif self.plane == XZ:
                return xc, zc
            else:
                return yc, zc

    def _motion_path(self) -> List[Tuple[float, float, float, float]]:
        """
        Calculate the path for the current G-code command.

        Returns:
            List of coordinate tuples (x, y, z, a) representing the path
        """
        xyz = []

        # Execute g-code
        if self.gcode in (0, 1):  # fast move or line
            # If any axis is moving, interpolate all axes including A
            if self.dx != 0.0 or self.dy != 0.0 or self.dz != 0.0 or self.da != 0.0:
                # Determine the number of interpolation steps based on the largest movement
                max_delta = max(abs(self.dx), abs(self.dy), abs(self.dz), abs(self.da))
                steps = max(
                    int(max_delta / 0.5), 1
                )  # 0.5 is resolution, adjust as needed
                for i in range(1, steps + 1):
                    t = i / steps
                    x = self.x + t * self.dx
                    y = self.y + t * self.dy
                    z = self.z + t * self.dz
                    a = self.a + t * self.da
                    xyz.append((x, y, z, a))

        elif self.gcode in (2, 3):  # CW = 2, CCW = 3 circle
            uc, vc = self._motion_center()
            xyz.extend(self._calculate_arc_path(uc, vc))

        elif self.gcode == 4:  # Dwell
            pass  # No movement for dwell

        elif self.gcode in (81, 82, 83, 85, 86, 89):  # Canned cycles
            xyz.extend(self._calculate_canned_cycle_path())

        return xyz

    def _calculate_arc_path(
        self, uc: float, vc: float
    ) -> List[Tuple[float, float, float, float]]:
        """
        Calculate path for arc movements (G02/G03).

        Args:
            uc: Center U coordinate
            vc: Center V coordinate

        Returns:
            List of coordinate tuples for the arc path
        """
        xyz = []
        gcode = self.gcode

        if self.plane == XY:
            u0, v0, w0, a0 = self.x, self.y, self.z, self.a
            u1, v1, w1, a1 = self.xval, self.yval, self.zval, self.aval
        elif self.plane == XZ:
            u0, v0, w0, a0 = self.x, self.z, self.y, self.a
            u1, v1, w1, a1 = self.xval, self.zval, self.yval, self.aval
            gcode = 5 - gcode  # flip 2-3 when XZ plane is used
        else:
            u0, v0, w0, a0 = self.y, self.z, self.x, self.a
            u1, v1, w1, a1 = self.yval, self.zval, self.xval, self.aval

        phi0 = math.atan2(v0 - vc, u0 - uc)
        phi1 = math.atan2(v1 - vc, u1 - uc)

        try:
            sagitta = 1.0 - CNC.accuracy / self.rval
        except ZeroDivisionError:
            sagitta = 0.0

        if sagitta > 0.0:
            df = 2.0 * math.acos(sagitta)
            df = min(df, math.pi / 4.0)
        else:
            df = math.pi / 4.0

        # Interpolate A axis
        da = a1 - a0
        dphi = phi1 - phi0 if (phi1 - phi0) != 0 else 1e-9  # avoid division by zero

        if gcode == 2:  # CW
            if phi1 >= phi0 - 1e-10:
                phi1 -= 2.0 * math.pi
            ws = (w1 - w0) / (phi1 - phi0)
            as_ = da / (phi1 - phi0)
            phi = phi0 - df
            while phi > phi1:
                u = uc + self.rval * math.cos(phi)
                v = vc + self.rval * math.sin(phi)
                w = w0 + (phi - phi0) * ws
                a = a0 + (phi - phi0) * as_
                if self.plane == XY:
                    xyz.append((u, v, w, a))
                elif self.plane == XZ:
                    xyz.append((u, w, v, a))
                else:
                    xyz.append((w, u, v, a))
                phi -= df
        else:  # CCW
            if phi1 <= phi0 + 1e-10:
                phi1 += 2.0 * math.pi
            ws = (w1 - w0) / (phi1 - phi0)
            as_ = da / (phi1 - phi0)
            phi = phi0 + df
            while phi < phi1:
                u = uc + self.rval * math.cos(phi)
                v = vc + self.rval * math.sin(phi)
                w = w0 + (phi - phi0) * ws
                a = a0 + (phi - phi0) * as_
                if self.plane == XY:
                    xyz.append((u, v, w, a))
                elif self.plane == XZ:
                    xyz.append((u, w, v, a))
                else:
                    xyz.append((w, u, v, a))
                phi += df

        xyz.append((self.xval, self.yval, self.zval, self.aval))
        return xyz

    def _calculate_canned_cycle_path(self) -> List[Tuple[float, float, float, float]]:
        """
        Calculate path for canned cycles (drilling operations).

        Returns:
            List of coordinate tuples for the canned cycle path
        """
        xyz = []

        # FIXME: Assuming only on plane XY
        if self.absolute:
            self.lval = 1
            if self.retractz:
                clearz = max(self.rval, self.z)
            else:
                clearz = self.rval
            drill = self.zval
        else:
            clearz = self.z + self.rval
            drill = clearz + self.dz

        x, y, z, a = self.x, self.y, self.z, self.a
        xyz.append((x, y, z, a))

        if z != clearz:
            z = clearz
            xyz.append((x, y, z, a))

        for l in range(self.lval):
            # Rapid move parallel to XY
            x += self.dx
            y += self.dy
            xyz.append((x, y, z, a))

            # Rapid move parallel to clearz
            if self.z > clearz:
                xyz.append((x, y, clearz, a))

            # Drill to z
            xyz.append((x, y, drill, a))

            # Move to original position
            z = clearz
            xyz.append((x, y, z, a))

        return xyz

    def _motion_end(self) -> None:
        """Update position after motion is complete."""
        if self.gcode in (0, 1, 2, 3):
            self.x = self.xval
            self.y = self.yval
            self.z = self.zval
            self.a = self.aval
            self.dx = 0
            self.dy = 0
            self.dz = 0
            self.da = 0
            if self.gcode >= 2:  # reset at the end
                self.rval = self.ival = self.jval = self.kval = 0.0

        elif self.gcode in (28, 30, 92):
            self.x = 0.0
            self.y = 0.0
            self.z = 0.0
            self.a = 0.0
            self.dx = 0
            self.dy = 0
            self.dz = 0
            self.da = 0

        elif self.gcode in (81, 82, 83):
            # FIXME: Assuming only on plane XY
            if self.absolute:
                self.lval = 1
                if self.retractz:
                    retract = max(self.rval, self.z)
                else:
                    retract = self.rval
                drill = self.zval
            else:
                retract = self.z + self.rval
                drill = retract + self.dz

            self.x += self.dx * self.lval
            self.y += self.dy * self.lval
            self.z = retract

            self.xval = self.x
            self.yval = self.y
            self.dx = 0
            self.dy = 0
            self.dz = drill - retract

    def _path_margins(self, xyzs: List[Tuple[float, float, float, float]]) -> None:
        """
        Update bounding box margins based on path coordinates.

        Args:
            xyzs: List of coordinate tuples
        """
        for xyz in xyzs:
            CNC.vars["xmin"] = min(CNC.vars["xmin"], xyz[0])
            CNC.vars["xmax"] = max(CNC.vars["xmax"], xyz[0])
            CNC.vars["ymin"] = min(CNC.vars["ymin"], xyz[1])
            CNC.vars["ymax"] = max(CNC.vars["ymax"], xyz[1])
            CNC.vars["zmin"] = min(CNC.vars["zmin"], xyz[2])
            CNC.vars["zmax"] = max(CNC.vars["zmax"], xyz[2])

    def get_margins(self) -> Tuple[float, float, float, float, float, float]:
        """
        Get the current bounding box margins.

        Returns:
            Tuple of (xmin, ymin, zmin, xmax, ymax, zmax)
        """
        return (
            CNC.vars["xmin"],
            CNC.vars["ymin"],
            CNC.vars["zmin"],
            CNC.vars["xmax"],
            CNC.vars["ymax"],
            CNC.vars["zmax"],
        )
