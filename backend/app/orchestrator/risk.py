"""Risk Score del repositorio y nota A–F (sección 5 del plan de desarrollo)."""

from collections.abc import Iterable

from app.engines.base import Severity

SEVERITY_WEIGHTS = {
    Severity.CRITICAL: 10,
    Severity.HIGH: 5,
    Severity.MEDIUM: 2,
    Severity.LOW: 0.5,
    Severity.INFO: 0,
}

# Puntaje mínimo de cada nota, de mejor a peor.
GRADE_THRESHOLDS = [(90, "A"), (75, "B"), (60, "C"), (40, "D")]


def risk_score(severities: Iterable[Severity]) -> float:
    """100 menos la suma de los pesos, con piso en 0.

    Recibe solo las severidades de los hallazgos que cuentan: abiertos y no
    marcados como falso positivo. El que llama decide cuáles son.
    """
    penalty = sum(SEVERITY_WEIGHTS[Severity(severity)] for severity in severities)
    return max(0.0, 100.0 - penalty)


def grade(score: float) -> str:
    """Nota A–F: A ≥ 90 · B ≥ 75 · C ≥ 60 · D ≥ 40 · F < 40."""
    for minimum, letter in GRADE_THRESHOLDS:
        if score >= minimum:
            return letter
    return "F"
