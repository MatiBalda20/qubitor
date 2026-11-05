import math
import re
from pathlib import Path

from app.engines.base import Engine, Finding, Severity

# Directorios y extensiones que no contienen código fuente analizable
IGNORED_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build"}
IGNORED_EXTENSIONS = {".lock", ".bin", ".exe", ".dll", ".so", ".pdf", ".png", ".jpg"}

# Patrones extraídos de la tabla técnica del Módulo C
PATTERNS = {
    "secrets.aws": (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS Access Key expuesta"),
    "secrets.github": (re.compile(r"gh[pousr]_[A-Za-z0-9]{36}"), "GitHub Token expuesto"),
    "secrets.google": (re.compile(r"AIza[0-9A-Za-z_\-]{35}"), "Google API Key expuesta"),
    "secrets.slack": (re.compile(r"xox[baprs]-[0-9A-Za-z\-]{10,}"), "Slack Token expuesto"),
    "secrets.private_key": (re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"), "Clave privada expuesta")
}

# Detección genérica: variable sospechosa asignada a un string largo
GENERIC_VAR_REGEX = re.compile(r"(?i)(?:key|secret|token|password)\s*[:=]\s*['\"]([^'\"]{20,})['\"]")


def shannon_entropy(data: str) -> float:
    """Calcula la entropía de Shannon para evaluar la aleatoriedad de un string."""
    if not data:
        return 0.0
    entropy = 0.0
    for char in set(data):
        p_x = float(data.count(char)) / len(data)
        entropy -= p_x * math.log2(p_x)
    return entropy


class SecretsEngine(Engine):
    name = "secrets"

    def scan(self, repo_path: str) -> list[Finding]:
        repo = Path(repo_path).resolve()
        findings: list[Finding] = []

        for file_path in repo.rglob("*"):
            if self._should_ignore(file_path, repo):
                continue

            try:
                content = file_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            relative_path = file_path.relative_to(repo).as_posix()
            findings.extend(self._scan_content(content, relative_path))

        return findings

    def _should_ignore(self, path: Path, repo_root: Path) -> bool:
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(repo_root):
            return True
        if path.suffix in IGNORED_EXTENSIONS:
            return True
        relative_parts = path.relative_to(repo_root).parts
        if any(part in IGNORED_DIRS for part in relative_parts):
            return True
        return False

    def _scan_content(self, content: str, file_path: str) -> list[Finding]:
        findings = []
        lines = content.splitlines()

        for line_number, line in enumerate(lines, start=1):
            # 1. Búsqueda por patrones conocidos
            for rule_id, (regex, title) in PATTERNS.items():
                for match in regex.finditer(line):
                    secret_value = match.group(0)
                    findings.append(self._create_finding(rule_id, title, file_path, line_number, line, secret_value))

            # 2. Búsqueda genérica por alta entropía
            for match in GENERIC_VAR_REGEX.finditer(line):
                secret_value = match.group(1)
                if shannon_entropy(secret_value) > 4.5:
                    findings.append(self._create_finding(
                        "secrets.generic.entropy", 
                        "Secreto genérico de alta entropía expuesto", 
                        file_path, 
                        line_number, 
                        line, 
                        secret_value
                    ))

        return findings

    def _create_finding(self, rule_id: str, title: str, file_path: str, line_number: int, full_line: str, secret: str) -> Finding:
        # Enmascara el secreto en el código fuente para evitar fugas en el reporte
        masked_line = full_line.replace(secret, "***")
        
        return Finding(
            engine=self.name,
            rule_id=rule_id,
            title=title,
            severity=Severity.CRITICAL,
            file_path=file_path,
            line=line_number,
            snippet=masked_line.strip()[:200],
            description=f"Se detectó un secreto en código fuente. Rotá la credencial inmediatamente.",
            cwe="CWE-798",
            metadata={"secret_type": rule_id.split(".")[-1]}
        )