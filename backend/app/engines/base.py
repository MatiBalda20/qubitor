"""Contrato común entre motores (Módulo A).

Todos los motores (SAST, SCA, secretos y criptografía) devuelven hallazgos con
este mismo formato, así el orquestador los integra sin conocer cómo funciona
cada uno. Cualquier cambio en este archivo requiere un Pull Request aprobado
por todo el equipo.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum


class Severity(str, Enum):
    """Escala de severidad unificada (sección 3 del plan de desarrollo)."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class Finding:
    """Un hallazgo de un motor, tal como lo recibe el orquestador."""

    engine: str  # "sast" | "sca" | "secrets" | "crypto"
    rule_id: str  # ej. "crypto.classic.weak-hash.md5"
    title: str  # texto corto para el dashboard
    severity: Severity
    file_path: str  # relativo a la raíz del repo
    line: int | None
    snippet: str  # máx. 5 líneas, secretos ENMASCARADOS
    description: str
    cwe: str | None = None  # ej. "CWE-327"
    cve: str | None = None  # solo SCA
    metadata: dict = field(default_factory=dict)


class Engine(ABC):
    """Interfaz que implementa cada motor."""

    name: str

    @abstractmethod
    def scan(self, repo_path: str) -> list[Finding]:
        """Analiza el repo clonado en `repo_path` y devuelve sus hallazgos.

        No lanza excepciones por archivos ilegibles: los saltea.
        Debe terminar en menos de 60 s para un repo de 50 MB.
        """
