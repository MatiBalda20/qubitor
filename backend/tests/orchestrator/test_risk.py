import pytest

from app.engines.base import Severity
from app.orchestrator.risk import grade, risk_score


def test_sin_hallazgos_es_100():
    assert risk_score([]) == 100


def test_resta_el_peso_de_cada_severidad():
    severidades = [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]
    assert risk_score(severidades) == 100 - 10 - 5 - 2 - 0.5


def test_acepta_severidades_como_texto():
    assert risk_score(["high", "medium"]) == 93


def test_tiene_piso_en_cero():
    assert risk_score([Severity.CRITICAL] * 20) == 0


def test_inventario_no_resta():
    assert risk_score([Severity.INFO] * 50) == 100


@pytest.mark.parametrize(
    ("puntaje", "nota"),
    [(100, "A"), (90, "A"), (89.5, "B"), (75, "B"), (74, "C"), (60, "C"), (59, "D"), (40, "D"), (39.5, "F"), (0, "F")],
)
def test_nota(puntaje, nota):
    assert grade(puntaje) == nota
