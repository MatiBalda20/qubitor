import os

import pytest

from app.engines.base import Severity
from app.engines.sast.findings import bandit_to_findings


def _resultado(**cambios):
    datos = {
        "code": "1 def calcular(entrada):\n2     return eval(entrada)\n",
        "filename": "./app/utils.py",
        "issue_confidence": "HIGH",
        "issue_cwe": {"id": 78, "link": "https://cwe.mitre.org/data/definitions/78.html"},
        "issue_severity": "MEDIUM",
        "issue_text": "Use of possibly insecure function - consider using safer ast.literal_eval.",
        "line_number": 2,
        "more_info": "https://bandit.readthedocs.io/en/latest/blacklists/blacklist_calls.html#b307-eval",
        "test_id": "B307",
        "test_name": "blacklist",
    }
    datos.update(cambios)
    return datos


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "utils.py").write_text("")
    return tmp_path


def _convertir(repo, *resultados):
    return bandit_to_findings({"results": list(resultados)}, str(repo))


def test_salida_sin_resultados(repo):
    assert bandit_to_findings({"results": []}, str(repo)) == []
    assert bandit_to_findings({}, str(repo)) == []


def test_convierte_eval_a_finding(repo):
    [hallazgo] = _convertir(repo, _resultado())

    assert hallazgo.engine == "sast"
    assert hallazgo.rule_id == "sast.bandit.B307"
    assert hallazgo.title == "Uso de eval()"
    assert hallazgo.severity is Severity.HIGH
    assert hallazgo.file_path == "app/utils.py"
    assert hallazgo.line == 2
    assert hallazgo.cwe == "CWE-78"
    assert hallazgo.cve is None
    assert hallazgo.metadata["confidence"] == "HIGH"
    assert hallazgo.metadata["more_info"].startswith("https://bandit")


def test_ruta_con_barras_de_windows(repo):
    [hallazgo] = _convertir(repo, _resultado(filename=".\\app\\utils.py"))
    assert hallazgo.file_path == "app/utils.py"


def test_severidad_de_bandit_sin_ajuste(repo):
    [hallazgo] = _convertir(repo, _resultado(test_id="B303", issue_severity="MEDIUM"))
    assert hallazgo.severity is Severity.MEDIUM


def test_inyeccion_sql_sube_a_high(repo):
    [hallazgo] = _convertir(repo, _resultado(test_id="B608", issue_confidence="MEDIUM"))
    assert hallazgo.severity is Severity.HIGH
    assert "inyección SQL" in hallazgo.title


def test_confianza_baja_baja_un_nivel(repo):
    [hallazgo] = _convertir(
        repo, _resultado(test_id="B303", issue_severity="HIGH", issue_confidence="LOW")
    )
    assert hallazgo.severity is Severity.MEDIUM


def test_regla_sin_titulo_propio_usa_el_nombre_de_bandit(repo):
    [hallazgo] = _convertir(repo, _resultado(test_id="B999", test_name="some_new_check"))
    assert hallazgo.title == "Some new check"


def test_sin_cwe(repo):
    [hallazgo] = _convertir(repo, _resultado(issue_cwe={}))
    assert hallazgo.cwe is None


def test_snippet_sin_numeros_de_linea(repo):
    [hallazgo] = _convertir(repo, _resultado())
    assert hallazgo.snippet == "def calcular(entrada):\n    return eval(entrada)"


def test_snippet_enmascara_textos(repo):
    codigo = '1 password = "hunter2"\n2 query = f"SELECT * FROM t WHERE id = {x}"\n3 key = b\'\\x00abc\'\n'
    [hallazgo] = _convertir(repo, _resultado(code=codigo))

    assert "hunter2" not in hallazgo.snippet
    assert "SELECT" not in hallazgo.snippet
    assert "abc" not in hallazgo.snippet
    assert hallazgo.snippet.splitlines() == [
        'password = "***"',
        'query = f"***"',
        "key = b'***'",
    ]


def test_snippet_maximo_cinco_lineas(repo):
    codigo = "".join(f"{n} x = {n}\n" for n in range(1, 9))
    [hallazgo] = _convertir(repo, _resultado(code=codigo))
    assert len(hallazgo.snippet.splitlines()) == 5


def test_descarta_archivos_fuera_del_repo(repo):
    assert _convertir(repo, _resultado(filename="../afuera.py")) == []


def test_descarta_carpetas_de_dependencias(repo):
    assert _convertir(repo, _resultado(filename="./node_modules/x/a.py")) == []


def test_descarta_enlaces_simbolicos(repo, tmp_path_factory):
    afuera = tmp_path_factory.mktemp("afuera") / "privado.py"
    afuera.write_text("eval(x)\n")
    try:
        os.symlink(afuera, repo / "enlace.py")
    except OSError:
        pytest.skip("crear enlaces simbólicos requiere permisos en este sistema")

    assert _convertir(repo, _resultado(filename="./enlace.py")) == []
