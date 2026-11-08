"""Etapa y porcentaje del escaneo en curso, para la barra de progreso del frontend.

El worker los guarda en los metadatos del trabajo en Redis (no en la base: son
datos de vida corta y cambian varias veces por escaneo) y la API los lee al
responder `GET /scans/{id}`. Las etapas son las de la sección 2 del plan, las
mismas que `SCAN_STAGES` en frontend/src/types/Scan.ts.
"""

import logging

from redis import Redis
from rq import get_current_job
from rq.job import Job
from rq.serializers import JSONSerializer

from app.worker.queue import get_connection, job_id

logger = logging.getLogger(__name__)

# Porcentaje al empezar cada etapa. Los motores son lo que más tarda.
STAGE_PROGRESS = {
    "clone": 5,
    "engines": 20,
    "normalize": 75,
    "triage": 80,
    "score": 88,
    "persist": 95,
}


def report_stage(stage: str) -> None:
    """Guarda la etapa en el trabajo actual. Si Redis falla, el escaneo sigue igual."""
    job = get_current_job()
    if job is None:
        return
    job.meta.update(stage=stage, progress=STAGE_PROGRESS[stage])
    try:
        job.save_meta()
    except Exception:
        logger.warning("No se pudo guardar la etapa %s del trabajo %s", stage, job.id, exc_info=True)


def read_progress(scan_id: str, connection: Redis | None = None) -> tuple[str | None, int | None]:
    """Etapa y porcentaje que informó el worker, o (None, None) si no se saben."""
    try:
        job = Job.fetch(job_id(scan_id), connection=connection or get_connection(), serializer=JSONSerializer)
    except Exception:
        # El trabajo venció en Redis o Redis no responde: la barra queda sin porcentaje.
        return None, None
    stage = job.meta.get("stage")
    if stage not in STAGE_PROGRESS:
        return None, None
    return stage, job.meta.get("progress")
