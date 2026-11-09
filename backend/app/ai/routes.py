"""Endpoint del resumen ejecutivo de un escaneo (Módulo E).

La tarjeta del dashboard lo consulta para el último escaneo terminado. Como el
resto de la API, un escaneo de otra organización responde 404.
"""

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import CurrentUser, get_current_user
from app.models.database import get_db
from app.models.models import Repository, Scan

router = APIRouter(tags=["ia"])


class RiskOut(BaseModel):
    title: str
    impact: str
    priority: Literal["inmediata", "alta", "media"]


class ExecutiveSummaryOut(BaseModel):
    scan_id: str
    # False mientras el escaneo no terminó o si se escaneó antes de existir el resumen.
    available: bool
    status: Literal["good", "acceptable", "at_risk", "critical"] | None = None
    headline: str | None = None
    summary: str | None = None
    top_risks: list[RiskOut] = []
    priorities: list[str] = []
    generated_by: Literal["gemini", "heuristic"] | None = None
    generated_at: str | None = None
    # Cómo terminó el triage: completed, partial, quota_exceeded, unavailable, disabled o skipped.
    triage_status: str | None = None
    triage_reason: str | None = None


@router.get("/scans/{scan_id}/summary", response_model=ExecutiveSummaryOut)
def get_scan_summary(scan_id: uuid.UUID, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    scan = db.scalar(
        select(Scan).join(Repository).where(Scan.id == scan_id, Repository.organization_id == user.organization_id)
    )
    if scan is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No existe el escaneo")
    data = scan.ai_summary if isinstance(scan.ai_summary, dict) else None
    if not data:
        return ExecutiveSummaryOut(scan_id=str(scan.id), available=False)
    return ExecutiveSummaryOut(
        scan_id=str(scan.id),
        available=True,
        status=data.get("status"),
        headline=data.get("headline"),
        summary=data.get("summary"),
        top_risks=[risk for risk in data.get("top_risks") or [] if isinstance(risk, dict)],
        priorities=[p for p in data.get("priorities") or [] if isinstance(p, str)],
        generated_by=data.get("generated_by"),
        generated_at=data.get("generated_at"),
        triage_status=data.get("triage_status"),
        triage_reason=data.get("triage_reason"),
    )
