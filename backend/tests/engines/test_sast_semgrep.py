import shutil

import pytest

from app.engines.base import Severity
from app.engines.sast import engine as engine_module
from app.engines.sast import semgrep
from app.engines.sast.bandit import BanditError
from app.engines.sast.engine import SastEngine
from app.engines.sast.semgrep import SemgrepError, run_semgrep, semgrep_to_findings

hay_semgrep = pytest.mark.skipif(shutil.which("semgrep") is None, reason="Semgrep solo está en la imagen del worker")


def _resultado(**cambios):
    datos = {
        "check_id": "tmp.rules.qubitor-js-sql-injection",
        "path": "src/db.js",
        "start": {"line": 2, "col": 3},
        "end": {"line": 2, "col": 40},
        "extra": {
            "message": "La consulta SQL se arma concatenando datos.",
            "severity": "ERROR",
            "metadata": {"qubitor_id": "sql-injection", "cwe": "CWE-89", "title": "Consulta SQL armada con strings"},
            "lines": "requires login",
        },
    }
    datos.update(cambios)
    return datos


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "db.js").write_text(
        "function buscar(db, id) {\n  return db.query(`SELECT * FROM users WHERE id = ${id}`);\n}\n"
    )
    return tmp_path


def test_convierte_el_resultado_en_finding(repo):
    [hallazgo] = semgrep_to_findings({"results": [_resultado()]}, str(repo))

    assert hallazgo.engine == "sast"
    assert hallazgo.rule_id == "sast.semgrep.sql-injection"
    assert hallazgo.severity is Severity.HIGH
    assert (hallazgo.file_path, hallazgo.line, hallazgo.cwe) == ("src/db.js", 2, "CWE-89")
    assert hallazgo.title == "Consulta SQL armada con strings"
    assert hallazgo.metadata["tool"] == "semgrep"


def test_el_snippet_se_lee_del_archivo_y_enmascara_textos(repo):
    [hallazgo] = semgrep_to_findings({"results": [_resultado()]}, str(repo))

    assert hallazgo.snippet == "  return db.query(`***`);"
    assert "requires login" not in hallazgo.snippet


@pytest.mark.parametrize(
    ("severidad", "esperada"), [("ERROR", Severity.HIGH), ("WARNING", Severity.MEDIUM), ("INFO", Severity.LOW)]
)
def test_mapea_la_severidad(repo, severidad, esperada):
    resultado = _resultado()
    resultado["extra"]["severity"] = severidad
    [hallazgo] = semgrep_to_findings({"results": [resultado]}, str(repo))
    assert hallazgo.severity is esperada


def test_descarta_archivos_fuera_del_repo(repo):
    assert semgrep_to_findings({"results": [_resultado(path="../afuera.js")]}, str(repo)) == []


def test_sin_semgrep_instalado_devuelve_none(repo, monkeypatch):
    def no_existe(*args, **kwargs):
        raise FileNotFoundError("semgrep")

    monkeypatch.setattr(semgrep.subprocess, "run", no_existe)
    assert run_semgrep(str(repo)) is None


def test_se_puede_apagar_con_una_variable(repo, monkeypatch):
    llamadas = []
    monkeypatch.setattr(semgrep.subprocess, "run", lambda *a, **k: llamadas.append(a))
    monkeypatch.setenv("SEMGREP_ENABLED", "false")

    assert run_semgrep(str(repo)) is None
    assert llamadas == []


def test_timeout_lanza_semgrep_error(repo, monkeypatch):
    def lento(*args, **kwargs):
        raise semgrep.subprocess.TimeoutExpired(cmd="semgrep", timeout=1)

    monkeypatch.setattr(semgrep.subprocess, "run", lento)
    with pytest.raises(SemgrepError, match="límite"):
        run_semgrep(str(repo), timeout=1)


# El motor combina Bandit y Semgrep


def _motor(monkeypatch, bandit, semgrep_resultado):
    monkeypatch.setattr(engine_module, "run_bandit", bandit)
    monkeypatch.setattr(engine_module, "bandit_to_findings", lambda salida, repo: salida)
    monkeypatch.setattr(engine_module, "_semgrep_findings", semgrep_resultado)
    return SastEngine()


def _falla(error):
    def lanzar(*args):
        raise error

    return lanzar


def test_junta_los_hallazgos_de_las_dos_herramientas(monkeypatch, repo):
    motor = _motor(monkeypatch, lambda r: ["de bandit"], lambda r: ["de semgrep"])
    assert motor.scan(str(repo)) == ["de bandit", "de semgrep"]


def test_si_falla_una_herramienta_devuelve_la_otra(monkeypatch, repo):
    motor = _motor(monkeypatch, _falla(BanditError("x")), lambda r: ["de semgrep"])
    assert motor.scan(str(repo)) == ["de semgrep"]


def test_si_fallan_las_dos_el_motor_falla(monkeypatch, repo):
    motor = _motor(monkeypatch, _falla(BanditError("bandit")), _falla(SemgrepError("semgrep")))
    with pytest.raises(BanditError):
        motor.scan(str(repo))


def test_sin_semgrep_un_error_de_bandit_no_se_pierde(monkeypatch, repo):
    motor = _motor(monkeypatch, _falla(BanditError("bandit")), lambda r: None)
    with pytest.raises(BanditError):
        motor.scan(str(repo))


# Con Semgrep real (corre en la imagen del worker)


@hay_semgrep
def test_reglas_reales_detectan_las_fallas_de_javascript(tmp_path):
    (tmp_path / "app.js").write_text(
        "const cp = require('child_process');\n"
        "function f(db, el, id, cmd, code) {\n"
        "  eval(code);\n"
        "  db.query('SELECT * FROM t WHERE id = ' + id);\n"
        "  cp.exec(`ls ${cmd}`);\n"
        "  el.innerHTML = code;\n"
        "  document.write(code);\n"
        "  setTimeout('alert(1)', 10);\n"
        "  const g = new Function(code);\n"
        "}\n"
    )
    (tmp_path / "seguro.js").write_text(
        "function g(db, el, id) {\n"
        "  eval('1 + 1');\n"
        "  db.query('SELECT 1 WHERE id = $1', [id]);\n"
        "  el.innerHTML = 'hola';\n"
        "}\n"
    )
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "lib.js").write_text("eval(x);\n")

    hallazgos = semgrep_to_findings(run_semgrep(str(tmp_path)), str(tmp_path))

    assert {h.rule_id for h in hallazgos} == {
        "sast.semgrep.eval",
        "sast.semgrep.sql-injection",
        "sast.semgrep.command-injection",
        "sast.semgrep.inner-html",
        "sast.semgrep.document-write",
        "sast.semgrep.timer-string",
        "sast.semgrep.new-function",
    }
    assert {h.file_path for h in hallazgos} == {"app.js"}
