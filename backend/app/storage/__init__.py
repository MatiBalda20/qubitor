"""Almacenamiento del Módulo D: reportes en un bucket S3-compatible (R2 o Supabase Storage)."""

from app.storage.reports import ReportStorage, archive_scan, get_report_storage

__all__ = ["ReportStorage", "archive_scan", "get_report_storage"]
