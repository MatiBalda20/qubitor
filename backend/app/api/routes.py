"""Endpoints REST de repositorios, escaneos y hallazgos (Módulo A).

Todas las consultas filtran por la organización del usuario: un recurso de otra
organización responde 404, igual que uno que no existe, para no revelar nada.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.auth import CurrentUser, get_current_user
from app.api.schemas import (
    FindingOut,
    FindingUpdate,
    RepositoryIn,
    RepositoryOut,
    ScanOut,
    finding_out,
    repository_out,
    scan_out,
)
from app.engines.base import Severity
from app.models.database import get_db
from app.models.models import Finding, FindingStatus, Repository, Scan, ScanStatus
from app.orchestrator.risk import grade, risk_score
from app.worker.clone import is_github_url
from app.worker.queue import JOB_TIMEOUT_SECONDS, MAX_RETRIES, enqueue_scan

logger = logging.getLogger(__name__)

router = APIRouter()

HISTORY_LIMIT = 50
_ACTIVE = (ScanStatus.QUEUED, ScanStatus.RUNNING)
# Más de lo que pueden durar todos los intentos de un trabajo, con margen para la espera en la cola.
STALE_AFTER = timedelta(seconds=JOB_TIMEOUT_SECONDS * (MAX_RETRIES + 1)) + timedelta(minutes=15)
_SEVERITY_RANK = {severity: rank for rank, severity in enumerate(Severity)}


@router.get("/repositories", response_model=list[RepositoryOut])
def list_repositories(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    repos = db.scalars(
        select(Repository)
        .where(Repository.organization_id == user.organization_id)
        .order_by(Repository.created_at.desc())
    )
    return [repository_out(repo) for repo in repos]


@router.post("/repositories", response_model=RepositoryOut, status_code=status.HTTP_201_CREATED)
def connect_repository(
    body: RepositoryIn,
    response: Response,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Conecta un repo público de GitHub. Si ya estaba conectado, lo devuelve."""
    url = _normalize_url(body.url)
    if not is_github_url(url):
        raise HTTPException(422, "Solo se pueden conectar repos públicos de GitHub")

    # GitHub no distingue mayúsculas en owner/repo: Acme/Demo y acme/demo son el mismo.
    repo = db.scalar(
        select(Repository).where(
            Repository.organization_id == user.organization_id, func.lower(Repository.url) == url.lower()
        )
    )
    if repo is not None:
        response.status_code = status.HTTP_200_OK
        return repository_out(repo)

    repo = Repository(
        organization_id=user.organization_id,
        full_name=url.removeprefix("https://github.com/"),
        url=url,
    )
    db.add(repo)
    db.commit()
    return repository_out(repo)


@router.post("/repositories/{repository_id}/scans", response_model=ScanOut, status_code=status.HTTP_202_ACCEPTED)
def start_scan(
    repository_id: uuid.UUID,
    response: Response,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Crea el escaneo y lo encola. Responde al instante; el worker lo ejecuta."""
    repo = _get_repository(db, repository_id, user)

    # Si el repo ya tiene un escaneo en cola o en curso, se devuelve ese.
    active = db.scalar(
        select(Scan).where(Scan.repository_id == repo.id, Scan.status.in_(_ACTIVE)).order_by(Scan.created_at.desc())
    )
    if active is not None and not _is_stale(active):
        response.status_code = status.HTTP_200_OK
        return scan_out(active)
    if active is not None:
        # El worker se cayó o el trabajo venció sin avisar: sin esto, el repo no
        # se podría volver a escanear nunca.
        active.status = ScanStatus.FAILED
        active.error = "El escaneo no terminó a tiempo: el worker se detuvo o superó el tiempo límite"
        active.finished_at = datetime.now(timezone.utc)

    scan = Scan(repository_id=repo.id, status=ScanStatus.QUEUED)
    db.add(scan)
    db.commit()
    try:
        enqueue_scan(str(scan.id), repo.url)
    except Exception as error:
        logger.exception("No se pudo encolar el escaneo %s", scan.id)
        scan.status = ScanStatus.FAILED
        scan.error = "No se pudo encolar el escaneo"
        db.commit()
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "La cola de escaneos no está disponible") from error
    return scan_out(scan)


@router.get("/repositories/{repository_id}/history", response_model=list[ScanOut])
def repository_history(
    repository_id: uuid.UUID, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Escaneos del repo, del más nuevo al más viejo."""
    repo = _get_repository(db, repository_id, user)
    scans = db.scalars(
        select(Scan).where(Scan.repository_id == repo.id).order_by(Scan.created_at.desc()).limit(HISTORY_LIMIT)
    )
    return [scan_out(scan) for scan in scans]


@router.get("/scans/{scan_id}", response_model=ScanOut)
def get_scan(scan_id: uuid.UUID, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return scan_out(_get_scan(db, scan_id, user))


@router.get("/scans/{scan_id}/findings", response_model=list[FindingOut])
def get_scan_findings(
    scan_id: uuid.UUID, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Hallazgos del escaneo, del más grave al menos grave."""
    scan = _get_scan(db, scan_id, user)
    findings = sorted(
        scan.findings,
        key=lambda f: (_SEVERITY_RANK[_effective_severity(f)], f.file_path, f.line or 0),
    )
    return [finding_out(finding) for finding in findings]


@router.patch("/findings/{finding_id}", response_model=FindingOut)
def update_finding(
    finding_id: uuid.UUID,
    body: FindingUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Marca un hallazgo como resuelto, falso positivo o abierto, y recalcula el score."""
    finding = db.scalar(
        select(Finding)
        .join(Scan)
        .join(Repository)
        .where(Finding.id == finding_id, Repository.organization_id == user.organization_id)
    )
    if finding is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No existe el hallazgo")

    finding.status = body.status
    scan = finding.scan
    if scan.status == ScanStatus.COMPLETED:
        scan.risk_score = risk_score(_effective_severity(f) for f in scan.findings if _counts_toward_score(f))
        scan.grade = grade(scan.risk_score)
    db.commit()
    return finding_out(finding)


def _get_repository(db: Session, repository_id: uuid.UUID, user: CurrentUser) -> Repository:
    repo = db.scalar(
        select(Repository).where(Repository.id == repository_id, Repository.organization_id == user.organization_id)
    )
    if repo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No existe el repositorio")
    return repo


def _get_scan(db: Session, scan_id: uuid.UUID, user: CurrentUser) -> Scan:
    scan = db.scalar(
        select(Scan).join(Repository).where(Scan.id == scan_id, Repository.organization_id == user.organization_id)
    )
    if scan is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No existe el escaneo")
    return scan


def _is_stale(scan: Scan) -> bool:
    """True si el escaneo lleva más tiempo activo del que puede durar."""
    since = scan.started_at or scan.created_at
    return since is not None and datetime.now(timezone.utc) - since > STALE_AFTER


def _normalize_url(url: str) -> str:
    return url.strip().removesuffix("/").removesuffix(".git")


def _effective_severity(finding: Finding) -> Severity:
    """La severidad ajustada por la IA si hubo triage (igual que el frontend)."""
    return finding.ai_adjusted_severity or finding.severity


def _counts_toward_score(finding: Finding) -> bool:
    """Solo cuentan los abiertos que la IA no marcó como falso positivo."""
    return finding.status == FindingStatus.OPEN and not finding.ai_is_false_positive
