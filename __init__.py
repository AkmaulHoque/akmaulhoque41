# -*- coding: utf-8 -*-
"""QGIS plugin entry point."""


def classFactory(iface):
    from .plugin import SpatialAggregationMeanPlugin
    return SpatialAggregationMeanPlugin(iface)
