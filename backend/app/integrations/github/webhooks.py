"""Escaneo automático en cada push (Módulo E): endpoint interno para el Worker de webhooks.

GitHub manda el evento al Cloudflare Worker (`infra/webhook-worker`), que verifica
la firma de GitHub y reenvía acá solo lo necesario, firmado con un secreto
compartido (INTERNAL_WEBHOOK_SECRET). El Worker no habla con Redis: tener
REDIS_URL alcanza para ejecutar código en el scan-worker, así que la cola sigue
siendo exclusiva de la API (Módulo A).

Firma: `X-Qubitor-Signature: sha256=<hex>` = HMAC-SHA256(secreto, "<timestamp>.<cuerpo>"),
con `X-Qubitor-Timestamp` en segundos. Se rechaza todo pedido de más de 5 minutos
para que una firma capturada no se pueda reusar.
"""

import hashlib
import hmac
import logging
import os
import re
import time

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.routes import _ACTIVE, _is_stale
from app.models.database import get_db
from app.models.models import Repository, Scan, ScanStatus
from app.worker.clone import is_github_url
from app.worker.queue import enqueue_scan, get_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal/github", tags=["github"], include_in_schema=False)

MAX_BODY_BYTES = 16 * 1024
MAX_CLOCK_SKEW_SECONDS = 300
DELIVERY_TTL_SECONDS = 24 * 60 * 60
MIN_SECRET_LENGTH = 32

_DELIVERY_ID = re.compile(r"[0-9A-Za-z-]{1,64}")
_COMMIT_SHA = re.compile(r"[0-9a-f]{40}")


class PushEvent(BaseModel):
    delivery_id: str = Field(max_length=64)
    repository_url: str = Field(max_length=300)
    commit_sha: str = Field(max_length=40)
    ref: str = Field(max_length=255)


async def raw_body(request: Request) -> bytes:
    """El cuerpo tal cual llegó: la firma se calcula sobre estos bytes."""
    body = await request.body()
    if len(body) > MAX_BODY_BYTES:
        raise HTTPException(413, "El cuerpo es demasiado grande")
    return body


def internal_secret() -> str:
    secret = os.getenv("INTERNAL_WEBHOOK_SECRET", "")
    if len(secret) < MIN_SECRET_LENGTH:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Los webhooks no están configurados")
    return secret


def verify_signature(secret: str, timestamp: str | None, signature: str | None, body: bytes, now: float | None = None) -> bool:
    if not timestamp or not signature or not timestamp.isdigit():
        return False
    now = time.time() if now is None else now
    if abs(now - int(timestamp)) > MAX_CLOCK_SKEW_SECONDS:
        return False
    expected = hmac.new(secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)


def mark_delivery(delivery_id: str) -> bool:
    """True la primera vez que se ve una entrega; False si ya se procesó (SET NX en Redis)."""
    return bool(get_connection().set(f"qubitor:webhook:delivery:{delivery_id}", 1, nx=True, ex=DELIVERY_TTL_SECONDS))


@router.post("/push", status_code=status.HTTP_202_ACCEPTED)
def github_push(request: Request, body: bytes = Depends(raw_body), db: Session = Depends(get_db)):
    secret = internal_secret()
    if not verify_signature(
        secret, request.headers.get("X-Qubitor-Timestamp"), request.headers.get("X-Qubitor-Signature"), body
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Firma inválida")

    try:
        event = PushEvent.model_validate_json(body)
    except ValidationError:
        raise HTTPException(422, "Evento inválido") from None
    url = event.repository_url.removesuffix("/").removesuffix(".git")
    if (
        not _DELIVERY_ID.fullmatch(event.delivery_id)
        or not _COMMIT_SHA.fullmatch(event.commit_sha)
        or not is_github_url(url)
    ):
        raise HTTPException(422, "Evento inválido")

    try:
        first_time = mark_delivery(event.delivery_id)
    except Exception:
        logger.exception("Webhook: no se pudo registrar la entrega %s", event.delivery_id)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "La cola de escaneos no está disponible") from None
    if not first_time:
        return {"duplicate": True, "scans": [], "skipped": 0}

    repos = db.scalars(select(Repository).where(func.lower(Repository.url) == url.lower())).all()
    started, skipped = [], 0
    for repo in repos:
        scan_id = _start_scan(db, repo)
        if scan_id is None:
            skipped += 1
        else:
            started.append(scan_id)
    logger.info(
        "Webhook %s: push a %s, %d escaneos lanzados, %d ya en curso",
        event.delivery_id, url, len(started), skipped,
    )
    return {"duplicate": False, "scans": started, "skipped": skipped}


def _start_scan(db: Session, repo: Repository) -> str | None:
    """Encola un escaneo del repo, salvo que ya haya uno activo (mismo criterio que la API)."""
    active = db.scalar(
        select(Scan).where(Scan.repository_id == repo.id, Scan.status.in_(_ACTIVE)).order_by(Scan.created_at.desc())
    )
    if active is not None and not _is_stale(active):
        return None
    if active is not None:
        active.status = ScanStatus.FAILED
        active.error = "El escaneo no terminó a tiempo: el worker se detuvo o superó el tiempo límite"

    scan = Scan(repository_id=repo.id, status=ScanStatus.QUEUED)
    db.add(scan)
    db.commit()
    try:
        enqueue_scan(str(scan.id), repo.url)
    except Exception:
        logger.exception("Webhook: no se pudo encolar el escaneo %s", scan.id)
        scan.status = ScanStatus.FAILED
        scan.error = "No se pudo encolar el escaneo"
        db.commit()
        return None
    return str(scan.id)
