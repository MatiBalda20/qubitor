"""Ejecución de los motores en paralelo (Módulo A).

Si un motor falla o se pasa del tiempo, se registra el error y se siguen
usando los resultados de los demás: un escaneo parcial es mejor que ninguno.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, wait
from dataclasses import dataclass, field

from app.engines.base import Engine, Finding

logger = logging.getLogger(__name__)

# El contrato pide a cada motor terminar en 60 s; se deja un margen.
TIMEOUT_SECONDS = 70


@dataclass
class EnginesResult:
    findings: list[Finding] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)  # nombre del motor → error


def run_engines(engines: list[Engine], repo_path: str, timeout: float = TIMEOUT_SECONDS) -> EnginesResult:
    """Ejecuta todos los motores sobre `repo_path` al mismo tiempo."""
    result = EnginesResult()
    if not engines:
        return result

    pool = ThreadPoolExecutor(max_workers=len(engines), thread_name_prefix="engine")
    futures = {pool.submit(engine.scan, repo_path): engine.name for engine in engines}
    done, pending = wait(futures, timeout=timeout)
    # No se espera a los motores colgados: un hilo no se puede cortar desde
    # afuera, pero el escaneo sigue y el worker libera el proceso al terminar.
    pool.shutdown(wait=False, cancel_futures=True)

    for future, name in futures.items():
        if future in pending:
            result.errors[name] = f"superó el límite de {timeout:g} s"
        elif (error := future.exception()) is not None:
            result.errors[name] = f"{type(error).__name__}: {error}"
        else:
            result.findings.extend(future.result())

    for name, error in result.errors.items():
        logger.warning("El motor %s falló: %s", name, error)
    return result
