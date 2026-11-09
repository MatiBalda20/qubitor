"""Clonado superficial de un repo de GitHub (etapa 1 del pipeline).

El repo es código ajeno que no es de confianza: solo se aceptan URLs de
GitHub, no se crean enlaces simbólicos y se corta el clonado si supera el
límite. Para un repo privado (Módulo E) se pasa el token OAuth del usuario
como cabecera HTTP por variables de entorno de Git: no queda en la URL, en
los argumentos del proceso ni en `.git/config`. Git recibe un entorno mínimo,
sin las credenciales del worker.
"""

import base64
import os
import re
import shutil
import stat
import subprocess
import time
from pathlib import Path

MAX_REPO_BYTES = 50 * 1024 * 1024
CLONE_TIMEOUT_SECONDS = 120
_POLL_SECONDS = 0.5

# fullmatch: con `match` y `$`, una URL con un salto de línea al final pasaba la validación.
_GITHUB_URL = re.compile(r"https://github\.com/(?!\.)[\w.-]+/(?!\.)[\w.-]+?(\.git)?/?")

# Variables del entorno que Git necesita para correr; el resto (credenciales del
# worker como DATABASE_URL o REDIS_URL) no se le pasa.
_INHERITED_ENV = ("PATH", "HOME", "SYSTEMROOT", "TEMP", "TMP", "USERPROFILE")


class CloneError(Exception):
    """Falla transitoria del clonado: se puede reintentar."""


class CloneRejected(CloneError):
    """El repo no se va a poder clonar nunca: no tiene sentido reintentar."""


def is_github_url(url: str) -> bool:
    """True si es la URL de un repo de GitHub que se puede clonar."""
    return bool(_GITHUB_URL.fullmatch(url))


def clone_repository(url: str, destination: str, token: str | None = None) -> str:
    """Clona el último commit de `url` en `destination` y devuelve su SHA.

    `token` es el token OAuth de GitHub del usuario, solo para repos privados.
    """
    if not is_github_url(url):
        raise CloneRejected("Solo se pueden escanear URLs de GitHub")
    _run_clone(_clone_command(url, destination), destination, env=git_env(token))
    return subprocess.run(
        ["git", "-C", destination, "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True, timeout=10, env=git_env(),
    ).stdout.strip()


def git_env(token: str | None = None) -> dict[str, str]:
    """Entorno mínimo para Git, con el token como cabecera si se pasa uno.

    GIT_CONFIG_COUNT/KEY/VALUE agregan configuración solo para este proceso
    (Git 2.31+), así el token no queda escrito en ningún archivo. Se ignora la
    configuración global y del sistema para que ningún credential helper lo guarde.
    """
    env = {name: os.environ[name] for name in _INHERITED_ENV if name in os.environ}
    env |= {
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_LFS_SKIP_SMUDGE": "1",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "LANG": "C",
    }
    if token:
        credentials = base64.b64encode(f"x-access-token:{token}".encode()).decode()
        env |= {
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "http.https://github.com/.extraheader",
            "GIT_CONFIG_VALUE_0": f"Authorization: Basic {credentials}",
        }
    return env


def remove_tree(path: str) -> None:
    """Borra el clon. Qubitor no conserva el código de los usuarios."""
    for root, _, files in os.walk(path):
        for name in files:
            file_path = os.path.join(root, name)
            if not os.path.islink(file_path):
                # En Windows Git deja archivos de solo lectura en .git.
                os.chmod(file_path, stat.S_IWRITE)
    shutil.rmtree(path, ignore_errors=True)


def _clone_command(url: str, destination: str) -> list[str]:
    return [
        "git",
        "-c", "core.symlinks=false",
        "-c", "protocol.allow=never",
        "-c", "protocol.https.allow=always",
        "clone", "--depth", "1", "--single-branch", "--no-tags", "--no-recurse-submodules",
        "--", url, destination,
    ]


def _run_clone(command: list[str], destination: str, env: dict[str, str] | None = None) -> None:
    """Ejecuta el clonado midiendo cuánto ocupa, para cortarlo si se pasa."""
    env = env if env is not None else git_env()
    process = subprocess.Popen(command, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    deadline = time.monotonic() + CLONE_TIMEOUT_SECONDS
    try:
        while process.poll() is None:
            if time.monotonic() > deadline:
                raise CloneError(f"El clonado superó el límite de {CLONE_TIMEOUT_SECONDS} s")
            if _size_of(destination) > MAX_REPO_BYTES:
                raise CloneRejected("El repo supera el límite de 50 MB")
            time.sleep(_POLL_SECONDS)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()

    stderr = process.stderr.read() if process.stderr else ""
    if process.returncode != 0:
        if "not found" in stderr.lower() or "could not read username" in stderr.lower():
            raise CloneRejected("El repo no existe o Qubitor no tiene acceso")
        raise CloneError(f"git clone terminó con código {process.returncode}")
    if _size_of(destination) > MAX_REPO_BYTES:
        raise CloneRejected("El repo supera el límite de 50 MB")


def _size_of(path: str) -> int:
    total = 0
    for file in Path(path).rglob("*"):
        try:
            if file.is_file() and not file.is_symlink():
                total += file.stat().st_size
        except OSError:
            continue  # Git está creando y borrando archivos mientras se mide
    return total
