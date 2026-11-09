"""Caché del triage en la base: reutiliza evaluaciones de escaneos anteriores del mismo repo.

El mismo hallazgo (fingerprint) con el mismo código y la misma severidad ya fue
evaluado por Gemini en un escaneo previo: se reutiliza esa respuesta en lugar de
gastar cuota. La búsqueda se limita al repositorio del escaneo, así una
organización nunca recibe evaluaciones generadas con el código de otra.
"""

import logging
import uuid
from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.triage import TriageCache, TriageResult, content_key
from app.engines.base import Finding, Severity

logger = logging.getLogger(__name__)


class SqlTriageCache(TriageCache):
    def __init__(self, scan_id: str, session_factory: Callable[[], Session] | None = None):
        self.scan_id = scan_id
        if session_factory is None:
            from app.models.database import SessionLocal

            session_factory = SessionLocal
        self._session_factory = session_factory

    def get_many(self, keys: list[str]) -> dict[str, TriageResult]:
        try:
            scan_key = uuid.UUID(self.scan_id)
        except ValueError:
            return {}
        wanted = set(keys)
        fingerprints = {key.split(":", 1)[0] for key in wanted}
        if not fingerprints:
            return {}

        from app.models.models import Finding as FindingRow
        from app.models.models import Scan

        found: dict[str, TriageResult] = {}
        with self._session_factory() as session:
            repository_id = session.scalar(select(Scan.repository_id).where(Scan.id == scan_key))
            if repository_id is None:
                return {}
            rows = session.scalars(
                select(FindingRow)
                .join(Scan, FindingRow.scan_id == Scan.id)
                .where(
                    Scan.repository_id == repository_id,
                    Scan.id != scan_key,
                    FindingRow.fingerprint.in_(fingerprints),
                    FindingRow.ai_is_false_positive.is_not(None),
                )
                .order_by(Scan.created_at.desc())
            )
            for row in rows:
                key = content_key(row.fingerprint, _as_finding(row))
                if key in wanted and key not in found:
                    found[key] = TriageResult(
                        is_false_positive=bool(row.ai_is_false_positive),
                        adjusted_severity=Severity(row.ai_adjusted_severity or row.severity),
                        explanation=row.ai_explanation or "",
                        remediation=row.ai_remediation or "",
                    )
        return found

    def put_many(self, entries: dict[str, TriageResult]) -> None:
        # Las evaluaciones nuevas quedan en la base junto con los hallazgos (SqlScanStore).
        return None


def _as_finding(row) -> Finding:
    return Finding(
        engine=row.engine, rule_id=row.rule_id, title=row.title, severity=Severity(row.severity),
        file_path=row.file_path, line=row.line, snippet=row.snippet, description=row.description,
    )
