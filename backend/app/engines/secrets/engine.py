import math
import re
from pathlib import Path

from app.engines.base import Engine, Finding, Severity

IGNORED_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build"}
IGNORED_EXTENSIONS = {".lock", ".bin", ".exe", ".dll", ".so", ".pdf", ".png", ".jpg"}

PATTERNS = {
    "secrets.aws": (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS Access Key expuesta"),
    "secrets.github": (re.compile(r"gh[pousr]_[A-Za-z0-9]{36}"), "GitHub Token expuesto"),
    "secrets.google": (re.compile(r"AIza[0-9A-Za-z_\-]{35}"), "Google API Key expuesta"),
    "secrets.slack": (re.compile(r"xox[baprs]-[0-9A-Za-z\-]{10,}"), "Slack Token expuesto"),
    "secrets.private_key": (re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"), "Clave privada expuesta")
}

# Cuantificadores acotados: el motor analiza código ajeno y no puede tardar
# un tiempo cuadrático en una línea larga. Con comillas se toma el valor entero.
GENERIC_VAR_REGEX = re.compile(
    r"""(?i)(?:key|secret|token|password)[a-z0-9_]{0,40}['"]?\s{0,5}[:=]\s{0,5}"""
    r"""(?:'([^'\r\n]{20,})'|"([^"\r\n]{20,})"|([a-z0-9_+/=.\-]{20,}))"""
)

def shannon_entropy(data: str) -> float:
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
        if any(part in IGNORED_DIRS for part in path.relative_to(repo_root).parts):
            return True
        return False

    def _scan_content(self, content: str, file_path: str) -> list[Finding]:
        findings = []
        lines = content.splitlines()

        for line_number, line in enumerate(lines, start=1):
            line_secrets = [] # Tuplas de (valor_secreto, rule_id, title)
            
            # 1. Búsqueda por patrones conocidos
            for rule_id, (regex, title) in PATTERNS.items():
                for match in regex.finditer(line):
                    line_secrets.append((match.group(0), rule_id, title))

            # 2. Búsqueda genérica por alta entropía
            for match in GENERIC_VAR_REGEX.finditer(line):
                secret_value = match.group(match.lastindex)
                # Deduplicación: Si ya lo capturó un patrón específico, no lo agregamos como genérico
                if not any(s[0] == secret_value for s in line_secrets):
                    if shannon_entropy(secret_value) > 4.5:
                        line_secrets.append((secret_value, "secrets.generic.entropy", "Secreto genérico de alta entropía expuesto"))

            # 3. Creación de findings con snippet enmascarado globalmente para la línea
            if line_secrets:
                masked_line = line
                for secret_value, _, _ in line_secrets:
                    masked_line = masked_line.replace(secret_value, "***")
                
                snippet = masked_line.strip()[:200]
                
                for secret_value, rule_id, title in line_secrets:
                    findings.append(Finding(
                        engine=self.name,
                        rule_id=rule_id,
                        title=title,
                        severity=Severity.CRITICAL,
                        file_path=file_path,
                        line=line_number,
                        snippet=snippet,
                        description="Se detectó un secreto en código fuente. Rotá la credencial inmediatamente.",
                        cwe="CWE-798",
                        metadata={"secret_type": rule_id.split(".")[-1]}
                    ))

        return findings