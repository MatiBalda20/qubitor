"""Persistencia del resultado de un escaneo, vista desde el scan-worker.

El worker solo conoce esta interfaz. Con `DATABASE_URL` configurada guarda en
Postgres (`SqlScanStore`); sin ella, `LogScanStore` deja el pipeline andando
para probar la cola en local sin una base.
"""

import logging
import os
from typing import Protocol

from app.orchestrator.pipeline import ScanResult

logger = logging.getLogger(__name__)


class ScanStore(Protocol):
    def mark_running(self, scan_id: str) -> None: ...

    def save_result(self, scan_id: str, commit_sha: str, result: ScanResult) -> None: ...

    def mark_failed(self, scan_id: str, error: str) -> None: ...


class LogScanStore:
    """Registra los resultados en el log, sin guardarlos."""

    def mark_running(self, scan_id: str) -> None:
        logger.info("Escaneo %s: en curso", scan_id)

    def save_result(self, scan_id: str, commit_sha: str, result: ScanResult) -> None:
        logger.info(
            "Escaneo %s: %d hallazgos, score %s, nota %s (commit %s)",
            scan_id, len(result.findings), result.risk_score, result.grade, commit_sha,
        )

    def mark_failed(self, scan_id: str, error: str) -> None:
        logger.warning("Escaneo %s: falló: %s", scan_id, error)


def get_store() -> ScanStore:
    if not os.getenv("DATABASE_URL"):
        return LogScanStore()
    # Se importa acá para que el worker funcione sin las dependencias de la base.
    from app.worker.sql_store import SqlScanStore

    return SqlScanStore()
