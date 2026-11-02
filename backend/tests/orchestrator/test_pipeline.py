from app.engines.base import Engine, Finding, Severity
from app.orchestrator.normalize import fingerprint
from app.orchestrator.pipeline import analyze_repository


def _finding(engine, severity, line=1):
    return Finding(
        engine=engine,
        rule_id=f"{engine}.regla",
        title="",
        severity=severity,
        file_path="a.py",
        line=line,
        snippet="",
        description="",
    )


class MotorFijo(Engine):
    def __init__(self, name, hallazgos):
        self.name = name
        self.hallazgos = hallazgos

    def scan(self, repo_path):
        return self.hallazgos


class MotorQueFalla(Engine):
    name = "roto"

    def scan(self, repo_path):
        raise RuntimeError("no anda")


def test_repo_sin_hallazgos_tiene_nota_a():
    resultado = analyze_repository("repo", [MotorFijo("sast", [])])
    assert resultado.findings == {}
    assert (resultado.risk_score, resultado.grade) == (100, "A")
    assert not resultado.failed


def test_deduplica_y_calcula_el_score():
    critico = _finding("sast", Severity.CRITICAL)
    motores = [
        MotorFijo("sast", [critico, critico, _finding("sast", Severity.HIGH, line=2)]),
        MotorFijo("crypto", [_finding("crypto", Severity.INFO)]),
    ]

    resultado = analyze_repository("repo", motores)

    assert len(resultado.findings) == 3
    assert resultado.findings[fingerprint(critico)] is critico
    assert resultado.risk_score == 100 - 10 - 5
    assert resultado.grade == "B"
    assert resultado.duration_seconds >= 0


def test_escaneo_parcial_si_falla_un_motor():
    resultado = analyze_repository(
        "repo", [MotorQueFalla(), MotorFijo("sast", [_finding("sast", Severity.HIGH)])]
    )
    assert list(resultado.errors) == ["roto"]
    assert len(resultado.findings) == 1
    assert resultado.risk_score == 95
    assert not resultado.failed


def test_falla_si_fallan_todos_los_motores():
    resultado = analyze_repository("repo", [MotorQueFalla()])
    assert resultado.failed


def test_sin_motores_no_es_fallo():
    assert not analyze_repository("repo", []).failed
