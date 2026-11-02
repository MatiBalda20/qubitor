"""Lectura de los archivos de dependencias de un repo (Módulo D, SCA).

Solo se toman versiones exactas: con un rango (`requests>=2.0`, `^4.17.0`) no
se sabe qué versión está instalada, y reportarla daría falsos positivos.
"""

import re
from dataclasses import dataclass


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
