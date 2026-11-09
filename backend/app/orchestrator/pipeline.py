"""Pipeline de análisis de un repo ya clonado (Módulo A).

Une las etapas 2, 3 y 5 del auditor: motores en paralelo, normalización y
Risk Score. El clonado (Módulo E), el triage con IA (Módulo E, entre la
normalización y el score) y la persistencia los coordina el scan-worker.
"""

import time
from dataclasses import dataclass, field

from app.engines.base import Engine, Finding
from app.orchestrator.normalize import deduplicate
from app.orchestrator.risk import grade, risk_score
from app.orchestrator.runner import run_engines


@dataclass
class ScanResult:
    findings: dict[str, Finding]  # fingerprint → hallazgo
    errors: dict[str, str]  # nombre del motor → error
    risk_score: float
    grade: str
    duration_seconds: float
    engine_count: int
    # Módulo E: evaluación de la IA por fingerprint y resumen ejecutivo. Vacíos sin triage.
    triage: dict = field(default_factory=dict)
    summary: dict | None = None

    @property
    def failed(self) -> bool:
        """True si fallaron todos los motores: no hay nada que mostrar."""
        return self.engine_count > 0 and len(self.errors) == self.engine_count


def analyze_repository(repo_path: str, engines: list[Engine]) -> ScanResult:
    start = time.monotonic()
    engines_result = run_engines(engines, repo_path)
    findings = deduplicate(engines_result.findings)
    # Al terminar el escaneo todos los hallazgos están abiertos y sin triage.
    score = risk_score(finding.severity for finding in findings.values())
    return ScanResult(
        findings=findings,
        errors=engines_result.errors,
        risk_score=score,
        grade=grade(score),
        duration_seconds=round(time.monotonic() - start, 2),
        engine_count=len(engines),
    )
