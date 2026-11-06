"""Motor SAST: código inseguro (Módulo C)."""

from app.engines.base import Engine, Finding
from app.engines.sast.bandit import run_bandit
from app.engines.sast.findings import bandit_to_findings


class SastEngine(Engine):
    """Analiza el código Python con Bandit.

    Si Bandit no puede ejecutarse, lanza `BanditError`: el orquestador lo
    registra y sigue con los demás motores. Semgrep (JavaScript) se suma
    cuando se confirme que entra en la memoria del plan free de Render.
    """

    name = "sast"

    def scan(self, repo_path: str) -> list[Finding]:
        return bandit_to_findings(run_bandit(repo_path), repo_path)
