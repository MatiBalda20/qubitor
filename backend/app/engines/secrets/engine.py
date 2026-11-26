import math
import re
import subprocess
import time
from pathlib import Path

from app.engines.base import Engine, Finding, Severity
from app.worker.clone import MAX_REPO_BYTES, _size_of, git_env

# Límites del análisis del historial de Git: el repo es ajeno y puede estar
# armado para agotar la memoria o el tiempo del worker (QUB-03).
HISTORY_MAX_COMMITS = 20
HISTORY_FETCH_TIMEOUT_SECONDS = 15
HISTORY_LOG_TIMEOUT_SECONDS = 15
HISTORY_MAX_OUTPUT_BYTES = 8 * 1024 * 1024
HISTORY_MAX_LINE_BYTES = 4096
# Git trata como binarios (no calcula su diff) los archivos más grandes que esto.
HISTORY_BIG_FILE_THRESHOLD = "1m"
_POLL_SECONDS = 0.2

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

        head_keys = {(f.rule_id, f.file_path, f.snippet) for f in findings}
        findings.extend(self._scan_git_history(repo, head_keys=head_keys))
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

    def _scan_git_history(
        self,
        repo: Path,
        max_commits: int = HISTORY_MAX_COMMITS,
        head_keys: set[tuple[str, str, str]] | None = None,
    ) -> list[Finding]:
        """Recorre los últimos commits para detectar secretos borrados pero aún en la historia.

        Si el historial no se puede analizar entero (supera los límites o git
        falla), se devuelve lo encontrado más un hallazgo `info` que lo avisa:
        "no encontré nada" y "no pude mirar" no pueden verse igual.
        """
        if not (repo / ".git").exists():
            return []

        try:
            count = _commit_count(repo)
            if count <= 1:
                problem = _deepen(repo, max_commits)
                if problem:
                    return [self._history_incomplete(problem)]
                count = _commit_count(repo)
            if count <= 1:
                return []  # el repo tiene un solo commit: no hay historial que mirar
        except (OSError, ValueError, subprocess.SubprocessError):
            return [self._history_incomplete("No se pudo consultar el historial de Git")]

        findings: list[Finding] = []
        try:
            problem = self._scan_log(repo, max_commits, head_keys or set(), findings)
        except (OSError, subprocess.SubprocessError):
            problem = "No se pudo leer el historial de Git"
        if problem:
            findings.append(self._history_incomplete(problem))
        return findings

    def _scan_log(
        self, repo: Path, max_commits: int, head_keys: set[tuple[str, str, str]], findings: list[Finding]
    ) -> str | None:
        """Lee `git log -p` en streaming con tope de bytes, de largo de línea y de tiempo.

        Devuelve None si leyó todo, o el motivo por el que cortó.
        """
        command = [
            "git", "-C", str(repo), "-c", f"core.bigFileThreshold={HISTORY_BIG_FILE_THRESHOLD}",
            "log", f"-n{max_commits}", "-p", "--no-color", "--no-ext-diff", "--no-textconv",
            "--pretty=format:COMMIT:%H",
        ]
        process = subprocess.Popen(command, env=git_env(), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        deadline = time.monotonic() + HISTORY_LOG_TIMEOUT_SECONDS
        problem = None
        total = 0
        hunk_re = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)")
        seen: set[tuple[str, str, str]] = set()
        current_commit = ""
        current_file = "git-history"
        current_line = 0
        try:
            assert process.stdout is not None
            while True:
                if time.monotonic() > deadline:
                    problem = f"El análisis del historial superó {HISTORY_LOG_TIMEOUT_SECONDS} s"
                    break
                chunk = process.stdout.readline(HISTORY_MAX_LINE_BYTES)
                if not chunk:
                    break
                total += len(chunk)
                if total > HISTORY_MAX_OUTPUT_BYTES:
                    problem = f"El historial supera {HISTORY_MAX_OUTPUT_BYTES // (1024 * 1024)} MB de cambios"
                    break
                if not chunk.endswith(b"\n"):
                    # Línea más larga que el tope (código minificado o datos): se saltea
                    # el resto sin cargarlo en memoria, contándolo en el total.
                    while True:
                        rest = process.stdout.readline(HISTORY_MAX_LINE_BYTES)
                        total += len(rest)
                        if not rest or rest.endswith(b"\n") or total > HISTORY_MAX_OUTPUT_BYTES:
                            break
                    if chunk.startswith(b"+") and not chunk.startswith(b"+++"):
                        current_line += 1
                    continue
                raw_line = chunk.decode("utf-8", errors="replace").rstrip("\r\n")

                if raw_line.startswith("COMMIT:"):
                    current_commit = raw_line.removeprefix("COMMIT:").strip()[:12]
                    continue
                if raw_line.startswith("+++ b/"):
                    current_file = raw_line.removeprefix("+++ b/").strip()
                    continue
                if hunk_match := hunk_re.match(raw_line):
                    current_line = int(hunk_match.group(1))
                    continue
                if raw_line.startswith(" "):
                    current_line += 1
                    continue
                if not raw_line.startswith("+") or raw_line.startswith("+++"):
                    continue

                line_num = current_line
                current_line += 1

                rel_path = Path(current_file)
                if any(part in IGNORED_DIRS for part in rel_path.parts) or rel_path.suffix.lower() in IGNORED_EXTENSIONS:
                    continue

                for f in self._scan_content(raw_line[1:], current_file):
                    key = (f.rule_id, current_file, f.snippet)
                    if key in seen or key in head_keys:
                        continue
                    seen.add(key)
                    findings.append(self._history_finding(f, current_file, line_num, current_commit))
        finally:
            if process.poll() is None:
                process.kill()
            process.wait()
        if problem is None and process.returncode != 0:
            problem = "git log terminó con error"
        return problem

    def _history_finding(self, f: Finding, file_path: str, line: int, commit: str) -> Finding:
        return Finding(
            engine=self.name,
            rule_id=f"{f.rule_id}.history",
            title=f"{f.title} (en historial de Git)",
            severity=Severity.CRITICAL,
            file_path=file_path,
            line=line or None,
            snippet=f.snippet,
            description=(
                f"Secreto detectado en el commit {commit}. Aunque haya sido borrado "
                "en un commit posterior, sigue expuesto en el historial de Git. Rotá la credencial inmediatamente."
            ),
            cwe="CWE-798",
            metadata={**f.metadata, "in_git_history": True, "commit": commit},
        )

    def _history_incomplete(self, reason: str) -> Finding:
        """Aviso visible de que el historial no se analizó entero (no penaliza el score)."""
        return Finding(
            engine=self.name,
            rule_id="secrets.history.incomplete",
            title="El historial de Git no se pudo analizar completo",
            severity=Severity.INFO,
            file_path=".git",
            line=None,
            snippet="",
            description=(
                f"{reason}. Puede haber secretos en commits anteriores que no se revisaron: "
                "el resultado del historial no es un escaneo limpio."
            ),
            metadata={"in_git_history": True, "reason": reason},
        )


def _commit_count(repo: Path) -> int:
    res = subprocess.run(
        ["git", "-C", str(repo), "rev-list", "--count", "HEAD"],
        env=git_env(),
        capture_output=True,
        text=True,
        timeout=5,
    )
    return int(res.stdout.strip() or "0") if res.returncode == 0 else 0


def _deepen(repo: Path, max_commits: int) -> str | None:
    """Trae los commits anteriores de un clon superficial sin pasar el límite del clon.

    El clon se mide durante `git clone`, pero `fetch --deepen` puede bajar mucho
    más (QUB-03): se mide igual y se corta si el repo supera MAX_REPO_BYTES.
    Devuelve None si pudo, o el motivo por el que no.
    """
    process = subprocess.Popen(
        ["git", "-C", str(repo), "fetch", "--no-tags", "--no-recurse-submodules", f"--deepen={max_commits}"],
        env=git_env(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    deadline = time.monotonic() + HISTORY_FETCH_TIMEOUT_SECONDS
    try:
        while process.poll() is None:
            if time.monotonic() > deadline:
                return f"Traer el historial superó {HISTORY_FETCH_TIMEOUT_SECONDS} s"
            if _size_of(str(repo)) > MAX_REPO_BYTES:
                return "El historial supera el límite de 50 MB del repo"
            time.sleep(_POLL_SECONDS)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
    if process.returncode != 0:
        return "No se pudo traer el historial de Git"
    if _size_of(str(repo)) > MAX_REPO_BYTES:
        return "El historial supera el límite de 50 MB del repo"
    return None
