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
