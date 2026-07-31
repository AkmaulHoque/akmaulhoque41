# -*- coding: utf-8 -*-
"""Main plugin class."""

import os

from qgis.PyQt.QtCore import QCoreApplication, QUrl
from qgis.PyQt.QtGui import QDesktopServices, QIcon
from qgis.core import QgsApplication

from .compat import QAction
from .provider import SpatialAggregationMeanProvider


class SpatialAggregationMeanPlugin:
    """Registers the Processing provider and a convenient menu/toolbar action."""

    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.provider = None
        self.action = None
        self.manual_action = None

    def tr(self, text):
        return QCoreApplication.translate("SpatialAggregationMean", text)

    def initGui(self):
        self.provider = SpatialAggregationMeanProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

        self.action = QAction(
            QIcon(os.path.join(self.plugin_dir, "icon.svg")),
            self.tr("Spatial Aggregation Mean"),
            self.iface.mainWindow(),
        )
        self.action.setObjectName("spatialAggregationMeanAction")
        self.action.setWhatsThis(
            self.tr("Aggregate monthly climate CSV grids to district means")
        )
        self.action.triggered.connect(self.run)
        self.iface.addPluginToVectorMenu(self.tr("Spatial Aggregation Mean"), self.action)
        self.iface.addToolBarIcon(self.action)

        self.manual_action = QAction(
            QIcon(os.path.join(self.plugin_dir, "icon.svg")),
            self.tr("User Manual"),
            self.iface.mainWindow(),
        )
        self.manual_action.setObjectName("spatialAggregationMeanManualAction")
        self.manual_action.setWhatsThis(
            self.tr("Open the step-by-step Spatial Aggregation Mean user manual")
        )
        self.manual_action.triggered.connect(self.open_manual)
        self.iface.addPluginToVectorMenu(
            self.tr("Spatial Aggregation Mean"), self.manual_action
        )

    def unload(self):
        if self.manual_action is not None:
            self.iface.removePluginVectorMenu(
                self.tr("Spatial Aggregation Mean"), self.manual_action
            )
            self.manual_action.deleteLater()
            self.manual_action = None

        if self.action is not None:
            self.iface.removePluginVectorMenu(
                self.tr("Spatial Aggregation Mean"), self.action
            )
            self.iface.removeToolBarIcon(self.action)
            self.action.deleteLater()
            self.action = None

        if self.provider is not None:
            QgsApplication.processingRegistry().removeProvider(self.provider)
            self.provider = None

    def run(self):
        try:
            from qgis import processing
        except ImportError:  # QGIS 3 fallback
            import processing

        processing.execAlgorithmDialog(
            "spatialaggregationmean:district_monthly_means",
            {},
        )

    def open_manual(self):
        """Open the bundled HTML user manual in the default browser."""
        manual_path = os.path.join(self.plugin_dir, "docs", "user_manual.html")
        if not os.path.exists(manual_path):
            self.iface.messageBar().pushWarning(
                self.tr("Spatial Aggregation Mean"),
                self.tr("The bundled user manual could not be found. Reinstall the plugin ZIP."),
            )
            return

        opened = QDesktopServices.openUrl(QUrl.fromLocalFile(manual_path))
        if not opened:
            self.iface.messageBar().pushWarning(
                self.tr("Spatial Aggregation Mean"),
                self.tr("QGIS could not open the user manual in the default browser."),
            )

