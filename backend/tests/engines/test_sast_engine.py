import pytest

from app.engines.base import Engine, Severity
from app.engines.sast import SastEngine

pytest.importorskip("bandit")


def _escribir(repo, ruta, codigo):
    archivo = repo / ruta
    archivo.parent.mkdir(parents=True, exist_ok=True)
    archivo.write_text(codigo)


def test_cumple_el_contrato():
    motor = SastEngine()
    assert isinstance(motor, Engine)
    assert motor.name == "sast"


def test_repo_vacio_devuelve_lista_vacia(tmp_path):
    assert SastEngine().scan(str(tmp_path)) == []


def test_codigo_seguro_no_tiene_hallazgos(tmp_path):
    _escribir(tmp_path, "app/ok.py", "import ast\n\ndef f(x):\n    return ast.literal_eval(x)\n")
    assert SastEngine().scan(str(tmp_path)) == []


def test_fallas_plantadas_del_repo_de_demo(tmp_path):
    _escribir(
        tmp_path,
        "app/db.py",
        "def buscar(conn, nombre):\n"
        "    return conn.execute(f\"SELECT * FROM users WHERE name = '{nombre}'\")\n",
    )
    _escribir(tmp_path, "app/utils.py", "def calcular(entrada):\n    return eval(entrada)\n")
    _escribir(tmp_path, "app/roto.py", "def f(:\n")

    hallazgos = {h.rule_id: h for h in SastEngine().scan(str(tmp_path))}

    assert set(hallazgos) == {"sast.bandit.B608", "sast.bandit.B307"}
    sql, evaluar = hallazgos["sast.bandit.B608"], hallazgos["sast.bandit.B307"]
    assert (sql.file_path, sql.line, sql.cwe) == ("app/db.py", 2, "CWE-89")
    assert (evaluar.file_path, evaluar.line) == ("app/utils.py", 2)
    assert sql.severity is evaluar.severity is Severity.HIGH
    assert "users" not in sql.snippet


def test_shell_true(tmp_path):
    _escribir(
        tmp_path,
        "run.py",
        "import subprocess\n\ndef run(cmd):\n    subprocess.call(cmd, shell=True)\n",
    )
    hallazgos = {h.rule_id: h for h in SastEngine().scan(str(tmp_path))}

    # Bandit también avisa (low) por importar subprocess.
    assert hallazgos["sast.bandit.B404"].severity is Severity.LOW
    assert hallazgos["sast.bandit.B602"].severity is Severity.HIGH
    assert hallazgos["sast.bandit.B602"].cwe == "CWE-78"
