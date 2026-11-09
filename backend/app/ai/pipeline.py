"""Etapa de IA del pipeline: triage, Risk Score ajustado y resumen ejecutivo (Módulo E).

Va entre la normalización y la persistencia (sección 2 del plan). El scan-worker
llama a `apply_ai`, que nunca lanza: ante cualquier error devuelve el resultado
tal como llegó, con los hallazgos y el score de los motores.
"""

import dataclasses
import logging
import os

from app.ai.gemini import JsonModel, get_gemini_client
from app.ai.summary import build_summary
from app.ai.triage import TriageCache, TriageOutcome, triage_findings
from app.engines.base import Severity
from app.orchestrator.pipeline import ScanResult
from app.orchestrator.risk import grade, risk_score

logger = logging.getLogger(__name__)


def apply_ai(
    scan_id: str,
    result: ScanResult,
    model: JsonModel | None = None,
    cache: TriageCache | None = None,
) -> ScanResult:
    """Devuelve el resultado con el triage, el score recalculado y el resumen ejecutivo."""
    try:
        model = model if model is not None else _default_model()
        cache = cache if cache is not None else _default_cache(scan_id)
        outcome = triage_findings(result.findings, model, cache)
        score = adjusted_risk_score(result, outcome)
        summary = build_summary(result.findings, score, grade(score), outcome, model)
        logger.info(
            "Escaneo %s: triage %s (%d de %d evaluados, %d de la caché)",
            scan_id, outcome.status, len(outcome.results), outcome.candidates, outcome.from_cache,
        )
        return dataclasses.replace(
            result, triage=outcome.results, summary=summary, risk_score=score, grade=grade(score)
        )
    except Exception:
        logger.exception("Escaneo %s: falló la etapa de IA, se guardan los hallazgos sin triage", scan_id)
        return result


def adjusted_risk_score(result: ScanResult, outcome: TriageOutcome) -> float:
    """Risk Score con la severidad ajustada por la IA y sin los falsos positivos.

    Mismo criterio que la API al marcar un hallazgo (routes.py) y que lib/risk.ts.
    """
    severities = []
    for fp, finding in result.findings.items():
        evaluation = outcome.results.get(fp)
        if evaluation is not None and evaluation.is_false_positive:
            continue
        severities.append(evaluation.adjusted_severity if evaluation is not None else Severity(finding.severity))
    return risk_score(severities)


def _default_model() -> JsonModel | None:
    try:
        return get_gemini_client()
    except Exception:
        logger.exception("No se pudo crear el cliente de Gemini")
        return None


def _default_cache(scan_id: str) -> TriageCache | None:
    if not os.getenv("DATABASE_URL"):
        return None
    from app.ai.cache import SqlTriageCache

    return SqlTriageCache(scan_id)
