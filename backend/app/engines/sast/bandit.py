"""Ejecución de Bandit sobre el código Python del repo (Módulo C, SAST).

Bandit corre como subproceso con salida JSON; este archivo solo lo ejecuta y
devuelve esa salida. La traducción a `Finding` está en `findings.py`.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

# Configuración propia: el .bandit del repo analizado no se lee (QUB-01).
CONFIG_FILE = Path(__file__).parent / "rules" / "bandit.ini"

# Carpetas que no son código del usuario: dependencias, entornos y builds.
IGNORED_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build"}

# Bandit tiene que terminar antes que el límite de 60 s del contrato.
TIMEOUT_SECONDS = 50

# Bandit sale con 0 si no encontró nada y con 1 si encontró problemas.
_OK_EXIT_CODES = {0, 1}

# Variables mínimas para que Python y Bandit corran sin heredar credenciales del worker.
_INHERITED_ENV = ("PATH", "HOME", "SYSTEMROOT", "TEMP", "TMP", "USERPROFILE")


class BanditError(Exception):
    """Bandit no pudo ejecutarse o devolvió una salida inválida."""


def bandit_env() -> dict[str, str]:
    """Entorno mínimo para el subproceso de Bandit, sin secretos del worker."""
    return {name: os.environ[name] for name in _INHERITED_ENV if name in os.environ}


def run_bandit(repo_path: str, timeout: int = TIMEOUT_SECONDS) -> dict:
    """Ejecuta Bandit sobre `repo_path` y devuelve su salida JSON.

    Se ejecuta con el repo como directorio de trabajo, así las rutas de la
    salida quedan relativas a la raíz del repo. Con `-I` Python no agrega el
    directorio actual a `sys.path`, evitando que el repo inyecte módulos.

    El repo tampoco puede silenciar hallazgos (QUB-01): `--ini` usa la
    configuración de Qubitor en lugar del `.bandit` del repo, e `--ignore-nosec`
    reporta también las líneas marcadas con `# nosec`. Un falso positivo real se
    marca en la app.
    """
    exclude = ",".join(f"*/{name}/*" for name in sorted(IGNORED_DIRS))
    command = [
        sys.executable, "-I", "-m", "bandit", "-r", ".", "-f", "json", "-q", "-x", exclude,
        "--ini", str(CONFIG_FILE), "--ignore-nosec",
    ]
    try:
        process = subprocess.run(
            command,
            cwd=repo_path,
            env=bandit_env(),
            capture_output=True,
            text=True,
            timeout=timeout,
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