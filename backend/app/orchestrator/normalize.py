"""Normalización de hallazgos: fingerprint y deduplicación (Módulo A)."""

import hashlib

from app.engines.base import Finding, Severity

# De mayor a menor gravedad, para quedarse con la peor si hay duplicados.
SEVERITY_ORDER = [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]


def fingerprint(finding: Finding) -> str:
    """Hash de motor + regla + archivo + línea.

    Identifica el mismo problema dentro de un escaneo y entre escaneos (para
    el historial de hallazgos nuevos y resueltos). No incluye el snippet ni
    la severidad: si cambian, sigue siendo el mismo hallazgo.
    """
    key = "|".join([finding.engine, finding.rule_id, finding.file_path, str(finding.line or "")])
    return hashlib.sha256(key.encode()).hexdigest()


def deduplicate(findings: list[Finding]) -> dict[str, Finding]:
    """Deja un hallazgo por fingerprint, el de mayor severidad.

    Devuelve un dict fingerprint → hallazgo, en el orden en que aparecieron.
    """
    unique: dict[str, Finding] = {}
    for finding in findings:
        key = fingerprint(finding)
        current = unique.get(key)
        if current is None or _rank(finding) < _rank(current):
            unique[key] = finding
    return unique


def _rank(finding: Finding) -> int:
    return SEVERITY_ORDER.index(finding.severity)
