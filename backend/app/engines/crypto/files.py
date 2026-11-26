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


# Los primeros bytes que se miran para decidir si un archivo es binario (mismo criterio que git).
_BINARY_SNIFF_BYTES = 8000


def read_text(path: Path) -> str | None:
    """El contenido del archivo como texto, o None si no se puede leer o es binario.

    El contrato pide no lanzar excepciones por archivos ilegibles: se saltean.
    Un archivo que no es UTF-8 válido (por ejemplo, código heredado en latin-1)
    no se descarta: se decodifica como latin-1, que acepta cualquier byte y
    conserva el ASCII, así los patrones siguen funcionando (QUB-01/F-06).
    """
    try:
        data = path.read_bytes()
    except OSError:
        return None
    return decode_source(data)


def decode_source(data: bytes) -> str | None:
    """Texto de un archivo fuente: UTF-8, o latin-1 si no es UTF-8. None si es binario."""
    if b"\0" in data[:_BINARY_SNIFF_BYTES]:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin-1")
