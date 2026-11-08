"""El scan-worker clona los repos privados con el token del usuario (Módulo E)."""

import os
from pathlib import Path

import pytest

from app.worker import job as job_module
from app.worker.clone import CloneRejected
from app.worker.store import LogScanStore


class _Store(LogScanStore):
    def __init__(self):
        self.eventos = []

    def mark_running(self, scan_id):
        self.eventos.append(("running", scan_id))

    def save_result(self, scan_id, commit_sha, result):
        self.eventos.append(("completed", scan_id))

    def mark_failed(self, scan_id, error):
        self.eventos.append(("failed", scan_id, error))


@pytest.fixture
def entorno(monkeypatch, tmp_path):
    store = _Store()
    llamadas = []

    def clon_falso(url, destino, **kwargs):
        llamadas.append((url, kwargs))
        os.makedirs(destino)
        Path(destino, "app.py").write_text("x = 1\n")
        return "b" * 40

    monkeypatch.setattr(job_module, "get_store", lambda: store)
    monkeypatch.setattr(job_module, "archive_scan", lambda *args: False)
    monkeypatch.setattr(job_module, "clone_repository", clon_falso)
    monkeypatch.setattr(job_module, "default_engines", lambda: [])
    monkeypatch.setenv("REPOS_DIR", str(tmp_path))
    return store, llamadas


def test_repo_privado_se_clona_con_el_token(entorno, monkeypatch):
    store, llamadas = entorno
    monkeypatch.setattr(job_module, "clone_token_for_scan", lambda scan_id: "gho_del_usuario")

    resumen = job_module.run_scan("scan-1", "https://github.com/acme/privado")

    assert resumen["status"] == "completed"
    assert llamadas == [("https://github.com/acme/privado", {"token": "gho_del_usuario"})]
    # El token no queda en el resumen que RQ guarda en Redis.
    assert "gho_del_usuario" not in str(resumen)


def test_repo_publico_se_clona_sin_token(entorno, monkeypatch):
    _, llamadas = entorno
    monkeypatch.setattr(job_module, "clone_token_for_scan", lambda scan_id: None)

    job_module.run_scan("scan-2", "https://github.com/acme/demo")

    assert llamadas == [("https://github.com/acme/demo", {})]


def test_sin_acceso_al_repo_privado_el_escaneo_falla_sin_reintentar(entorno, monkeypatch):
    store, llamadas = entorno

    def sin_acceso(scan_id):
        raise CloneRejected("Quien conectó el repositorio privado ya no tiene GitHub vinculado: volvé a conectarlo")

    monkeypatch.setattr(job_module, "clone_token_for_scan", sin_acceso)

    resumen = job_module.run_scan("scan-3", "https://github.com/acme/privado")

    assert resumen["status"] == "failed"
    assert llamadas == []
    assert store.eventos[-1][0] == "failed"
