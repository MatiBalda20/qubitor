"""Configuración de producción: nada de desarrollo puede quedar abierto en Render."""

import importlib

from fastapi.testclient import TestClient

from app.api import auth


def test_auth_disabled_funciona_en_local(monkeypatch):
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.setenv("AUTH_DISABLED", "true")

    assert auth.auth_disabled() is True


def test_auth_disabled_se_ignora_en_render(monkeypatch):
    """QUB-13: en Render, AUTH_DISABLED=true no puede dejar entrar sin token."""
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("AUTH_DISABLED", "true")

    assert auth.auth_disabled() is False


def _app(monkeypatch, **env):
    import app.main as main

    for nombre in ("RENDER", "API_DOCS"):
        monkeypatch.delenv(nombre, raising=False)
    for nombre, valor in env.items():
        monkeypatch.setenv(nombre, valor)
    return TestClient(importlib.reload(main).app)


def test_docs_apagados_en_render(monkeypatch):
    """QUB-09: /docs y /openapi.json no se publican en producción."""
    client = _app(monkeypatch, RENDER="true")

    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404
    assert client.get("/health").status_code == 200


def test_docs_disponibles_en_local(monkeypatch):
    client = _app(monkeypatch)

    assert client.get("/openapi.json").status_code == 200


def teardown_module():
    import app.main as main

    importlib.reload(main)
