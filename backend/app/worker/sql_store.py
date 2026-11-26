"""Persistencia del escaneo en Postgres (Supabase) con los modelos de la base."""

import logging
import uuid
from collections.abc import Callable
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.models import Finding, FindingStatus, Scan, ScanStatus
from app.engines.base import Severity
from app.orchestrator.pipeline import ScanResult
from app.orchestrator.risk import grade, risk_score

logger = logging.getLogger(__name__)


class SqlScanStore:
    """Actualiza la fila del escaneo que creó la API y guarda sus hallazgos.

    Cada método es una transacción: si algo falla, no quedan hallazgos a medias.
    """

    def __init__(self, session_factory: Callable[[], Session] | None = None):
        if session_factory is None:
            from app.models.database import SessionLocal

            session_factory = SessionLocal
        self._session_factory = session_factory

    def mark_running(self, scan_id: str) -> None:
        with self._session_factory() as session, session.begin():
            scan = _get_scan(session, scan_id)
            if scan is not None:
                scan.status = ScanStatus.RUNNING
                scan.started_at = _now()
                scan.error = None

    def save_result(self, scan_id: str, commit_sha: str, result: ScanResult) -> None:
        with self._session_factory() as session, session.begin():
            scan = _get_scan(session, scan_id)
            if scan is None:
                return
            # Un reintento pudo haber guardado hallazgos antes de fallar: se reemplazan.
            session.execute(delete(Finding).where(Finding.scan_id == scan.id))
            confirmed = _confirmed_false_positives(session, scan)
            session.add_all(
                Finding(
                    scan_id=scan.id,
                    fingerprint=fingerprint,
                    engine=finding.engine,
                    rule_id=finding.rule_id,
                    title=_clean(finding.title),
                    severity=finding.severity,
                    file_path=_clean(finding.file_path),
                    line=finding.line,
                    snippet=_clean(finding.snippet),
                    description=_clean(finding.description),
                    cwe=finding.cwe,
                    cve=finding.cve,
                    metadata_=_clean(finding.metadata),
                    status=FindingStatus.FALSE_POSITIVE if fingerprint in confirmed else FindingStatus.OPEN,
                    **_triage_columns(result.triage.get(fingerprint)),
                )
                for fingerprint, finding in result.findings.items()
            )
            scan.status = ScanStatus.COMPLETED
            scan.commit_sha = commit_sha
            scan.risk_score = result.risk_score
            if confirmed & result.findings.keys():
                scan.risk_score = _score_without(result, confirmed)
            scan.grade = grade(scan.risk_score) if confirmed & result.findings.keys() else result.grade
            scan.engine_errors = _clean(result.errors) or None
            scan.ai_summary = _clean(result.summary)
            scan.error = None
            scan.finished_at = _now()

    def mark_failed(self, scan_id: str, error: str) -> None:
        with self._session_factory() as session, session.begin():
            scan = _get_scan(session, scan_id)
            if scan is not None:
                scan.status = ScanStatus.FAILED
                scan.error = _clean(error)
                scan.finished_at = _now()


def _get_scan(session: Session, scan_id: str) -> Scan | None:
    """La fila del escaneo, o None si no existe: no tiene sentido reintentar."""
    try:
        key = uuid.UUID(scan_id)
    except ValueError:
        key = None
    scan = session.get(Scan, key) if key else None
    if scan is None:
        logger.warning("El escaneo %s no existe en la base: no se guarda el resultado", scan_id)
    return scan


def _confirmed_false_positives(session: Session, scan: Scan) -> set[str]:
    """Fingerprints que una persona marcó como falso positivo en el último escaneo
    completado del mismo repo (F-03): si el hallazgo sigue apareciendo, la marca se
    conserva en lugar de volver a `open`.

    Solo se arrastran los falsos positivos. Un hallazgo marcado `resolved` que
    vuelve a aparecer no está resuelto, así que vuelve a quedar abierto.
    """
    previous = session.scalar(
        select(Scan.id)
        .where(Scan.repository_id == scan.repository_id, Scan.id != scan.id, Scan.status == ScanStatus.COMPLETED)
        .order_by(Scan.created_at.desc())
        .limit(1)
    )
    if previous is None:
        return set()
    return set(session.scalars(
        select(Finding.fingerprint).where(Finding.scan_id == previous, Finding.status == FindingStatus.FALSE_POSITIVE)
    ))


def _score_without(result: ScanResult, excluded: set[str]) -> float:
    """Risk Score con la severidad ajustada por la IA y sin los falsos positivos confirmados."""
    severities = []
    for fingerprint, finding in result.findings.items():
        if fingerprint in excluded:
            continue
        evaluation = result.triage.get(fingerprint)
        severities.append(evaluation.adjusted_severity if evaluation is not None else Severity(finding.severity))
    return risk_score(severities)


def _triage_columns(evaluation) -> dict:
    """Columnas ai_* del hallazgo a partir del triage del Módulo E; vacías si no hubo."""
    if evaluation is None:
        return {}
    return {
        "ai_is_false_positive": evaluation.is_false_positive,
        "ai_adjusted_severity": evaluation.adjusted_severity,
        "ai_explanation": _clean(evaluation.explanation),
        "ai_remediation": _clean(evaluation.remediation),
    }


def _clean(value):
    """Quita el byte nulo, que Postgres no acepta en textos ni en JSONB.

    Los textos salen del código del repo: un archivo con ese carácter no puede
    hacer fallar el guardado de todo el escaneo.
    """
    if isinstance(value, str):
        return value.replace("\x00", "")
    if isinstance(value, dict):
        return {_clean(key): _clean(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_clean(item) for item in value]
    return value


def _now() -> datetime:
    return datetime.now(timezone.utc)
