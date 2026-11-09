"""Formato de las respuestas de la API.

Siguen los tipos del frontend (frontend/src/types/Scan.ts y Finding.ts): si
cambia uno, se actualiza el otro en el mismo Pull Request.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.engines.base import Severity
from app.models.models import Finding, FindingStatus, Repository, Scan, ScanStatus

# Motores que corre el scan-worker (app/worker/job.py: default_engines).
ENGINE_NAMES = ["sast", "sca", "secrets", "crypto"]


class RepositoryIn(BaseModel):
    url: str


class RepositoryOut(BaseModel):
    id: str
    provider: Literal["github"]
    full_name: str
    url: str
    default_branch: str
    connected_at: datetime


class ScanOut(BaseModel):
    id: str
    repository_id: str
    status: ScanStatus
    engines: list[str]
    progress: float | None
    stage: str | None
    commit_sha: str | None
    created_at: datetime
    started_at: datetime
    finished_at: datetime | None
    duration_seconds: float | None
    risk_score: float | None
    grade: str | None
    error: str | None
    engine_errors: dict[str, str] | None


class AiTriageOut(BaseModel):
    is_false_positive: bool
    adjusted_severity: Severity
    explanation: str
    remediation: str


class FindingOut(BaseModel):
    id: str
    scan_id: str
    fingerprint: str
    engine: str
    rule_id: str
    title: str
    severity: Severity
    file_path: str
    line: int | None
    snippet: str
    description: str
    cwe: str | None
    cve: str | None
    metadata: dict
    status: FindingStatus
    triage: AiTriageOut | None


class FindingUpdate(BaseModel):
    status: FindingStatus


class ScanReportOut(BaseModel):
    """URLs firmadas para descargar los archivos del escaneo; null si no existe."""

    report_url: str | None
    cbom_url: str | None
    expires_in: int


def repository_out(repo: Repository) -> RepositoryOut:
    return RepositoryOut(
        id=str(repo.id),
        provider="github",
        full_name=repo.full_name,
        url=repo.url,
        default_branch=repo.default_branch or "main",
        connected_at=repo.created_at,
    )


def scan_out(scan: Scan) -> ScanOut:
    duration = None
    if scan.started_at and scan.finished_at:
        duration = round((scan.finished_at - scan.started_at).total_seconds(), 1)
    return ScanOut(
        id=str(scan.id),
        repository_id=str(scan.repository_id),
        status=scan.status,
        engines=ENGINE_NAMES,
        # El worker todavía no informa en qué etapa está: solo se sabe al terminar.
        progress=100 if scan.status == ScanStatus.COMPLETED else None,
        stage=None,
        commit_sha=scan.commit_sha,
        created_at=scan.created_at,
        # El frontend necesita una fecha aunque el escaneo siga en cola.
        started_at=scan.started_at or scan.created_at,
        finished_at=scan.finished_at,
        duration_seconds=duration,
        risk_score=scan.risk_score,
        grade=scan.grade,
        error=scan.error,
        engine_errors=scan.engine_errors,
    )


def finding_out(finding: Finding) -> FindingOut:
    triage = None
    if finding.ai_is_false_positive is not None:
        triage = AiTriageOut(
            is_false_positive=finding.ai_is_false_positive,
            adjusted_severity=finding.ai_adjusted_severity or finding.severity,
            explanation=finding.ai_explanation or "",
            remediation=finding.ai_remediation or "",
        )
    return FindingOut(
        id=str(finding.id),
        scan_id=str(finding.scan_id),
        fingerprint=finding.fingerprint,
        engine=finding.engine,
        rule_id=finding.rule_id,
        title=finding.title,
        severity=finding.severity,
        file_path=finding.file_path,
        line=finding.line,
        snippet=finding.snippet,
        description=finding.description,
        cwe=finding.cwe,
        cve=finding.cve,
        metadata=finding.metadata_ or {},
        status=finding.status,
        triage=triage,
    )
