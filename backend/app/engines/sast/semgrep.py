"""SAST de JavaScript y TypeScript con Semgrep y reglas propias (Módulo C).

Semgrep corre como subproceso con salida JSON, igual que Bandit. Solo está
instalado en la imagen del scan-worker (no tiene versión para Windows): si no
está, se saltea y el SAST sigue con Bandit.
"""

import json
import logging
import os
import re
import subprocess
import tempfile
from pathlib import Path

from app.engines.base import Finding, Severity
from app.engines.sast.bandit import IGNORED_DIRS
from app.engines.sast.findings import MAX_SNIPPET_LINES, _relative_path

logger = logging.getLogger(__name__)

RULES_FILE = Path(__file__).parent / "rules" / "javascript.yml"
JS_PATTERNS = ["*.js", "*.jsx", "*.mjs", "*.cjs", "*.ts", "*.tsx"]

# Corre junto a Bandit dentro del límite de 60 s del contrato.
TIMEOUT_SECONDS = 45
# Tope de memoria por archivo de Semgrep: el plan free de Render tiene 512 MB en total.
MAX_MEMORY_MB = 300
# Los archivos minificados o generados enormes no se analizan.
MAX_TARGET_BYTES = 1_000_000

_SEVERITY = {"ERROR": Severity.HIGH, "WARNING": Severity.MEDIUM, "INFO": Severity.LOW}
_OK_EXIT_CODES = {0, 1}

# Textos entre comillas simples, dobles o backticks (template literals de JS).
_JS_STRING = re.compile(r"""(['"`])(?:\\.|(?!\1).)*?\1""")


class SemgrepError(Exception):
    """Semgrep no pudo ejecutarse o devolvió una salida inválida."""


def semgrep_enabled() -> bool:
    """SEMGREP_ENABLED=false lo apaga sin tocar código, por ejemplo si en Render falta memoria."""
    return os.getenv("SEMGREP_ENABLED", "true").strip().lower() != "false"


def run_semgrep(repo_path: str, timeout: int = TIMEOUT_SECONDS) -> dict | None:
    """Salida JSON de Semgrep sobre el repo, o None si no está instalado o está apagado."""
    if not semgrep_enabled():
        return None
    command = [
        "semgrep", "scan",
        "--config", str(RULES_FILE),
        "--json", "--quiet", "--metrics=off", "--disable-version-check",
        "--timeout", "20",
        "--max-memory", str(MAX_MEMORY_MB),
        # Un solo proceso: por defecto Semgrep lanza uno por CPU (12 en Render) y,
        # sumado a los otros motores, el worker se queda sin memoria.
        "--jobs", "1",
        "--max-target-bytes", str(MAX_TARGET_BYTES),
    ]
    for pattern in JS_PATTERNS:
        command += ["--include", pattern]
    for name in sorted(IGNORED_DIRS):
        command += ["--exclude", name]
    command.append(".")

    # Semgrep escribe su configuración en HOME: el usuario del worker no tiene uno propio.
    with tempfile.TemporaryDirectory(prefix="semgrep-home-") as home:
        env = {**os.environ, "HOME": home, "XDG_CONFIG_HOME": home, "SEMGREP_SEND_METRICS": "off"}
        try:
            process = subprocess.run(
                command, cwd=repo_path, env=env, capture_output=True, text=True, timeout=timeout
            )
        except FileNotFoundError:
            return None
        except subprocess.TimeoutExpired as error:
            raise SemgrepError(f"Semgrep superó el límite de {timeout} s") from error

    if process.returncode not in _OK_EXIT_CODES:
        raise SemgrepError(f"Semgrep terminó con código {process.returncode}: {process.stderr.strip()[-300:]}")
    try:
        return json.loads(process.stdout)
    except json.JSONDecodeError as error:
        raise SemgrepError("Semgrep devolvió una salida que no es JSON") from error


def semgrep_to_findings(output: dict, repo_path: str) -> list[Finding]:
    """Convierte la salida de Semgrep en hallazgos del contrato común."""
    root = Path(repo_path).resolve()
    findings = []
    for result in output.get("results", []):
        file_path = _relative_path(result.get("path", ""), root)
        if file_path is None:
            continue
        extra = result.get("extra") or {}
        metadata = extra.get("metadata") or {}
        start = (result.get("start") or {}).get("line")
        end = (result.get("end") or {}).get("line") or start
        findings.append(
            Finding(
                engine="sast",
                rule_id=f"sast.semgrep.{metadata.get('qubitor_id') or result.get('check_id', 'regla')}",
                title=metadata.get("title") or extra.get("message", "Código inseguro"),
                severity=_SEVERITY.get(extra.get("severity"), Severity.LOW),
                file_path=file_path,
                line=start,
                snippet=_snippet(root / file_path, start, end),
                description=extra.get("message", ""),
                cwe=metadata.get("cwe"),
                metadata={"tool": "semgrep", "semgrep_severity": extra.get("severity")},
            )
        )
    return findings


def _snippet(path: Path, start: int | None, end: int | None) -> str:
    """Las líneas del hallazgo leídas del archivo, con los textos enmascarados.

    Semgrep sin cuenta ya no incluye el código en su salida ("requires login"),
    así que se lee del repo clonado.
    """
    if not start:
        return ""
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    selected = lines[start - 1 : min(end or start, start + MAX_SNIPPET_LINES - 1)]
    return "\n".join(_JS_STRING.sub(r"\1***\1", line).rstrip() for line in selected)
