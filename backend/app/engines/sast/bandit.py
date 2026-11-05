"""Ejecución de Bandit sobre el código Python del repo (Módulo C, SAST).

Bandit corre como subproceso con salida JSON; este archivo solo lo ejecuta y
devuelve esa salida. La traducción a `Finding` está en `findings.py`.
"""

import json
import subprocess
import sys

# Carpetas que no son código del usuario: dependencias, entornos y builds.
IGNORED_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build"}

# Bandit tiene que terminar antes que el límite de 60 s del contrato.
TIMEOUT_SECONDS = 50

# Bandit sale con 0 si no encontró nada y con 1 si encontró problemas.
_OK_EXIT_CODES = {0, 1}


class BanditError(Exception):
    """Bandit no pudo ejecutarse o devolvió una salida inválida."""


def run_bandit(repo_path: str, timeout: int = TIMEOUT_SECONDS) -> dict:
    """Ejecuta Bandit sobre `repo_path` y devuelve su salida JSON.

    Se ejecuta con el repo como directorio de trabajo, así las rutas de la
    salida quedan relativas a la raíz del repo.
    """
    exclude = ",".join(f"*/{name}/*" for name in sorted(IGNORED_DIRS))
    command = [sys.executable, "-m", "bandit", "-r", ".", "-f", "json", "-q", "-x", exclude]
    try:
        process = subprocess.run(
            command, cwd=repo_path, capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired as error:
        raise BanditError(f"Bandit superó el límite de {timeout} s") from error
    except OSError as error:
        raise BanditError(f"No se pudo ejecutar Bandit: {error}") from error

    if process.returncode not in _OK_EXIT_CODES:
        raise BanditError(f"Bandit terminó con código {process.returncode}: {process.stderr.strip()}")
    try:
        return json.loads(process.stdout)
    except json.JSONDecodeError as error:
        raise BanditError("Bandit devolvió una salida que no es JSON") from error
