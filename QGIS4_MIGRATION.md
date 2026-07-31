# QGIS 4 / Qt 6 migration notes

Version 1.3.2 supports QGIS 3.22+ and QGIS 4.x.

Compatibility declaration:
- QGIS plugin listings determine QGIS 4 readiness from `qgisMaximumVersion`.
- `qgisMaximumVersion=4.99` in `metadata.txt`.
- `deprecated=False` retained.
- Qt 6 `QAction` import with a Qt 5 fallback.
- QGIS 4 Processing enum namespaces with QGIS 3 fallbacks.
- Uses only `qgis.PyQt`; no direct PyQt5/PyQt6 imports.

Before publishing, test the same ZIP in QGIS 3.44 LTR and a current QGIS 4 release.
