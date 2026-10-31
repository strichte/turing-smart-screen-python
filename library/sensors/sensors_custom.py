# SPDX-License-Identifier: GPL-3.0-or-later
#
# turing-smart-screen-python - a Python system monitor and library for USB-C displays like Turing Smart Screen or XuanFang
# https://github.com/mathoudebine/turing-smart-screen-python/
#
# Copyright (C) 2021 Matthieu Houdebine (mathoudebine)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# This file allows to add custom data source as sensors and display them in System Monitor themes
# There is no limitation on how much custom data source classes can be added to this file
# See CustomDataExample theme for the theme implementation part

import math
import os
import platform
from abc import ABC, abstractmethod
from typing import List


# Custom data classes must be implemented in this file, inherit the CustomDataSource and implement its 2 methods
class CustomDataSource(ABC):
    @abstractmethod
    def as_numeric(self) -> float:
        # Numeric value will be used for graph and radial progress bars
        # If there is no numeric value, keep this function empty
        pass

    @abstractmethod
    def as_string(self) -> str:
        # Text value will be used for text display and radial progress bar inner text
        # Numeric value can be formatted here to be displayed as expected
        # It is also possible to return a text unrelated to the numeric value
        # If this function is empty, the numeric value will be used as string without formatting
        pass

    @abstractmethod
    def last_values(self) -> List[float]:
        # List of last numeric values will be used for plot graph
        # If you do not want to draw a line graph or if your custom data has no numeric values, keep this function empty
        pass


class Vram(CustomDataSource):
    """Single-line GPU VRAM readout: 'VRAM <used> / <total> MB  <pct>%'."""

    def as_numeric(self) -> float:
        # Numeric = memory used % (usable for an optional progress/radial bar)
        # Reuse the SAME concrete sensors backend stats.py already selected.
        from library import stats
        _load, mem_pct, _used, _total, _temp = stats.sensors.Gpu.stats()
        return mem_pct

    def as_string(self) -> str:
        from library import stats
        _load, mem_pct, used_mb, total_mb, _temp = stats.sensors.Gpu.stats()
        # Guard against unsupported / missing GPU sensors
        if total_mb is None or used_mb is None or math.isnan(total_mb) or math.isnan(used_mb) or total_mb <= 0:
            return "VRAM: --"
        pct = 0 if (mem_pct is None or math.isnan(mem_pct)) else int(round(mem_pct))
        return f"VRAM: {int(round(used_mb))}/{int(round(total_mb))} MB  {pct}%"

    def last_values(self) -> List[float]:
        # No line graph for this stat
        return None


# Example for a custom data class that has numeric and text values
class ExampleCustomNumericData(CustomDataSource):
    # This list is used to store the last 10 values to display a line graph
    last_val = [math.nan] * 10  # By default, it is filed with math.nan values to indicate there is no data stored

    def as_numeric(self) -> float:
        # Numeric value will be used for graph and radial progress bars
        # Here a Python function from another module can be called to get data
        # Example: self.value = my_module.get_rgb_led_brightness() / audio.system_volume() ...
        self.value = 75.845

        # Store the value to the history list that will be used for line graph
        self.last_val.append(self.value)
        # Also remove the oldest value from history list
        self.last_val.pop(0)

        return self.value

    def as_string(self) -> str:
        # Text value will be used for text display and radial progress bar inner text.
        # Numeric value can be formatted here to be displayed as expected
        # It is also possible to return a text unrelated to the numeric value
        # If this function is empty, the numeric value will be used as string without formatting
        # Example here: format numeric value: add unit as a suffix, and keep 1 digit decimal precision
        return f'{self.value:>5.1f}%'
        # Important note! If your numeric value can vary in size, be sure to display it with a default size.
        # E.g. if your value can range from 0 to 9999, you need to display it with at least 4 characters every time.
        # --> return f'{self.as_numeric():>4}%'
        # Otherwise, part of the previous value can stay displayed ("ghosting") after a refresh

    def last_values(self) -> List[float]:
        # List of last numeric values will be used for plot graph
        return self.last_val


# Example for a custom data class that only has text values
class ExampleCustomTextOnlyData(CustomDataSource):
    def as_numeric(self) -> float:
        # If there is no numeric value, keep this function empty
        pass

    def as_string(self) -> str:
        # If a custom data class only has text values, it won't be possible to display graph or radial bars
        return "Python: " + platform.python_version()

    def last_values(self) -> List[float]:
        # If a custom data class only has text values, it won't be possible to display line graph
        pass


# ---------------------------------------------------------------------------
# WireView 2 Pro sensors (https://github.com/emaspa/wireview-hwmon)
#
# Reads the values exposed by the wireview-hwmon kernel driver through the
# standard Linux hwmon sysfs interface:
#     /sys/class/hwmon/hwmon<N>/  (device name "wireview")
#
# The hwmon number (hwmon7 right now) is NOT hardcoded: it can change after a
# reboot or if other hwmon devices are added/removed. The device is located
# by reading the "name" file of every hwmon directory until one named
# "wireview" is found.
#
# Sysfs attribute map (raw value -> physical unit), as exposed by the driver:
#   curr1_input .. curr6_input : Pin 1 .. Pin 6 current        (mA)
#   curr7_input                : Total current                 (mA)
#   in0_input .. in5_input     : Pin 1 .. Pin 6 voltage        (mV)
#   in6_input                  : Average voltage               (mV)
#   in7_input                  : Vdd voltage                   (mV)
#   power1_input               : Total power                   (uW)
#   power2_input .. power7_input: Pin 1 .. Pin 6 power         (uW)
#   temp1_input                : Onboard In temperature        (millideg C)
#   temp2_input                : Onboard Out temperature       (millideg C)
#   temp3_input                : External 1 temperature        (millideg C)
#   temp4_input                : External 2 temperature        (millideg C)
#   energy1_input              : Total energy                  (uJ, since
#                                  wireviewd daemon start)
#
# Each class below is a CustomDataSource and can be used in a theme by its
# class name (see STATS -> CUSTOM in config.yaml / the theme). The dashboard
# calls as_numeric(), as_string() and last_values() on an instance of the
# class. To expose more attributes (e.g. per-pin voltage/current/power),
# add another subclass following the same pattern.
# ---------------------------------------------------------------------------


HWMON_ROOT = "/sys/class/hwmon"
HWMON_NAME = "wireview"


def _find_wireview_hwmon_dir():
    """Return the sysfs directory of the wireview hwmon device, or None.

    Identifies the device by its "name" file so the code keeps working if the
    hwmon index changes (e.g. hwmon7 -> hwmon8 after a reboot).
    """
    try:
        for entry in os.listdir(HWMON_ROOT):
            if not entry.startswith("hwmon"):
                continue
            hwmon_dir = os.path.join(HWMON_ROOT, entry)
            try:
                with open(os.path.join(hwmon_dir, "name"), "r") as f:
                    if f.read().strip() == HWMON_NAME:
                        return hwmon_dir
            except (OSError, ValueError):
                continue
    except OSError:
        pass
    return None


def _read_wireview_attr(attr):
    """Read a hwmon attribute file and return its value as float, or None."""
    hwmon_dir = _find_wireview_hwmon_dir()
    if hwmon_dir is None:
        return None
    try:
        with open(os.path.join(hwmon_dir, attr), "r") as f:
            return float(f.read().strip())
    except (OSError, ValueError):
        return None


class WireviewDataSource(CustomDataSource):
    """Base class for WireView 2 Pro sensors reading a single sysfs attribute.

    Subclass and set attr/scale/unit/fmt. The hwmon value is read on every
    call to as_numeric(); when the device is unavailable math.nan is
    returned so graphs/radial bars are skipped and "n/a" is shown as text.
    """

    # sysfs attribute file to read, e.g. "power1_input"
    attr = None
    # Multiplier applied to the raw sysfs value to get the physical unit
    scale = 1.0
    # Unit suffix shown in as_string()
    unit = ""
    # Optional label prepended to as_string() output (e.g. "Cable Temp", "Pin 1")
    label = ""
    # Format for as_string(); {value} and {unit} are replaced
    fmt = "{value:>8.2f}{unit}"
    # Field width used for the "n/a" fallback; keep it equal to the value
    # field width of fmt so no ghost characters remain on error
    null_width = 8

    # Rolling history of the last numeric values, used for line graphs.
    # Each subclass gets its own list (via __init_subclass__) so histories
    # are not shared between different sensors.
    last_val = [math.nan] * 10

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.last_val = [math.nan] * 10

    def __init__(self):
        self.value = math.nan

    def as_numeric(self) -> float:
        raw = _read_wireview_attr(self.attr)
        self.value = raw * self.scale if raw is not None else math.nan

        # Store the value to the history list that will be used for line graph
        self.last_val.append(self.value)
        # Also remove the oldest value from history list
        self.last_val.pop(0)

        return self.value

    def as_string(self) -> str:
        # Text value used for text display and radial progress bar inner text
        if math.isnan(self.value):
            return f"{'n/a':>{self.null_width}}{self.unit}"
        text = self.fmt.format(value=self.value, unit=self.unit)
        if self.label:
            text = f"{self.label} {text}"
        return text

    def last_values(self) -> List[float]:
        # List of last numeric values will be used for plot graph
        return self.last_val
class WireviewTotalPower(WireviewDataSource):
    """Total GPU power (power1_input: Total) in watts."""
    attr = "power1_input"
    scale = 0.000001   # uW -> W
    unit = "W"
    label = ""         # set to "Total Power" to re-enable the text prefix
    fmt = "{value:.0f}{unit}"


class WireviewTotalCurrent(WireviewDataSource):
    """Total current (curr7_input: Total) in amperes."""
    attr = "curr7_input"
    scale = 0.001      # mA -> A
    unit = "A"
    fmt = "{value:>8.2f}{unit}"


class WireviewCurrentPin1(WireviewDataSource):
    """Pin 1 current (curr1_input) in amperes."""
    attr = "curr1_input"
    scale = 0.001      # mA -> A
    unit = "A"
    label = "1:"
    fmt = "{value:.2f}{unit}"


class WireviewCurrentPin2(WireviewDataSource):
    """Pin 2 current (curr2_input) in amperes."""
    attr = "curr2_input"
    scale = 0.001      # mA -> A
    unit = "A"
    label = "2:"
    fmt = "{value:.2f}{unit}"


class WireviewCurrentPin3(WireviewDataSource):
    """Pin 3 current (curr3_input) in amperes."""
    attr = "curr3_input"
    scale = 0.001      # mA -> A
    unit = "A"
    label = "3:"
    fmt = "{value:.2f}{unit}"


class WireviewCurrentPin4(WireviewDataSource):
    """Pin 4 current (curr4_input) in amperes."""
    attr = "curr4_input"
    scale = 0.001      # mA -> A
    unit = "A"
    label = "4:"
    fmt = "{value:.2f}{unit}"


class WireviewCurrentPin5(WireviewDataSource):
    """Pin 5 current (curr5_input) in amperes."""
    attr = "curr5_input"
    scale = 0.001      # mA -> A
    unit = "A"
    label = "5:"
    fmt = "{value:.2f}{unit}"


class WireviewCurrentPin6(WireviewDataSource):
    """Pin 6 current (curr6_input) in amperes."""
    attr = "curr6_input"
    scale = 0.001      # mA -> A
    unit = "A"
    label = "6:"
    fmt = "{value:.2f}{unit}"


# --- Bargraph variants of the per-pin current sensors (in milliamps) ---------
# display_themed_progress_bar() casts its value to int() before drawing, which
# zeroes sub-ampere readings (0.25 A -> 0). These variants return the raw sysfs
# value unchanged in milliamps (scale 1.0), so the integer cast is harmless
# (250 mA stays 250). Wire the per-pin GRAPH widgets to these classes and keep
# the TEXT widgets on the ampere classes above. The bar MAX_VALUE is therefore
# expressed in milliamps (e.g. 1000 mA == the original 0..1 A range).
class WireviewCurrentPin1mA(WireviewDataSource):
    """Pin 1 current (curr1_input) in milliamps - for bargraph display."""
    attr = "curr1_input"
    scale = 1.0          # mA -> mA
    unit = "mA"
    label = "1:"
    fmt = "{value:>6.1f}{unit}"
    null_width = 6


class WireviewCurrentPin2mA(WireviewDataSource):
    """Pin 2 current (curr2_input) in milliamps - for bargraph display."""
    attr = "curr2_input"
    scale = 1.0          # mA -> mA
    unit = "mA"
    label = "2:"
    fmt = "{value:>6.1f}{unit}"
    null_width = 6


class WireviewCurrentPin3mA(WireviewDataSource):
    """Pin 3 current (curr3_input) in milliamps - for bargraph display."""
    attr = "curr3_input"
    scale = 1.0          # mA -> mA
    unit = "mA"
    label = "3:"
    fmt = "{value:>6.1f}{unit}"
    null_width = 6


class WireviewCurrentPin4mA(WireviewDataSource):
    """Pin 4 current (curr4_input) in milliamps - for bargraph display."""
    attr = "curr4_input"
    scale = 1.0          # mA -> mA
    unit = "mA"
    label = "4:"
    fmt = "{value:>6.1f}{unit}"
    null_width = 6


class WireviewCurrentPin5mA(WireviewDataSource):
    """Pin 5 current (curr5_input) in milliamps - for bargraph display."""
    attr = "curr5_input"
    scale = 1.0          # mA -> mA
    unit = "mA"
    label = "5:"
    fmt = "{value:>6.1f}{unit}"
    null_width = 6


class WireviewCurrentPin6mA(WireviewDataSource):
    """Pin 6 current (curr6_input) in milliamps - for bargraph display."""
    attr = "curr6_input"
    scale = 1.0          # mA -> mA
    unit = "mA"
    label = "6:"
    fmt = "{value:>6.1f}{unit}"
    null_width = 6


class WireviewAverageVoltage(WireviewDataSource):
    """Average voltage (in6_input: Average) in volts."""
    attr = "in6_input"
    scale = 0.001      # mV -> V
    unit = "V"
    fmt = "{value:>8.3f}{unit}"


class WireviewVddVoltage(WireviewDataSource):
    """Vdd supply voltage (in7_input: Vdd) in volts."""
    attr = "in7_input"
    scale = 0.001      # mV -> V
    unit = "V"
    fmt = "{value:>8.3f}{unit}"


class WireviewTempOnboardIn(WireviewDataSource):
    """Onboard In temperature (temp1_input) in degrees Celsius."""
    attr = "temp1_input"
    scale = 0.001      # millideg C -> deg C
    unit = "°C"
    fmt = "{value:>8.1f}{unit}"


class WireviewTempOnboardOut(WireviewDataSource):
    """Onboard Out temperature (temp2_input) in degrees Celsius."""
    attr = "temp2_input"
    scale = 0.001      # millideg C -> deg C
    unit = "°C"
    fmt = "{value:>8.1f}{unit}"


class WireviewTempExternal1(WireviewDataSource):
    """External 1 temperature (temp3_input) in degrees Celsius."""
    attr = "temp3_input"
    scale = 0.001      # millideg C -> deg C
    unit = "°C"
    label = ""
    fmt = "{value:.0f}{unit}"


class WireviewTempExternal2(WireviewDataSource):
    """External 2 temperature (temp4_input) in degrees Celsius."""
    attr = "temp4_input"
    scale = 0.001      # millideg C -> deg C
    unit = "°C"
    label = ""
    fmt = "{value:.0f}{unit}"


class WireviewTotalEnergy(WireviewDataSource):
    """Total energy (energy1_input: Total) in watt-hours.

    The counter is monotonic since the wireviewd daemon start.
    """
    attr = "energy1_input"
    scale = 1.0 / 3600000000.0   # uJ -> Wh
    unit = "Wh"
    fmt = "{value:>10.2f}{unit}"
    null_width = 10
