import pytest

from app.engines.base import Engine, Finding, Severity


def _finding(**cambios):
    datos = dict(
        engine="sast",
        rule_id="sast.bandit.B307",
        title="Uso de eval()",
        severity=Severity.HIGH,
        file_path="app/utils.py",
        line=3,
        snippet="eval(entrada)",
        description="eval ejecuta código arbitrario.",
    )
    datos.update(cambios)
    return Finding(**datos)


def test_severidad_se_crea_desde_texto():
    assert Severity("critical") is Severity.CRITICAL


def test_severidad_se_compara_y_serializa_como_texto():
    assert Severity.HIGH == "high"
    assert Severity.HIGH.value == "high"


def test_severidad_invalida_falla():
    with pytest.raises(ValueError):
        Severity("urgente")


def test_finding_campos_opcionales_por_defecto():
    hallazgo = _finding()
    assert hallazgo.cwe is None
    assert hallazgo.cve is None
    assert hallazgo.metadata == {}


def test_finding_acepta_linea_vacia():
    assert _finding(line=None).line is None


def test_metadata_no_se_comparte_entre_hallazgos():
    primero, segundo = _finding(), _finding()
    primero.metadata["algoritmo"] = "MD5"
    assert segundo.metadata == {}


def test_engine_no_se_puede_instanciar_sin_scan():
    class MotorIncompleto(Engine):
        name = "incompleto"

    with pytest.raises(TypeError):
        MotorIncompleto()


def test_engine_concreto_devuelve_findings():
    class MotorDePrueba(Engine):
        name = "prueba"

        def scan(self, repo_path):
            return [_finding(file_path=f"{repo_path}/app.py")]

    hallazgos = MotorDePrueba().scan("repo")
    assert hallazgos[0].file_path == "repo/app.py"
