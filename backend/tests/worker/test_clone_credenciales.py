"""Clonado con token y entorno mínimo para Git (Módulo E)."""

import base64
import os
import subprocess

import pytest

from app.worker import clone
from app.worker.clone import CloneRejected, clone_repository, git_env, is_github_url


def test_rechaza_una_url_con_salto_de_linea_al_final():
    assert not is_github_url("https://github.com/a/b\n")
    with pytest.raises(CloneRejected):
        clone_repository("https://github.com/a/b\n", "destino")


def test_acepta_urls_validas():
    assert is_github_url("https://github.com/qubitor-org/demo")
    assert is_github_url("https://github.com/qubitor-org/demo.git")


def test_git_no_recibe_las_credenciales_del_worker(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://secreto")
    monkeypatch.setenv("REDIS_URL", "rediss://secreto")
    monkeypatch.setenv("GEMINI_API_KEY", "secreto")
    monkeypatch.setenv("CLERK_SECRET_KEY", "sk_test_secreto")

    env = git_env()

    assert not {"DATABASE_URL", "REDIS_URL", "GEMINI_API_KEY", "CLERK_SECRET_KEY"} & set(env)
    assert env["GIT_TERMINAL_PROMPT"] == "0"
    # Sin configuración global: ningún credential helper puede guardar el token.
    assert env["GIT_CONFIG_GLOBAL"] == os.devnull
    assert env["GIT_CONFIG_NOSYSTEM"] == "1"


def test_sin_token_no_hay_cabecera_de_autorizacion():
    assert "GIT_CONFIG_COUNT" not in git_env()
    assert "GIT_CONFIG_COUNT" not in git_env(None)


def test_el_token_va_como_cabecera_solo_para_github():
    env = git_env("gho_token_de_prueba")

    assert env["GIT_CONFIG_COUNT"] == "1"
    assert env["GIT_CONFIG_KEY_0"] == "http.https://github.com/.extraheader"
    esquema, credenciales = env["GIT_CONFIG_VALUE_0"].removeprefix("Authorization: ").split(" ")
    assert esquema == "Basic"
    assert base64.b64decode(credenciales).decode() == "x-access-token:gho_token_de_prueba"


def test_el_token_no_aparece_en_los_argumentos_del_proceso(tmp_path, monkeypatch):
    lanzados = []

    class _ProcesoFalso:
        returncode = 0
        stderr = None

        def __init__(self, command, env, **_):
            lanzados.append((command, env))

        def poll(self):
            return 0

    def _rev_parse(*_, **__):
        return subprocess.CompletedProcess([], 0, stdout="a" * 40 + "\n", stderr="")

    monkeypatch.setattr(clone.subprocess, "Popen", _ProcesoFalso)
    monkeypatch.setattr(clone.subprocess, "run", _rev_parse)

    sha = clone_repository("https://github.com/a/privado", str(tmp_path / "repo"), token="gho_secreto")

    assert sha == "a" * 40
    command, env = lanzados[0]
    assert not any("gho_secreto" in parte for parte in command)
    assert "https://github.com/a/privado" in command
    assert "gho_secreto" not in env["GIT_CONFIG_KEY_0"]
    assert "gho_secreto" in base64.b64decode(env["GIT_CONFIG_VALUE_0"].split(" ")[-1]).decode()


@pytest.mark.skipif(not os.getenv("QUBITOR_TESTS_RED"), reason="usa internet (QUBITOR_TESTS_RED=1)")
def test_un_token_invalido_no_se_filtra_en_el_error_ni_en_disco(tmp_path):
    destino = tmp_path / "repo"

    # GitHub rechaza un token inválido aunque el repo sea público: no se reintenta.
    with pytest.raises(CloneRejected) as error:
        clone_repository("https://github.com/octocat/Hello-World", str(destino), token="gho_token_que_no_se_guarda")

    assert "gho_token_que_no_se_guarda" not in str(error.value)
    for archivo in tmp_path.rglob("*"):
        if archivo.is_file():
            assert b"gho_token_que_no_se_guarda" not in archivo.read_bytes()
