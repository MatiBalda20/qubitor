"""Cola de escaneos sobre Redis con RQ (Módulo A).

La API publica un trabajo y responde al instante; el scan-worker lo toma en otro
servicio. Los trabajos que agotan sus reintentos quedan en la cola de errores
(`FailedJobRegistry` de RQ).
"""

from functools import lru_cache

from redis import Redis
from rq import Queue, Retry
from rq.job import Job
from rq.serializers import JSONSerializer

from app.config import redis_url

QUEUE_NAME = "scans"
SCAN_JOB = "app.worker.job.run_scan"

# Reintentos ante fallas transitorias. Sin intervalo: esperar requiere el
# scheduler de RQ, que consulta Redis todo el tiempo y gasta la cuota de Upstash.
MAX_RETRIES = 2

JOB_TIMEOUT_SECONDS = 300  # clonado + motores + triage
RESULT_TTL_SECONDS = 60 * 60
FAILURE_TTL_SECONDS = 7 * 24 * 60 * 60  # para poder revisar la cola de errores


@lru_cache(maxsize=1)
def get_connection() -> Redis:
    """Una sola conexión por proceso: la API la usa en cada consulta de progreso,
    y abrir una nueva cada vez repetiría el handshake TLS con Upstash."""
    return Redis.from_url(redis_url(), socket_connect_timeout=5, health_check_interval=30)


def job_id(scan_id: str) -> str:
    return f"scan-{scan_id}"


def get_queue(connection: Redis | None = None) -> Queue:
    # JSON en lugar de pickle: los datos de un trabajo nunca ejecutan código al leerse.
    return Queue(QUEUE_NAME, connection=connection or get_connection(), serializer=JSONSerializer)


def enqueue_scan(scan_id: str, repo_url: str, connection: Redis | None = None) -> Job:
    """Publica un escaneo una sola vez: si ya se encoló, devuelve ese trabajo.

    RQ no rechaza un id repetido: lo vuelve a poner en la cola y el escaneo
    corre dos veces. Por eso se marca en Redis con SET NX, que es atómico
    aunque lleguen dos pedidos al mismo tiempo.
    """
    connection = connection or get_connection()
    queue = get_queue(connection)
    job_key = job_id(scan_id)
    if not connection.set(f"qubitor:enqueued:{job_key}", 1, nx=True, ex=FAILURE_TTL_SECONDS):
        existing = queue.fetch_job(job_key)
        if existing is not None:
            return existing
        # La marca quedó pero el trabajo ya venció en Redis: se puede volver a encolar.
    return queue.enqueue_call(
        SCAN_JOB,
        args=(scan_id, repo_url),
        job_id=job_key,
        timeout=JOB_TIMEOUT_SECONDS,
        result_ttl=RESULT_TTL_SECONDS,
        failure_ttl=FAILURE_TTL_SECONDS,
        retry=Retry(max=MAX_RETRIES),
    )
