"""Motor de configuración insegura (Módulo C — ampliación 30/11).

Analiza Dockerfile, docker-compose, nginx y Terraform (.tf) para detectar
contenedores como root, TLS 1.0/1.1, cipher suites débiles y puertos o reglas
de red expuestas.
"""

import re
from pathlib import Path

from app.engines.base import Engine, Finding, Severity

IGNORED_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build"}
MAX_FILE_BYTES = 1_000_000

_DOCKER_ROOT = re.compile(r"^\s*USER\s+(?:root|0)(?:\s|$)", re.IGNORECASE)
_DOCKER_USER = re.compile(r"^\s*USER\s+\S+", re.IGNORECASE)

_NGINX_OLD_TLS = re.compile(r"ssl_protocols\b[^;]*\bTLSv1(?:\.1)?\b", re.IGNORECASE)
_NGINX_WEAK_CIPHER = re.compile(r"ssl_ciphers\b[^;]*\b(?:RC4|MD5|DES|3DES|NULL|EXPORT|aNULL)\b", re.IGNORECASE)

_COMPOSE_PORT = re.compile(r"""^\s*-\s*["']?(?:0\.0\.0\.0:)?(\d+):\d+""")
_COMPOSE_PRIVILEGED = re.compile(r"^\s*privileged\s*:\s*true\b", re.IGNORECASE)

_TF_PUBLIC_CIDR = re.compile(r"""["']0\.0\.0\.0/0["']""")
_TF_OLD_TLS = re.compile(r"""TLSv1(?:\.1)?|ELBSecurityPolicy-2016-08""", re.IGNORECASE)


class ConfigEngine(Engine):
    name = "config"

    def scan(self, repo_path: str) -> list[Finding]:
        repo = Path(repo_path).resolve()
        findings: list[Finding] = []

        for path in sorted(repo.rglob("*")):
            if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(repo):
                continue
            rel = path.relative_to(repo)
            if any(part in IGNORED_DIRS for part in rel.parts):
                continue
            try:
                if path.stat().st_size > MAX_FILE_BYTES:
                    continue
                content = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            rel_posix = rel.as_posix()
            name_lower = path.name.lower()

            if name_lower == "dockerfile" or name_lower.startswith("dockerfile.") or path.suffix.lower() == ".dockerfile":
                findings.extend(self._scan_dockerfile(content, rel_posix))
            elif name_lower.startswith("docker-compose") and path.suffix.lower() in (".yml", ".yaml"):
                findings.extend(self._scan_compose(content, rel_posix))
            elif "nginx" in name_lower or path.suffix.lower() == ".conf":
                findings.extend(self._scan_nginx(content, rel_posix))
            elif path.suffix.lower() == ".tf":
                findings.extend(self._scan_terraform(content, rel_posix))

        return findings

    def _scan_dockerfile(self, content: str, file_path: str) -> list[Finding]:
        findings: list[Finding] = []
        lines = content.splitlines()
        has_user = False

        for i, line in enumerate(lines, start=1):
            if _DOCKER_ROOT.match(line):
                has_user = True
                findings.append(self._finding(
                    rule="config.docker.root-user",
                    title="Contenedor ejecutándose como root en Dockerfile",
                    severity=Severity.HIGH,
                    file_path=file_path,
                    line=i,
                    snippet=line.strip()[:200],
                    description="Ejecutar el contenedor como root amplía el impacto ante un escape de contenedor. Definí un usuario sin privilegios con USER.",
                    cwe="CWE-250",
                ))
            elif _DOCKER_USER.match(line):
                has_user = True

        if not has_user and any(l.strip().upper().startswith("FROM ") for l in lines):
            findings.append(self._finding(
                rule="config.docker.missing-user",
                title="Dockerfile sin directiva USER (corre como root por defecto)",
                severity=Severity.MEDIUM,
                file_path=file_path,
                line=1,
                snippet=lines[0].strip()[:200] if lines else "",
                description="Sin una directiva USER explícita, Docker ejecuta el proceso principal como root.",
                cwe="CWE-250",
            ))
        return findings

    def _scan_nginx(self, content: str, file_path: str) -> list[Finding]:
        findings: list[Finding] = []
        for i, line in enumerate(content.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if _NGINX_OLD_TLS.search(line):
                findings.append(self._finding(
                    rule="config.nginx.tls-insecure",
                    title="Protocolo TLS 1.0/1.1 habilitado en nginx",
                    severity=Severity.HIGH,
                    file_path=file_path,
                    line=i,
                    snippet=stripped[:200],
                    description="TLS 1.0 y 1.1 están deprecados y son vulnerables a ataques de downgrade. Permití solo TLSv1.2 y TLSv1.3.",
                    cwe="CWE-327",
                ))
            if _NGINX_WEAK_CIPHER.search(line):
                findings.append(self._finding(
                    rule="config.nginx.weak-cipher",
                    title="Cipher suite débil configurada en nginx",
                    severity=Severity.HIGH,
                    file_path=file_path,
                    line=i,
                    snippet=stripped[:200],
                    description="Se detectaron algoritmos rotos (RC4/DES/MD5/NULL) en ssl_ciphers. Usá suites modernas con AEAD (AES-GCM/ChaCha20).",
                    cwe="CWE-327",
                ))
        return findings

    def _scan_compose(self, content: str, file_path: str) -> list[Finding]:
        findings: list[Finding] = []
        for i, line in enumerate(content.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if _COMPOSE_PRIVILEGED.match(line):
                findings.append(self._finding(
                    rule="config.compose.privileged",
                    title="Contenedor en modo privileged en docker-compose",
                    severity=Severity.HIGH,
                    file_path=file_path,
                    line=i,
                    snippet=stripped[:200],
                    description="privileged: true otorga acceso casi total al host. Eliminá esta opción y usá capabilities mínimas.",
                    cwe="CWE-250",
                ))
            elif match := _COMPOSE_PORT.match(line):
                port = match.group(1)
                findings.append(self._finding(
                    rule="config.compose.exposed-port",
                    title=f"Puerto {port} expuesto públicamente en docker-compose",
                    severity=Severity.MEDIUM,
                    file_path=file_path,
                    line=i,
                    snippet=stripped[:200],
                    description="El puerto queda enlazado a todas las interfaces (0.0.0.0). Si es un servicio interno, restringilo a 127.0.0.1.",
                    cwe="CWE-284",
                ))
        return findings

    def _scan_terraform(self, content: str, file_path: str) -> list[Finding]:
        findings: list[Finding] = []
        for i, line in enumerate(content.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith(("#", "//")):
                continue
            if _TF_PUBLIC_CIDR.search(line):
                findings.append(self._finding(
                    rule="config.terraform.public-cidr",
                    title="Regla de red abierta a 0.0.0.0/0 en Terraform",
                    severity=Severity.HIGH,
                    file_path=file_path,
                    line=i,
                    snippet=stripped[:200],
                    description="Permitir tráfico desde 0.0.0.0/0 expone el recurso a todo Internet. Restringí el CIDR a rangos conocidos.",
                    cwe="CWE-284",
                ))
            if _TF_OLD_TLS.search(line):
                findings.append(self._finding(
                    rule="config.terraform.tls-insecure",
                    title="Política TLS insegura en Terraform",
                    severity=Severity.HIGH,
                    file_path=file_path,
                    line=i,
                    snippet=stripped[:200],
                    description="Actualizá la política TLS a TLSv1.2 o TLSv1.3.",
                    cwe="CWE-327",
                ))
        return findings

    def _finding(
        self,
        *,
        rule: str,
        title: str,
        severity: Severity,
        file_path: str,
        line: int,
        snippet: str,
        description: str,
        cwe: str,
    ) -> Finding:
        return Finding(
            engine="sast",
            rule_id=rule,
            title=title,
            severity=severity,
            file_path=file_path,
            line=line,
            snippet=snippet,
            description=description,
            cwe=cwe,
            metadata={"tool": "config"},
        )