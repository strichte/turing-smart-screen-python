# WireView 2 Pro integration — turing-smart-screen-python

This document describes how the **Thermal Grizzly WireView Pro II** power monitor
sensors were added to the `turing-smart-screen-python` dashboard, following
[Step 1 of the System Monitor custom-stats guide](https://github.com/mathoudebine/turing-smart-screen-python/wiki/System-monitor-:-themes#add-custom-stats-to-a-theme).

## Hardware / data source

- Sensor data is provided by [`emaspa/wireview-hwmon`](https://github.com/emaspa/wireview-hwmon)
  (kernel module + `wireviewd` daemon), already installed and confirmed working.
- The driver exposes a `wireview` hwmon device under `/sys/class/hwmon/hwmon<N>/`.
- On this install the device is `hwmon7`, but **the hwmon index can change** after a
  reboot or if other hwmon devices are added/removed. The code therefore locates the
  device by reading the `name` file of every `hwmon*` directory until one named
  `wireview` is found — the index `7` is **not** hardcoded.

## What was added

File: `library/sensors/sensors_custom.py`

All new classes inherit `CustomDataSource` and can be used in a theme by their exact
class name under `STATS -> CUSTOM` in `theme.yaml`. The dashboard (`library/stats.py`,
`Custom.stats()`) instantiates each class via
`getattr(sensors_custom, <class_name>)()` and calls `as_numeric()`, `as_string()` and
`last_values()`.

### New sensor classes

| Class | Sysfs attribute | Unit | What it shows |
|---|---|---|---|
| `WireviewTotalPower` | `power1_input` | W | Total GPU power |
| `WireviewTotalCurrent` | `curr7_input` | A | Total current |
| `WireviewCurrentPin1` … `WireviewCurrentPin6` | `curr1_input` … `curr6_input` | A | Per-pin current (Pin 1 … Pin 6) |
| `WireviewAverageVoltage` | `in6_input` | V | Average voltage |
| `WireviewVddVoltage` | `in7_input` | V | Vdd supply voltage |
| `WireviewTempOnboardIn` | `temp1_input` | °C | Onboard In temperature |
| `WireviewTempOnboardOut` | `temp2_input` | °C | Onboard Out temperature |
| `WireviewTempExternal1` | `temp3_input` | °C | External 1 temperature |
| `WireviewTempExternal2` | `temp4_input` | °C | External 2 temperature |
| `WireviewTotalEnergy` | `energy1_input` | Wh | Total energy (since daemon start) |

### Design notes

- **Dynamic hwmon discovery**: `_find_wireview_hwmon_dir()` scans `/sys/class/hwmon/`
  and matches on the `name` file (`wireview`), so the theme keeps working if the
  index changes (e.g. `hwmon7` → `hwmon8`).
- **Graceful degradation**: if the device or an attribute is unavailable,
  `as_numeric()` returns `math.nan` and `as_string()` returns a fixed-width `"n/a"`.
  `stats.py` already skips graphs/radials for `nan`, so the dashboard does not break
  when the WireView device is temporarily absent.
- **`label` attribute**: the base `WireviewDataSource` supports an optional `label`
  that is prepended to `as_string()`. It is used to label the two external
  temperatures ("Cable Temp" / "Case Temp") and per-pin currents ("Pin 1" … "Pin 6").
- **Fixed-width formatting**: every `as_string()` uses a fixed field width so no
  "ghost" characters remain on screen after a refresh (a called-out pitfall in the
  example classes).
- Each subclass maintains its own rolling 10-value history (`last_val`) for line
  graphs.

## Raw sysfs → physical unit scaling

(as exposed by the `wireview-hwmon` driver)

- Current (`curr*`): milliamps → divide by 1 000 for amps
- Voltage (`in*`): millivolts → divide by 1 000 for volts
- Power (`power*`): microwatts → divide by 1 000 000 for watts
- Temperature (`temp*`): millidegrees C → divide by 1 000 for °C
- Energy (`energy1`): microjoules → divide by 3 600 000 000 for Wh

## Using the sensors in a theme

Add a `CUSTOM` block to your theme's `theme.yaml` (the refresh `INTERVAL` is shared
across all custom sensors). Class names must match `sensors_custom.py` exactly:

```yaml
STATS:
  CUSTOM:
    INTERVAL: 3
    WireviewTotalPower:
      TEXT:
        SHOW: True
        X: 4
        Y: 120
        ...
    WireviewCurrentPin1:
      GRAPH:
        SHOW: True
        X: 4
        Y: 140
        WIDTH: 180
        HEIGHT: 8
        MIN_VALUE: 0
        MAX_VALUE: 5
        BAR_COLOR: 53, 191, 92
        ...
```

## Related files

- `library/sensors/sensors_custom.py` — custom sensor class implementations
- `library/stats.py` (`Custom.stats()`) — consumes `STATS -> CUSTOM` from the theme
- `res/themes/<your-theme>/theme.yaml` — theme layout referencing the classes above

## Dashboard theme

A complete dark-mode 3.5" portrait theme is provided at
`res/themes/wireview-dark-green/`. It references the WireView sensor classes by
name under `STATS -> CUSTOM` and also includes plain-text sections for CPU, GPU,
RAM and disk.

### Theme features

- **Plain black background** — no background image; every text/graph element uses
  `BACKGROUND_COLOR: 0, 0, 0`.
- **Screen clearing at startup** — a `static_text` entry named `CLEAR` paints the
  entire 320×480 screen black first, so the display boot message is fully
  overwritten (each subsequent text element only repaints its own bounding box).
- **Section headers** — `static_text` entries label each section: `CPU`, `GPU`,
  `WireView`, `RAM`, `DISK`.
- **Color scheme** — dark green (`53, 191, 92`) on black, matching
  `bash-dark-green-gpu`.

### Sections

| Section | Elements |
|---|---|
| CPU | % radial, temperature, frequency |
| GPU | % radial, memory graph + text, temperature |
| WireView (CUSTOM) | Total Power text; current pins 1–6 (text + bar each); Cable Temp & Case Temp text |
| RAM | % radial + used text |
| Disk | usage radial dial + used/total/free text |

### Activating

Set in `config.yaml`:

```yaml
THEME: "wireview-dark-green"
```

