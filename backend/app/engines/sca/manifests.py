"""Lectura de los archivos de dependencias de un repo (Módulo D, SCA).

Solo se toman versiones exactas: con un rango (`requests>=2.0`, `^4.17.0`) no
se sabe qué versión está instalada, y reportarla daría falsos positivos.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path

from app.engines.crypto.files import iter_repo_files, read_text


@dataclass(frozen=True)
class Dependency:
    name: str
    version: str
    ecosystem: str      # como lo nombra OSV: "PyPI" | "npm"
    file_path: str      # relativo a la raíz del repo
    line: int | None


# nombre[extras]==versión ; marcadores
# Ej.: "requests==2.19.0", "uvicorn[standard]==0.30.1 ; python_version >= '3.10'"
_REQUIREMENT = re.compile(
    r"^(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)"
    r"\s*(?:\[[^\]]*\])?"
    r"\s*==\s*(?P<version>[A-Za-z0-9.!+_-]+)"
    r"\s*(?:;.*)?$"
)


def parse_requirements(text: str, file_path: str) -> list[Dependency]:
    dependencies: list[Dependency] = []
    for number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.split("#", 1)[0].strip()
        match = _REQUIREMENT.match(line)
        if match is None:
            continue
        dependencies.append(Dependency(
            name=match["name"],
            version=match["version"],
            ecosystem="PyPI",
            file_path=file_path,
            line=number,
        ))
    return dependencies


# Versión exacta de npm: "4.17.4" o "1.0.0-beta.2". Sin ^, ~, >, *, etc.
_EXACT_NPM_VERSION = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$")


def parse_package_json(text: str, file_path: str) -> list[Dependency]:
    data = _load_json(text)
    if data is None:
        return []
    dependencies: list[Dependency] = []
    for section in ("dependencies", "devDependencies"):
        packages = data.get(section)
        if not isinstance(packages, dict):
            continue
        for name, version in packages.items():
            if isinstance(version, str) and _EXACT_NPM_VERSION.match(version):
                dependencies.append(Dependency(
                    name=name,
                    version=version,
                    ecosystem="npm",
                    file_path=file_path,
                    line=_line_of(text, f'"{name}"'),
                ))
    return dependencies


def parse_package_lock(text: str, file_path: str) -> list[Dependency]:
    """Lee las versiones instaladas de un package-lock.json (formatos v1, v2 y v3)."""
    data = _load_json(text)
    if data is None:
        return []

    found: dict[tuple[str, str], str] = {}   # (nombre, versión) → texto a buscar para la línea
    packages = data.get("packages")
    if isinstance(packages, dict):
        # v2 y v3: {"node_modules/lodash": {"version": "4.17.4"}, ...}
        for key, info in packages.items():
            if "node_modules/" not in key or not isinstance(info, dict):
                continue
            name = key.rsplit("node_modules/", 1)[1]
            version = info.get("version")
            if isinstance(version, str):
                found.setdefault((name, version), f'"{key}"')
    else:
        # v1: {"dependencies": {"lodash": {"version": "4.17.4"}, ...}}
        legacy = data.get("dependencies")
        for name, info in (legacy if isinstance(legacy, dict) else {}).items():
            version = info.get("version") if isinstance(info, dict) else None
            if isinstance(version, str):
                found.setdefault((name, version), f'"{name}"')

    return [
        Dependency(name, version, "npm", file_path, _line_of(text, needle))
        for (name, version), needle in found.items()
    ]


def _load_json(text: str) -> dict | None:
    try:
        data = json.loads(text)
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def _line_of(text: str, needle: str) -> int | None:
    index = text.find(needle)
    if index == -1:
        return None
    return text.count("\n", 0, index) + 1


def find_dependencies(repo_path: str) -> list[Dependency]:
    """Busca los archivos de dependencias en todo el repo y los lee.

    Si una carpeta tiene package-lock.json, se usa ese y no su package.json:
    el lock tiene las versiones realmente instaladas.
    """
    repo = Path(repo_path)
    dependencies: list[Dependency] = []
    for path in iter_repo_files(repo, lambda p: _parser_for(p.name) is not None):
        if path.name == "package.json" and (path.parent / "package-lock.json").is_file():
            continue
        text = read_text(path)
        if text is not None:
            dependencies.extend(_parser_for(path.name)(text, path.relative_to(repo).as_posix()))
    return dependencies


def _parser_for(file_name: str):
    if file_name == "package.json":
        return parse_package_json
    if file_name == "package-lock.json":
        return parse_package_lock
    if file_name.startswith("requirements") and file_name.endswith(".txt"):
        return parse_requirements
    return None
