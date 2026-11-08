"""Puntaje base de CVSS 3.x a partir de su vector (Módulo D, SCA).

OSV publica el vector (por ejemplo "CVSS:3.1/AV:N/AC:L/...") pero no el
puntaje. Se calcula con las fórmulas de la especificación 3.1, sin sumar
dependencias al scan-worker. CVSS 4.0 usa tablas en lugar de fórmulas y queda
afuera: para esos vectores se devuelve None.
"""

_VERSIONS = ("CVSS:3.0", "CVSS:3.1")

_WEIGHTS = {
    "AV": {"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.2},
    "AC": {"L": 0.77, "H": 0.44},
    "UI": {"N": 0.85, "R": 0.62},
    "C": {"H": 0.56, "L": 0.22, "N": 0.0},
    "I": {"H": 0.56, "L": 0.22, "N": 0.0},
    "A": {"H": 0.56, "L": 0.22, "N": 0.0},
}

# Los privilegios pesan distinto si la falla alcanza a otros componentes (S:C).
_PRIVILEGES = {
    "U": {"N": 0.85, "L": 0.62, "H": 0.27},
    "C": {"N": 0.85, "L": 0.68, "H": 0.5},
}


def base_score(vector: str) -> float | None:
    """Puntaje base de 0.0 a 10.0, o None si el vector no es CVSS 3.x válido."""
    version, _, rest = vector.partition("/")
    if version not in _VERSIONS:
        return None
    metrics = dict(part.partition(":")[::2] for part in rest.split("/"))
    try:
        scope = metrics["S"]
        privileges = _PRIVILEGES[scope][metrics["PR"]]
        av, ac, ui, c, i, a = (_WEIGHTS[name][metrics[name]] for name in ("AV", "AC", "UI", "C", "I", "A"))
    except KeyError:
        return None

    impact_subscore = 1 - (1 - c) * (1 - i) * (1 - a)
    if scope == "U":
        impact = 6.42 * impact_subscore
    else:
        impact = 7.52 * (impact_subscore - 0.029) - 3.25 * (impact_subscore - 0.02) ** 15
    if impact <= 0:
        return 0.0

    exploitability = 8.22 * av * ac * privileges * ui
    total = impact + exploitability if scope == "U" else 1.08 * (impact + exploitability)
    return _round_up(min(total, 10))


def _round_up(value: float) -> float:
    """Redondea hacia arriba a un decimal, como pide la especificación 3.1.

    Se trabaja con enteros para que errores de coma flotante (4.000000001)
    no sumen una décima de más.
    """
    scaled = round(value * 100_000)
    if scaled % 10_000 == 0:
        return scaled / 100_000
    return (scaled // 10_000 + 1) / 10
