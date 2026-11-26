import subprocess

import pytest

from app.engines.sast import bandit
from app.engines.sast.bandit import BanditError, run_bandit

pytest.importorskip("bandit")


def test_repo_vacio_no_tiene_resultados(tmp_path):
    assert run_bandit(str(tmp_path))["results"] == []


def test_detecta_eval_con_ruta_relativa(tmp_path):
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "utils.py").write_text("def f(x):\n    return eval(x)\n")

    resultados = run_bandit(str(tmp_path))["results"]

    assert [r["test_id"] for r in resultados] == ["B307"]
    assert not resultados[0]["filename"].startswith(str(tmp_path))


def test_archivo_con_error_de_sintaxis_no_rompe(tmp_path):
    (tmp_path / "roto.py").write_text("def f(:\n")
    assert run_bandit(str(tmp_path))["results"] == []


def test_ignora_carpetas_de_dependencias(tmp_path):
    for carpeta in ("node_modules", ".venv"):
        (tmp_path / carpeta).mkdir()
        (tmp_path / carpeta / "lib.py").write_text("eval(input())\n")

    assert run_bandit(str(tmp_path))["results"] == []


def test_timeout_lanza_bandit_error(tmp_path, monkeypatch):
    def lento(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="bandit", timeout=1)

    monkeypatch.setattr(bandit.subprocess, "run", lento)
    with pytest.raises(BanditError, match="límite"):
        run_bandit(str(tmp_path), timeout=1)


def test_codigo_de_salida_inesperado_lanza_bandit_error(tmp_path, monkeypatch):
    monkeypatch.setattr(
        bandit.subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(a, 2, stdout="", stderr="falló"),
    )
    with pytest.raises(BanditError, match="código 2"):
        run_bandit(str(tmp_path))


def test_salida_que_no_es_json_lanza_bandit_error(tmp_path, monkeypatch):
    monkeypatch.setattr(
        bandit.subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(a, 0, stdout="no json", stderr=""),
    )
    with pytest.raises(BanditError, match="JSON"):
        run_bandit(str(tmp_path))

def test_bandit_no_recibe_credenciales_y_corre_aislado(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://secreto")
    monkeypatch.setenv("CLERK_SECRET_KEY", "sk_test_secreto")
    llamadas = []

    def fake_run(command, **kwargs):
        llamadas.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, stdout='{"results": []}', stderr="")

    monkeypatch.setattr(bandit.subprocess, "run", fake_run)
    run_bandit(str(tmp_path))

    command, kwargs = llamadas[0]
    assert "-I" in command
    assert "DATABASE_URL" not in kwargs["env"]
    assert "CLERK_SECRET_KEY" not in kwargs["env"]



# El repo analizado no puede silenciar hallazgos (QUB-01).

def test_un_bandit_del_repo_no_desactiva_reglas(tmp_path):
    (tmp_path / "app.py").write_text("x = input()\neval(x)\n", encoding="utf-8")
    (tmp_path / ".bandit").write_text("[bandit]\nskips: B307\n", encoding="utf-8")

    salida = run_bandit(str(tmp_path))

    assert "B307" in {r["test_id"] for r in salida["results"]}


def test_un_comentario_nosec_no_oculta_el_hallazgo(tmp_path):
    (tmp_path / "app.py").write_text("x = input()\neval(x)  # nosec\n", encoding="utf-8")

    salida = run_bandit(str(tmp_path))

    assert "B307" in {r["test_id"] for r in salida["results"]}


def test_bandit_usa_la_configuracion_de_qubitor(tmp_path, monkeypatch):
    llamadas = []

    def fake_run(command, **kwargs):
        llamadas.append(command)
        return subprocess.CompletedProcess(command, 0, stdout='{"results": []}', stderr="")

    monkeypatch.setattr(bandit.subprocess, "run", fake_run)
    run_bandit(str(tmp_path))

    command = llamadas[0]
    assert "--ignore-nosec" in command
    assert command[command.index("--ini") + 1] == str(bandit.CONFIG_FILE)
    assert bandit.CONFIG_FILE.is_file()
