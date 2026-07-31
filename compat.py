# -*- coding: utf-8 -*-
"""Compatibility helpers for QGIS 3/Qt 5 and QGIS 4/Qt 6."""

from qgis.core import (
    Qgis,
    QgsProcessing,
    QgsProcessingParameterField,
    QgsProcessingParameterFile,
    QgsProcessingParameterNumber,
)

# QAction moved from QtWidgets in Qt 5 to QtGui in Qt 6.
try:  # QGIS 4 / Qt 6
    from qgis.PyQt.QtGui import QAction
except ImportError:  # QGIS 3 / Qt 5
    from qgis.PyQt.QtWidgets import QAction


def _processing_enum(qgis_enum_name, member_name, legacy_owner, legacy_name):
    """Return a QGIS 4 enum value, with a QGIS 3 fallback."""
    enum_class = getattr(Qgis, qgis_enum_name, None)
    if enum_class is not None and hasattr(enum_class, member_name):
        return getattr(enum_class, member_name)
    return getattr(legacy_owner, legacy_name)


PROCESSING_SOURCE_VECTOR_POLYGON = _processing_enum(
    "ProcessingSourceType",
    "VectorPolygon",
    QgsProcessing,
    "TypeVectorPolygon",
)

PROCESSING_FIELD_ANY = _processing_enum(
    "ProcessingFieldParameterDataType",
    "Any",
    QgsProcessingParameterField,
    "Any",
)

PROCESSING_FILE_FOLDER = _processing_enum(
    "ProcessingFileParameterBehavior",
    "Folder",
    QgsProcessingParameterFile,
    "Folder",
)

PROCESSING_NUMBER_INTEGER = _processing_enum(
    "ProcessingNumberParameterType",
    "Integer",
    QgsProcessingParameterNumber,
    "Integer",
)
