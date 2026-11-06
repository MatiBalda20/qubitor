from app.engines.base import Finding, Severity
from app.orchestrator.normalize import deduplicate, fingerprint


def _finding(**cambios):
    datos = dict(
        engine="sast",
        rule_id="sast.bandit.B307",
        title="Uso de eval()",
        severity=Severity.HIGH,
        file_path="app/utils.py",
        line=2,
        snippet="eval(x)",
        description="",
    )
    datos.update(cambios)
    return Finding(**datos)


def test_fingerprint_es_estable():
    assert fingerprint(_finding()) == fingerprint(_finding())
    assert len(fingerprint(_finding())) == 64


def test_fingerprint_ignora_snippet_severidad_y_textos():
    otro = _finding(snippet="otro", severity=Severity.LOW, title="x", description="y")
    assert fingerprint(otro) == fingerprint(_finding())


def test_fingerprint_cambia_con_motor_regla_archivo_y_linea():
    base = fingerprint(_finding())
    for cambio in (
        {"engine": "crypto"},
        {"rule_id": "sast.bandit.B102"},
        {"file_path": "app/otro.py"},
        {"line": 3},
        {"line": None},
    ):
        assert fingerprint(_finding(**cambio)) != base


def test_deduplicar_lista_vacia():
    assert deduplicate([]) == {}


def test_deduplicar_deja_uno_por_fingerprint():
    unicos = deduplicate([_finding(), _finding(), _finding(line=5)])
    assert len(unicos) == 2
    assert [h.line for h in unicos.values()] == [2, 5]


def test_deduplicar_se_queda_con_la_mayor_severidad():
    unicos = deduplicate([_finding(severity=Severity.LOW), _finding(severity=Severity.CRITICAL)])
    [hallazgo] = unicos.values()
    assert hallazgo.severity is Severity.CRITICAL


def test_las_claves_son_los_fingerprints():
    hallazgo = _finding()
    assert list(deduplicate([hallazgo])) == [fingerprint(hallazgo)]
