import os
import socket
import time
import urllib.error
import urllib.request

import pytest

from app.worker.run import start_health_server


def _puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _get(port: int, path: str) -> tuple[int, bytes]:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=5) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


@pytest.fixture
def servidor(monkeypatch):
    port = _puerto_libre()
    monkeypatch.setenv("PORT", str(port))
    server = start_health_server()
    yield server, port
    if server is not None:
        server.shutdown()
        server.server_close()


def test_health_responde_200_ok(servidor):
    _, port = servidor

    assert _get(port, "/health") == (200, b"ok")


@pytest.mark.parametrize("ruta", ["/otra", "/", "/tmp/scans", "/app", "/../etc/passwd"])
def test_otras_rutas_responden_404(servidor, ruta):
    _, port = servidor

    status, body = _get(port, ruta)

    assert status == 404
    assert body == b"not found"


def test_sin_port_no_abre_ningun_puerto(monkeypatch):
    port = _puerto_libre()
    monkeypatch.delenv("PORT", raising=False)

    assert start_health_server() is None
    with pytest.raises(OSError):
        socket.create_connection(("127.0.0.1", port), timeout=1).close()


@pytest.mark.skipif(not hasattr(os, "fork"), reason="RQ Worker solo hace fork en Linux/macOS")
def test_sigue_respondiendo_mientras_un_hijo_forkeado_trabaja(servidor):
    _, port = servidor

    pid = os.fork()
    if pid == 0:  # el hijo hace de work-horse de RQ
        time.sleep(2)
        os._exit(0)
    try:
        assert _get(port, "/health") == (200, b"ok")
    finally:
        os.waitpid(pid, 0)
