"""CSV export generator for analytics reports."""

import csv
import io
import os
import zipfile
from typing import Any


class CsvExporter:
    """Generates CSV files from analytics data."""

    def export(self, data: dict[str, Any], report_type: str, period: str, file_path: str) -> None:
        """Export analytics data as CSV (or ZIP for full reports)."""
        if report_type == "full":
            self._export_full_zip(data, file_path)
        else:
            # Single report type — find the data key
            key = next(iter(data))
            self._export_single(data[key], file_path)

    def _export_single(self, records: Any, file_path: str) -> None:
        """Export a single report as CSV."""
        if isinstance(records, dict):
            # Summary is a single dict — write as key-value pairs
            with open(file_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Metric", "Value"])
                for key, value in records.items():
                    writer.writerow([key, value])
        elif isinstance(records, list) and len(records) > 0:
            # List of dicts — use keys as headers
            with open(file_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=records[0].keys())
                writer.writeheader()
                writer.writerows(records)
        else:
            # Empty list
            with open(file_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["No data available"])

    def _export_full_zip(self, data: dict[str, Any], file_path: str) -> None:
        """Export all report types as a ZIP of CSV files."""
        with zipfile.ZipFile(file_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for name, records in data.items():
                buf = io.StringIO()
                if isinstance(records, dict):
                    writer = csv.writer(buf)
                    writer.writerow(["Metric", "Value"])
                    for key, value in records.items():
                        writer.writerow([key, value])
                elif isinstance(records, list) and len(records) > 0:
                    writer = csv.DictWriter(buf, fieldnames=records[0].keys())
                    writer.writeheader()
                    writer.writerows(records)
                else:
                    writer = csv.writer(buf)
                    writer.writerow(["No data available"])

                zf.writestr(f"{name}.csv", buf.getvalue())
