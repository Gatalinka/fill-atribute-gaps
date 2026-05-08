# Fill Attribute Gaps — QGIS Plugin

Interpolate missing (NULL) attribute values between known key points in any vector layer.

![QGIS](https://img.shields.io/badge/QGIS-3.0%2B-green) ![License](https://img.shields.io/badge/license-GPL--2.0-blue)

## What it does

Pick a layer, choose a numeric column with some values filled in and some NULL, select an interpolation method, and the plugin fills in the blanks. Existing values (including 0) are never overwritten. Supports full undo with Ctrl+Z.

## Interpolation methods

| Method | Description |
|--------|-------------|
| **Linear** | Straight-line interpolation between key points (default) |
| **Nearest neighbor** | Copy the closest known value |
| **Cubic spline** | Smooth curve through key points (needs scipy, 3+ keys) |
| **PCHIP** | Smooth, monotone — never overshoots (needs scipy, 3+ keys) |
| **Akima** | Handles sharp transitions without oscillation (needs scipy, 5+ keys) |
| **Step (forward fill)** | Carry last known value forward |

## Output precision

Control how interpolated values are rounded:

- **Auto** — matches the field type (integer fields get whole numbers, decimal fields keep full precision)
- **Integer** — always round to whole numbers
- **Decimal places (1–10)** — round to a fixed number of decimal places

## Common use cases

- Filling elevation profiles along routes
- Chainage / milepost values along linear features
- Sensor readings (temperature, concentration) along transects
- Survey data completion
- Utility network attributes (pipe diameter, pole height)
- Bird overflight height extraction from scanned maps

## Installation

**From QGIS Plugin Manager:**
1. Open QGIS
2. Go to Plugins > Manage and Install Plugins
3. Search for "Fill Attribute Gaps"
4. Click Install

**From ZIP:**
1. Download the latest release ZIP
2. Go to Plugins > Manage and Install Plugins > Install from ZIP
3. Select the ZIP file

## Usage

1. Open a vector layer with a numeric field containing some NULL values
2. Go to Vector menu > Fill Attribute Gaps (or click the toolbar icon)
3. Select the layer, sort field (optional), and target field to fill
4. Choose an interpolation method and output precision
5. Click "Fill Gaps"
6. Use Ctrl+Z to undo if needed

## Requirements

- QGIS 3.0 or later
- numpy (included with QGIS)
- scipy (optional, needed for spline/PCHIP/Akima methods)

## Author

Maja Mihaljević

## License

This plugin is licensed under the GNU General Public License v2.0.
