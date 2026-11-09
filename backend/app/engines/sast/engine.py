"""Motor SAST: código inseguro (Módulo C)."""

import logging
from concurrent.futures import ThreadPoolExecutor

from app.engines.base import Engine, Finding
from app.engines.sast.bandit import run_bandit
from app.engines.sast.findings import bandit_to_findings
from app.engines.sast.semgrep import run_semgrep, semgrep_to_findings

logger = logging.getLogger(__name__)


class SastEngine(Engine):
    """Analiza Python con Bandit y JavaScript/TypeScript con Semgrep, en paralelo.

    Si falla una de las dos herramientas se devuelven los hallazgos de la otra;
    solo si fallan las dos se lanza el error, y el orquestador lo registra.
    Sin Semgrep instalado (fuera de la imagen del worker) solo corre Bandit.
    """

    name = "sast"

    def scan(self, repo_path: str) -> list[Finding]:
        with ThreadPoolExecutor(max_workers=2, thread_name_prefix="sast") as pool:
            bandit = pool.submit(lambda: bandit_to_findings(run_bandit(repo_path), repo_path))
            semgrep = pool.submit(_semgrep_findings, repo_path)

        findings: list[Finding] = []
        errors: list[Exception] = []
        ran = 0
        for name, future in (("Bandit", bandit), ("Semgrep", semgrep)):
            try:
                result = future.result()
            except Exception as error:
                logger.warning("SAST: %s falló: %s", name, error)
                errors.append(error)
                ran += 1
                continue
            if result is not None:
                findings.extend(result)
                ran += 1
        # Si fallaron todas las herramientas que se pudieron correr, el motor falló.
        if errors and len(errors) == ran:
            raise errors[0]
        return findings


def _semgrep_findings(repo_path: str) -> list[Finding] | None:
    """Hallazgos de Semgrep, o None si no está instalado."""
    output = run_semgrep(repo_path)
    if output is None:
        logger.info("SAST: Semgrep no está instalado, se analiza solo Python")
        return None
    return semgrep_to_findings(output, repo_path)
