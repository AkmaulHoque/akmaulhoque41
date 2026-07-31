# -*- coding: utf-8 -*-
"""District-wise monthly climate aggregation Processing algorithm."""

import csv
import math
import os
from collections import defaultdict

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsFeatureRequest,
    QgsGeometry,
    QgsPointXY,
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterField,
    QgsProcessingParameterFile,
    QgsProcessingParameterFolderDestination,
    QgsProcessingParameterNumber,
    QgsProcessingParameterString,
    QgsProcessingOutputFile,
    QgsRectangle,
    QgsSpatialIndex,
)

from .compat import (
    PROCESSING_FIELD_ANY,
    PROCESSING_FILE_FOLDER,
    PROCESSING_NUMBER_INTEGER,
    PROCESSING_SOURCE_VECTOR_POLYGON,
)


MONTHS = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
]

MONTH_ALIASES = {
    "january": ("january", "jan"),
    "february": ("february", "feb"),
    "march": ("march", "mar"),
    "april": ("april", "apr"),
    "may": ("may",),
    "june": ("june", "jun"),
    "july": ("july", "jul"),
    "august": ("august", "aug"),
    "september": ("september", "sep", "sept"),
    "october": ("october", "oct"),
    "november": ("november", "nov"),
    "december": ("december", "dec"),
}

LONGITUDE_ALIASES = ("long", "longitude", "lon", "lng", "x")
LATITUDE_ALIASES = ("lat", "latitude", "y")


class DistrictMonthlyMeansAlgorithm(QgsProcessingAlgorithm):
    DISTRICTS = "DISTRICTS"
    DISTRICT_FIELD = "DISTRICT_FIELD"
    INPUT_FOLDER = "INPUT_FOLDER"
    OUTPUT_FOLDER = "OUTPUT_FOLDER"
    NEAREST_COUNT = "NEAREST_COUNT"
    RECURSIVE = "RECURSIVE"
    OUTPUT_SUFFIX = "OUTPUT_SUFFIX"

    def tr(self, text):
        return QCoreApplication.translate("DistrictMonthlyMeansAlgorithm", text)

    def createInstance(self):
        return DistrictMonthlyMeansAlgorithm()

    def name(self):
        return "district_monthly_means"

    def displayName(self):
        return self.tr("Spatial Aggregation Mean")

    def group(self):
        return self.tr("Climate aggregation")

    def groupId(self):
        return "climate_aggregation"

    def shortHelpString(self):
        return self.tr(
            "Batch-processes CSV files containing longitude, latitude and 12 monthly "
            "columns. Grid points are assigned to district polygons in EPSG:4326. "
            "For districts containing no grid point, monthly values are calculated "
            "from the nearest N grid points. The output is one CSV per input file.\n\n"
            "Accepted coordinate headers: long/longitude/lon/lng/x and "
            "lat/latitude/y. Month names may be full names or common abbreviations. "
            "No external Python packages are required."
        )

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.DISTRICTS,
                self.tr("District polygon layer"),
                [PROCESSING_SOURCE_VECTOR_POLYGON],
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                self.DISTRICT_FIELD,
                self.tr("District name or unique ID field"),
                parentLayerParameterName=self.DISTRICTS,
                type=PROCESSING_FIELD_ANY,
            )
        )
        self.addParameter(
            QgsProcessingParameterFile(
                self.INPUT_FOLDER,
                self.tr("Folder containing input CSV files"),
                behavior=PROCESSING_FILE_FOLDER,
            )
        )
        self.addParameter(
            QgsProcessingParameterFolderDestination(
                self.OUTPUT_FOLDER,
                self.tr("Output folder"),
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.NEAREST_COUNT,
                self.tr("Nearest grid points for uncovered districts"),
                type=PROCESSING_NUMBER_INTEGER,
                defaultValue=8,
                minValue=1,
                maxValue=1000,
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.RECURSIVE,
                self.tr("Search CSV files in subfolders"),
                defaultValue=False,
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.OUTPUT_SUFFIX,
                self.tr("Output filename suffix"),
                defaultValue="_DistrictMean",
            )
        )
        self.addOutput(
            QgsProcessingOutputFile(
                "PROCESSING_REPORT",
                self.tr("CSV processing report"),
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.DISTRICTS, context)
        if source is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.DISTRICTS))

        district_field = self.parameterAsString(parameters, self.DISTRICT_FIELD, context)
        input_folder = self.parameterAsFile(parameters, self.INPUT_FOLDER, context)
        output_folder = self.parameterAsString(parameters, self.OUTPUT_FOLDER, context)
        nearest_count = self.parameterAsInt(parameters, self.NEAREST_COUNT, context)
        recursive = self.parameterAsBool(parameters, self.RECURSIVE, context)
        output_suffix = self.parameterAsString(parameters, self.OUTPUT_SUFFIX, context)

        if not os.path.isdir(input_folder):
            raise QgsProcessingException(self.tr("Input folder does not exist."))
        os.makedirs(output_folder, exist_ok=True)

        csv_files = self._find_csv_files(input_folder, recursive)
        if not csv_files:
            raise QgsProcessingException(self.tr("No CSV files were found in the input folder."))

        feedback.pushInfo(self.tr("Preparing district geometries in EPSG:4326..."))
        district_records, district_index = self._prepare_districts(
            source, district_field, context, feedback
        )
        if not district_records:
            raise QgsProcessingException(
                self.tr("No usable district geometries or district IDs were found.")
            )

        feedback.pushInfo(self.tr("CSV files found: {}" ).format(len(csv_files)))
        report_rows = []
        output_paths = []

        for file_number, csv_path in enumerate(csv_files, start=1):
            if feedback.isCanceled():
                break

            feedback.setProgress(100.0 * (file_number - 1) / max(1, len(csv_files)))
            feedback.pushInfo("=" * 60)
            feedback.pushInfo(
                self.tr("Processing {}/{}: {}" ).format(
                    file_number, len(csv_files), os.path.basename(csv_path)
                )
            )

            try:
                result = self._process_one_csv(
                    csv_path=csv_path,
                    district_records=district_records,
                    district_index=district_index,
                    district_field=district_field,
                    output_folder=output_folder,
                    output_suffix=output_suffix,
                    nearest_count=nearest_count,
                    feedback=feedback,
                )
                output_paths.append(result["output_path"])
                report_rows.append({
                    "input_csv": csv_path,
                    "status": "success",
                    "output_csv": result["output_path"],
                    "grid_points": result["grid_points"],
                    "districts_with_points": result["covered_count"],
                    "districts_nearest_fallback": result["missing_count"],
                    "message": "",
                })
                feedback.pushInfo(
                    self.tr("Saved: {}" ).format(result["output_path"])
                )
            except Exception as exc:
                message = str(exc)
                feedback.reportError(
                    self.tr("Skipped {}: {}" ).format(os.path.basename(csv_path), message),
                    fatalError=False,
                )
                report_rows.append({
                    "input_csv": csv_path,
                    "status": "failed",
                    "output_csv": "",
                    "grid_points": "",
                    "districts_with_points": "",
                    "districts_nearest_fallback": "",
                    "message": message,
                })

        report_path = os.path.join(output_folder, "spatial_aggregation_mean_processing_report.csv")
        self._write_report(report_path, report_rows)
        feedback.setProgress(100)
        feedback.pushInfo("=" * 60)
        feedback.pushInfo(self.tr("Processing report: {}" ).format(report_path))
        feedback.pushInfo(
            self.tr("Successful files: {} of {}" ).format(
                len(output_paths), len(csv_files)
            )
        )

        return {
            self.OUTPUT_FOLDER: output_folder,
            "PROCESSING_REPORT": report_path,
        }

    @staticmethod
    def _find_csv_files(folder, recursive):
        paths = []
        if recursive:
            for root, _, files in os.walk(folder):
                for filename in files:
                    if filename.lower().endswith(".csv"):
                        paths.append(os.path.join(root, filename))
        else:
            for filename in os.listdir(folder):
                path = os.path.join(folder, filename)
                if os.path.isfile(path) and filename.lower().endswith(".csv"):
                    paths.append(path)
        return sorted(paths, key=lambda p: p.lower())

    def _prepare_districts(self, source, district_field, context, feedback):
        source_crs = source.sourceCrs()
        target_crs = QgsCoordinateReferenceSystem("EPSG:4326")
        transform = None
        if source_crs.isValid() and source_crs != target_crs:
            transform = QgsCoordinateTransform(
                source_crs,
                target_crs,
                context.transformContext(),
            )

        grouped_geometries = defaultdict(list)
        field_index = source.fields().lookupField(district_field)
        if field_index < 0:
            raise QgsProcessingException(
                self.tr("District field '{}' was not found." ).format(district_field)
            )

        request = QgsFeatureRequest().setSubsetOfAttributes([field_index])
        total = source.featureCount()
        for i, feature in enumerate(source.getFeatures(request)):
            if feedback.isCanceled():
                break
            if total > 0 and i % 100 == 0:
                feedback.setProgress(min(5.0, 5.0 * i / total))

            raw_key = feature[district_field]
            if raw_key is None:
                continue
            key = str(raw_key).strip()
            if not key:
                continue

            geometry = feature.geometry()
            if geometry is None or geometry.isEmpty():
                continue
            geometry = QgsGeometry(geometry)
            if transform is not None:
                geometry.transform(transform)
            if not geometry.isGeosValid():
                geometry = geometry.makeValid()
            if geometry.isEmpty():
                continue
            grouped_geometries[key].append(geometry)

        district_records = {}
        district_index = QgsSpatialIndex()
        synthetic_id = 1

        for key in sorted(grouped_geometries, key=lambda value: value.casefold()):
            parts = grouped_geometries[key]
            geometry = parts[0] if len(parts) == 1 else QgsGeometry.unaryUnion(parts)
            if geometry is None or geometry.isEmpty():
                continue

            centroid_geometry = geometry.pointOnSurface()
            if centroid_geometry.isEmpty():
                centroid_geometry = geometry.centroid()
            centroid = centroid_geometry.asPoint()

            feature = QgsFeature()
            feature.setId(synthetic_id)
            feature.setGeometry(geometry)
            district_index.addFeature(feature)
            district_records[synthetic_id] = {
                "key": key,
                "geometry": geometry,
                "centroid": QgsPointXY(centroid),
            }
            synthetic_id += 1

        return district_records, district_index

    def _process_one_csv(
        self,
        csv_path,
        district_records,
        district_index,
        district_field,
        output_folder,
        output_suffix,
        nearest_count,
        feedback,
    ):
        dialect = self._detect_dialect(csv_path)
        with open(csv_path, "r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle, dialect=dialect)
            if not reader.fieldnames:
                raise QgsProcessingException(self.tr("CSV has no header row."))

            normalized_to_original = {}
            for original in reader.fieldnames:
                normalized = self._normalize_header(original)
                if normalized and normalized not in normalized_to_original:
                    normalized_to_original[normalized] = original

            longitude_column = self._first_matching_column(
                normalized_to_original, LONGITUDE_ALIASES
            )
            latitude_column = self._first_matching_column(
                normalized_to_original, LATITUDE_ALIASES
            )
            if longitude_column is None or latitude_column is None:
                raise QgsProcessingException(
                    self.tr(
                        "Longitude/latitude columns were not found. Accepted headers: "
                        "long, longitude, lon, lng, x; lat, latitude, y."
                    )
                )

            month_columns = {}
            missing_months = []
            for month in MONTHS:
                original = self._first_matching_column(
                    normalized_to_original, MONTH_ALIASES[month]
                )
                if original is None:
                    missing_months.append(month)
                else:
                    month_columns[month] = original
            if missing_months:
                raise QgsProcessingException(
                    self.tr("Missing month columns: {}" ).format(", ".join(missing_months))
                )

            point_index = QgsSpatialIndex()
            point_values = {}
            point_id = 1
            district_sums = {
                did: [0.0] * len(MONTHS) for did in district_records
            }
            district_counts = {
                did: [0] * len(MONTHS) for did in district_records
            }
            covered_ids = set()
            invalid_rows = 0

            for row_number, row in enumerate(reader, start=2):
                if feedback.isCanceled():
                    break
                try:
                    x = self._to_float(row.get(longitude_column))
                    y = self._to_float(row.get(latitude_column))
                except (TypeError, ValueError):
                    invalid_rows += 1
                    continue

                if x is None or y is None or not (-180 <= x <= 180) or not (-90 <= y <= 90):
                    invalid_rows += 1
                    continue

                values = [self._to_float(row.get(month_columns[m])) for m in MONTHS]
                point = QgsPointXY(x, y)
                point_geometry = QgsGeometry.fromPointXY(point)

                point_feature = QgsFeature()
                point_feature.setId(point_id)
                point_feature.setGeometry(point_geometry)
                point_index.addFeature(point_feature)
                point_values[point_id] = values

                candidates = district_index.intersects(QgsRectangle(x, y, x, y))
                for district_id in candidates:
                    district_geometry = district_records[district_id]["geometry"]
                    if district_geometry.intersects(point_geometry):
                        covered_ids.add(district_id)
                        for month_index, value in enumerate(values):
                            if value is not None:
                                district_sums[district_id][month_index] += value
                                district_counts[district_id][month_index] += 1
                point_id += 1

        if not point_values:
            raise QgsProcessingException(
                self.tr("No valid longitude-latitude grid rows were found.")
            )

        missing_ids = set(district_records) - covered_ids
        final_values = {}

        for district_id in covered_ids:
            final_values[district_id] = [
                (
                    district_sums[district_id][i] / district_counts[district_id][i]
                    if district_counts[district_id][i] > 0
                    else None
                )
                for i in range(len(MONTHS))
            ]

        k = min(max(1, nearest_count), len(point_values))
        for district_id in missing_ids:
            centroid = district_records[district_id]["centroid"]
            nearest_ids = point_index.nearestNeighbor(centroid, k)
            month_sums = [0.0] * len(MONTHS)
            month_counts = [0] * len(MONTHS)
            for point_feature_id in nearest_ids:
                values = point_values.get(point_feature_id, [])
                for month_index, value in enumerate(values):
                    if value is not None:
                        month_sums[month_index] += value
                        month_counts[month_index] += 1
            final_values[district_id] = [
                month_sums[i] / month_counts[i] if month_counts[i] else None
                for i in range(len(MONTHS))
            ]

        base_name = os.path.splitext(os.path.basename(csv_path))[0]
        proposed_path = os.path.join(output_folder, base_name + output_suffix + ".csv")
        output_path = self._unique_path(proposed_path)

        with open(output_path, "w", encoding="utf-8-sig", newline="") as output_handle:
            writer = csv.writer(output_handle)
            writer.writerow([district_field] + MONTHS)
            sorted_ids = sorted(
                district_records,
                key=lambda did: district_records[did]["key"].casefold(),
            )
            for district_id in sorted_ids:
                values = final_values.get(district_id, [None] * len(MONTHS))
                writer.writerow(
                    [district_records[district_id]["key"]]
                    + [self._format_number(value) for value in values]
                )

        if invalid_rows:
            feedback.pushWarning(
                self.tr("Ignored invalid coordinate rows: {}" ).format(invalid_rows)
            )
        feedback.pushInfo(
            self.tr("Districts using nearest-grid fallback: {}" ).format(len(missing_ids))
        )

        return {
            "output_path": output_path,
            "grid_points": len(point_values),
            "covered_count": len(covered_ids),
            "missing_count": len(missing_ids),
        }

    @staticmethod
    def _normalize_header(value):
        return str(value or "").replace("\ufeff", "").strip().lower()

    @staticmethod
    def _first_matching_column(normalized_to_original, aliases):
        for alias in aliases:
            if alias in normalized_to_original:
                return normalized_to_original[alias]
        return None

    @staticmethod
    def _to_float(value):
        if value is None:
            return None
        text = str(value).strip()
        if not text or text.lower() in {"na", "nan", "null", "none", "-999", "-9999"}:
            return None
        number = float(text)
        if not math.isfinite(number):
            return None
        return number

    @staticmethod
    def _format_number(value):
        if value is None:
            return ""
        return format(float(value), ".10g")

    @staticmethod
    def _detect_dialect(csv_path):
        with open(csv_path, "r", encoding="utf-8-sig", newline="") as handle:
            sample = handle.read(16384)
        try:
            return csv.Sniffer().sniff(sample, delimiters=",;\t|")
        except csv.Error:
            return csv.excel

    @staticmethod
    def _unique_path(path):
        if not os.path.exists(path):
            return path
        root, extension = os.path.splitext(path)
        counter = 2
        while True:
            candidate = "{}_{}{}".format(root, counter, extension)
            if not os.path.exists(candidate):
                return candidate
            counter += 1

    @staticmethod
    def _write_report(report_path, report_rows):
        fields = [
            "input_csv",
            "status",
            "output_csv",
            "grid_points",
            "districts_with_points",
            "districts_nearest_fallback",
            "message",
        ]
        with open(report_path, "w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(report_rows)
