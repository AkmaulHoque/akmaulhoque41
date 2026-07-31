# Spatial Aggregation Mean — QGIS Plugin

A portable QGIS 3 and QGIS 4 Processing plugin that converts monthly gridded climate CSV files into district-wise monthly mean CSV files.

## What it does

1. Reads every CSV in a selected folder.
2. Detects longitude and latitude columns (`long`, `longitude`, `lon`, `lng`, `x`; `lat`, `latitude`, `y`).
3. Detects January–December columns using full month names or common abbreviations.
4. Reprojects the selected district layer internally to WGS 84 (`EPSG:4326`).
5. Calculates the mean of grid values falling within each district.
6. For a district containing no grid point, calculates the mean of the nearest **N** grid points; default **N = 8**.
7. Writes one output CSV per input CSV and a processing report.

The plugin uses only PyQGIS and the Python standard library. It does **not** require GeoPandas, Pandas, SciPy, Rtree, Pyogrio, Google Colab, or Google Drive.

## Installation

1. Download `Spatial_Aggregation_Mean_QGIS_Plugin_v1.3.2_QGIS4_READY.zip`.
2. Open QGIS.
3. Go to **Plugins → Manage and Install Plugins → Install from ZIP**.
4. Select the ZIP file and install it.
5. Enable **Spatial Aggregation Mean** if QGIS does not enable it automatically.
6. Open the bundled manual from **Vector → Spatial Aggregation Mean → User Manual**.

## Running the plugin

Use either:

- the toolbar button / **Vector → Spatial Aggregation Mean → Spatial Aggregation Mean**, or
- **Processing Toolbox → Spatial Aggregation Mean → Climate aggregation → Spatial Aggregation Mean**.

Choose:

- a district polygon layer;
- the district-name or unique-ID field (for example `DISTRICT`);
- the input CSV folder;
- the output folder;
- nearest-grid count, normally `8`.

## Input CSV requirements

Each CSV must have:

- one longitude column;
- one latitude column;
- all 12 monthly columns.

Example:

```text
longitude,latitude,january,february,march,april,may,june,july,august,september,october,november,december
91.75,25.60,8.2,9.5,12.4,16.1,18.0,19.2,19.8,19.6,18.7,15.9,12.4,9.1
```

## Output

For `model_01.csv`, the default output is:

```text
model_01_DistrictMean.csv
```

Output columns are the selected district field followed by lowercase month names. A `spatial_aggregation_mean_processing_report.csv` file records successful and failed inputs.

## Important notes

- Use a district field whose values uniquely identify districts. If the same value appears in multiple polygon records, the plugin dissolves those parts logically before aggregation.
- Nearest-neighbour search is performed in WGS 84 longitude/latitude coordinates, matching the behaviour of the supplied SciPy `cKDTree` script.
- Existing output files are not overwritten; `_2`, `_3`, and so on are added automatically.
- Blank, `NA`, `NaN`, `null`, `-999`, and `-9999` monthly values are ignored in mean calculations.

## Compatibility

- QGIS 3.22+ and QGIS 4.x (metadata range: 3.22–4.99)
- Qt 5 and Qt 6 through the QGIS `qgis.PyQt` compatibility layer
- Windows, Linux, and macOS

## QGIS 4 compatibility

Version 1.3.2 is listed as compatible with QGIS 3 and QGIS 4 through `qgisMaximumVersion=4.99`. The code uses the QGIS-provided `qgis.PyQt` compatibility layer, handles the Qt 5/Qt 6 `QAction` module change, and selects the correct Processing enum namespaces for both QGIS major versions.

## License

GNU General Public License v2 or later.

## Bundled user manual

The plugin contains a complete step-by-step manual in `docs/user_manual.html` and `docs/Spatial_Aggregation_Mean_User_Manual.docx`. The HTML version can be opened directly from the QGIS Vector menu.


## Authors and contact

- Mr. Akmaul Hoque
- Dr. Manish Kumar Naskar
- Dr. Debasish Chakraborty
- Dr. Koushik Bag

Water Management Section, Division of System Research and Engineering (DSRE), ICAR Research Complex for NEH Region, Umiam, Meghalaya, India.

Contact: `akmaulhoque41@gmail.com`

## Public repository links required before QGIS upload

Before submitting to the official QGIS Plugin Repository, populate `homepage`, `repository`, and `tracker` in `metadata.txt` with working public links. The homepage should describe this plugin, the repository must expose the uncompressed source code, and the tracker should point to the repository issue tracker.
## Project links

- Homepage: https://github.com/AkmaulHoque/akmaulhoque41#readme
- Source repository: https://github.com/AkmaulHoque/akmaulhoque41
- Issue tracker: https://github.com/AkmaulHoque/akmaulhoque41/issues

