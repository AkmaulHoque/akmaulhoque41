# -*- coding: utf-8 -*-
"""Processing provider."""

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import QgsProcessingProvider

from .algorithm import DistrictMonthlyMeansAlgorithm


class SpatialAggregationMeanProvider(QgsProcessingProvider):
    def loadAlgorithms(self):
        self.addAlgorithm(DistrictMonthlyMeansAlgorithm())

    def id(self):
        return "spatialaggregationmean"

    def name(self):
        return self.tr("Spatial Aggregation Mean")

    def longName(self):
        return self.name()

    def icon(self):
        return super().icon()

    def tr(self, text):
        return QCoreApplication.translate("SpatialAggregationMeanProvider", text)
