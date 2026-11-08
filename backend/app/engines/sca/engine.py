"""Motor SCA: dependencias con vulnerabilidades conocidas (Módulo D)."""

from app.engines.base import Engine, Finding
from app.engines.sca.cache import default_osv_client
from app.engines.sca.findings import has_severity, vulnerability_to_finding
from app.engines.sca.manifests import find_dependencies
from app.engines.sca.osv import OsvClient


class ScaEngine(Engine):
    """Lee las dependencias del repo y consulta sus vulnerabilidades en OSV.

    Si OSV no responde, lanza `OsvError`: el orquestador lo registra y sigue
    con los demás motores.
    """

    name = "sca"

    def __init__(self, client: OsvClient | None = None):
        # Sin un cliente dado, usa OSV con la caché de KV si está configurada.
        self.client = client or default_osv_client()

    def scan(self, repo_path: str) -> list[Finding]:
        dependencies = find_dependencies(repo_path)
        if not dependencies:
            return []

        vuln_ids = self.client.query_batch(dependencies)

        # Cada vulnerabilidad se pide una sola vez, aunque afecte a varias dependencias.
        unique_ids = sorted({vuln_id for ids in vuln_ids for vuln_id in ids})
        details = self.client.get_vulns(unique_ids)

        findings: list[Finding] = []
        for dependency, ids in zip(dependencies, vuln_ids, strict=True):
            for vuln in _deduplicate([details[vuln_id] for vuln_id in ids]):
                findings.append(vulnerability_to_finding(dependency, vuln))
        return findings


def _deduplicate(vulns: list[dict]) -> list[dict]:
    """Deja una sola entrada por falla.

    OSV puede devolver la misma falla con varios IDs (GHSA-..., PYSEC-...) que
    se nombran entre sí como alias. Se prefiere la que trae la gravedad.
    """
    chosen: list[dict] = []
    seen: set[str] = set()
    for vuln in sorted(vulns, key=lambda v: not has_severity(v)):
        ids = {vuln.get("id"), *(vuln.get("aliases") or [])} - {None}
        if ids & seen:
            continue
        seen |= ids
        chosen.append(vuln)
    return chosen
