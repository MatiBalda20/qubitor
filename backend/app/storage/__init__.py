"""Almacenamiento del Módulo D: reportes en Cloudflare R2."""

from app.storage.reports import ReportStorage, archive_scan, get_report_storage

__all__ = ["ReportStorage", "archive_scan", "get_report_storage"]
