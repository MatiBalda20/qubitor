"""Recorrido de los archivos del repo escaneado (Módulo D).

Lo usan pqc.py, certs.py y el motor SCA. El repo no es de confianza: no se
siguen enlaces simbólicos que salgan del repo (podrían filtrar archivos del
servidor en el reporte) y se saltean las carpetas de dependencias y de build.
"""

from collections.abc import Callable, Iterator
from pathlib import Path

# Carpetas que no son código del usuario: dependencias, entornos y builds.
IGNORED_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build"}


def iter_repo_files(repo: Path, match: Callable[[Path], bool]) -> Iterator[Path]:
    """Los archivos del repo que cumplen `match`, en orden alfabético."""
    repo_root = repo.resolve()
    for path in sorted(repo.rglob("*")):
        if not match(path):
            continue
        if path.is_symlink() or not path.resolve().is_relative_to(repo_root):
            continue
        if not path.is_file() or any(part in IGNORED_DIRS for part in path.relative_to(repo).parts):
            continue
        yield path


def read_text(path: Path) -> str | None:
    """El contenido del archivo, o None si no se puede leer.

    El contrato pide no lanzar excepciones por archivos ilegibles: se saltean.
    """
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
