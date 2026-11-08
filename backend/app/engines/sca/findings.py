"""Conversión de vulnerabilidades de OSV en hallazgos del contrato (Módulo D, SCA)."""

import re

from app.engines.base import Finding, Severity
from app.engines.sca.manifests import Dependency

RULE_PREFIX = "sca.osv"
MAX_DETAILS_CHARS = 600

# Gravedad que calcula GitHub (`database_specific.severity`) → escala del equipo.
_GITHUB_SEVERITY = {
    "CRITICAL": Severity.CRITICAL,
    "HIGH": Severity.HIGH,
    "MODERATE": Severity.MEDIUM,
    "LOW": Severity.LOW,
}


def has_severity(vuln: dict) -> bool:
    return _github_severity(vuln) is not None


def vulnerability_to_finding(dep: Dependency, vuln: dict) -> Finding:
    fixed = fixed_version(vuln, dep)
    severity = _github_severity(vuln)
    upgrade_command = _upgrade_command(dep, fixed)

    summary = vuln.get("summary")
    title = f"{dep.name} {dep.version}: {summary}" if summary else (
        f"{dep.name} {dep.version} tiene una vulnerabilidad conocida"
    )
    details = (vuln.get("details") or "").strip()
    if len(details) > MAX_DETAILS_CHARS:
        details = details[:MAX_DETAILS_CHARS] + "…"
    remediation = (
        f"Actualizar a {fixed} o superior: `{upgrade_command}`."
        if fixed else "Todavía no hay una versión corregida publicada."
    )

    return Finding(
        engine="sca",
        # Con el ID en la regla, cada falla de un paquete tiene su propio fingerprint.
        rule_id=f"{RULE_PREFIX}.{vuln.get('id')}",
        title=title,
        # Sin gravedad de GitHub se asume media: hay una falla conocida, pero no
        # se sabe cuán grave es. Queda indicado en metadata["severity_source"].
        severity=severity or Severity.MEDIUM,
        file_path=dep.file_path,
        line=dep.line,
        snippet=_snippet(dep),
        description=f"{details}\n\n{remediation}".strip(),
        cwe=_first((vuln.get("database_specific") or {}).get("cwe_ids")),
        cve=_cve(vuln),
        metadata={
            "package": dep.name,
            "ecosystem": dep.ecosystem,
            "installed_version": dep.version,
            "fixed_version": fixed,
            "upgrade_command": upgrade_command,
            "vuln_id": vuln.get("id"),
            "aliases": vuln.get("aliases") or [],
            "cvss_vector": _cvss_vector(vuln),
            "severity_source": "github" if severity else "desconocida",
        },
    )


def fixed_version(vuln: dict, dep: Dependency) -> str | None:
    """La versión corregida más baja que sea mayor a la instalada.

    Una falla puede corregirse en varias ramas (por ejemplo 3.5 y 4.2): a quien
    tiene la 4.1 le sirve la 4.2, aunque la 3.5 sea menor.
    """
    installed = _version_key(dep.version)
    candidates: list[str] = []
    for affected in vuln.get("affected") or []:
        package = affected.get("package") or {}
        if package.get("ecosystem") != dep.ecosystem:
            continue
        if _normalize(package.get("name", "")) != _normalize(dep.name):
            continue
        for version_range in affected.get("ranges") or []:
            # Los rangos "GIT" usan hashes de commit, no versiones.
            if version_range.get("type") not in ("ECOSYSTEM", "SEMVER"):
                continue
            for event in version_range.get("events") or []:
                fixed = event.get("fixed")
                if fixed and _version_key(fixed) > installed:
                    candidates.append(fixed)
    return min(candidates, key=_version_key, default=None)


def _github_severity(vuln: dict) -> Severity | None:
    label = (vuln.get("database_specific") or {}).get("severity")
    return _GITHUB_SEVERITY.get(str(label).upper()) if label else None


def _cve(vuln: dict) -> str | None:
    ids = [vuln.get("id") or "", *(vuln.get("aliases") or [])]
    return next((i for i in ids if i.startswith("CVE-")), None)


def _cvss_vector(vuln: dict) -> str | None:
    for entry in vuln.get("severity") or []:
        if str(entry.get("type", "")).startswith("CVSS"):
            return entry.get("score")
    return None


def _upgrade_command(dep: Dependency, fixed: str | None) -> str | None:
    if fixed is None:
        return None
    if dep.ecosystem == "PyPI":
        return f"pip install {dep.name}=={fixed}"
    return f"npm install {dep.name}@{fixed}"


def _snippet(dep: Dependency) -> str:
    if dep.ecosystem == "PyPI":
        return f"{dep.name}=={dep.version}"
    return f'"{dep.name}": "{dep.version}"'


def _version_key(version: str) -> tuple[int, ...]:
    """Convierte "2.20.0" en (2, 20, 0) para poder comparar versiones como números.

    Se ignoran los sufijos de pre-release ("1.0.0-beta"): alcanza para elegir
    la versión corregida.
    """
    release = re.split(r"[-+]", version, maxsplit=1)[0]
    return tuple(int(part) for part in re.findall(r"\d+", release))


def _normalize(name: str) -> str:
    # En PyPI, "Flask", "flask" y "Fl_ask" son el mismo paquete.
    return re.sub(r"[-_.]+", "-", name).lower()


def _first(values) -> str | None:
    return values[0] if isinstance(values, list) and values else None
