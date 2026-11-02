"""Traducción de la salida JSON de Bandit al contrato común (`Finding`)."""

import re
from pathlib import Path

from app.engines.base import Finding, Severity
from app.engines.sast.bandit import IGNORED_DIRS

# El contrato limita el fragmento de código a 5 líneas.
MAX_SNIPPET_LINES = 5

_BANDIT_SEVERITY = {
    "HIGH": Severity.HIGH,
    "MEDIUM": Severity.MEDIUM,
    "LOW": Severity.LOW,
}

# Reglas que Bandit marca como medium pero que son ejecución de código o
# inyección directa: se suben a high (la IA puede ajustarlas después).
_SEVERITY_OVERRIDES = {
    "B102": Severity.HIGH,  # exec
    "B307": Severity.HIGH,  # eval
    "B608": Severity.HIGH,  # SQL armada con strings
}

# Con confianza baja se baja un nivel para no inflar el Risk Score.
_ONE_LEVEL_DOWN = {
    Severity.CRITICAL: Severity.HIGH,
    Severity.HIGH: Severity.MEDIUM,
    Severity.MEDIUM: Severity.LOW,
    Severity.LOW: Severity.LOW,
    Severity.INFO: Severity.INFO,
}

_TITLES = {
    "B102": "Uso de exec()",
    "B105": "Contraseña escrita en el código",
    "B106": "Contraseña escrita en el código",
    "B107": "Contraseña escrita en el código",
    "B301": "Deserialización insegura con pickle",
    "B307": "Uso de eval()",
    "B501": "Validación de certificados TLS deshabilitada",
    "B506": "Carga insegura de YAML",
    "B602": "Comando de shell con shell=True",
    "B605": "Comando de shell armado con strings",
    "B608": "Consulta SQL armada con strings (posible inyección SQL)",
}

# Prefijo "N " con el número de línea que Bandit agrega a cada línea del código.
_LINE_NUMBER = re.compile(r"^\d+ ?", re.MULTILINE)

# Textos y bytes entre comillas, con prefijos como f, b o r.
_STRING_LITERAL = re.compile(r"""([rRbBuUfF]{0,2})("{3}|'{3}|"|')(?:\\.|(?!\2).)*?\2""")


def bandit_to_findings(output: dict, repo_path: str) -> list[Finding]:
    """Convierte la salida de Bandit en hallazgos del contrato común."""
    root = Path(repo_path).resolve()
    findings = []
    for result in output.get("results", []):
        file_path = _relative_path(result.get("filename", ""), root)
        if file_path is None:
            continue
        findings.append(_to_finding(result, file_path))
    return findings


def _to_finding(result: dict, file_path: str) -> Finding:
    test_id = result["test_id"]
    cwe_id = (result.get("issue_cwe") or {}).get("id")
    return Finding(
        engine="sast",
        rule_id=f"sast.bandit.{test_id}",
        title=_TITLES.get(test_id, result.get("test_name", test_id).replace("_", " ").capitalize()),
        severity=_severity(result),
        file_path=file_path,
        line=result.get("line_number"),
        snippet=_snippet(result.get("code", "")),
        description=result.get("issue_text", ""),
        cwe=f"CWE-{cwe_id}" if cwe_id else None,
        metadata={
            "tool": "bandit",
            "bandit_severity": result.get("issue_severity"),
            "confidence": result.get("issue_confidence"),
            "more_info": result.get("more_info"),
        },
    )


def _severity(result: dict) -> Severity:
    test_id = result["test_id"]
    severity = _SEVERITY_OVERRIDES.get(test_id) or _BANDIT_SEVERITY.get(
        result.get("issue_severity"), Severity.LOW
    )
    if result.get("issue_confidence") == "LOW":
        severity = _ONE_LEVEL_DOWN[severity]
    return severity


def _relative_path(filename: str, root: Path) -> str | None:
    """Ruta relativa a la raíz del repo, o None si el archivo no debe reportarse.

    Se descartan los enlaces simbólicos y lo que quede fuera del repo: un repo
    malicioso podría apuntar a archivos del servidor y filtrar su contenido en
    el snippet.
    """
    # En Windows Bandit usa "\" como separador; se normaliza para que funcione igual en Linux.
    path = root / filename.replace("\\", "/")
    if path.is_symlink():
        return None
    try:
        relative = path.resolve().relative_to(root)
    except ValueError:
        return None
    if IGNORED_DIRS & set(relative.parts):
        return None
    return relative.as_posix()


def _snippet(code: str) -> str:
    """Código sin números de línea, con los textos enmascarados y máx. 5 líneas."""
    lines = _LINE_NUMBER.sub("", code).rstrip("\n").splitlines()[:MAX_SNIPPET_LINES]
    return "\n".join(_STRING_LITERAL.sub(r"\1\2***\2", line) for line in lines)
