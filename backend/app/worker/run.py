"""Punto de entrada del scan-worker: `python -m app.worker.run`."""

import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from rq import SimpleWorker, Worker
from rq.serializers import JSONSerializer
from rq.timeouts import TimerDeathPenalty

from app.worker.queue import QUEUE_NAME, get_connection


class _NoForkWorker(SimpleWorker):
    """Windows no tiene fork ni SIGALRM: es solo para probar en local."""

    death_penalty_class = TimerDeathPenalty


def worker_class() -> type[Worker]:
    return Worker if hasattr(os, "fork") else _NoForkWorker


class _HealthHandler(BaseHTTPRequestHandler):
    """Solo responde `GET /health`: no sirve archivos ni lista carpetas."""

    def do_GET(self) -> None:  # noqa: N802 (nombre que exige http.server)
        if self.path.split("?", 1)[0] == "/health":
            status, body = 200, b"ok"
        else:
            status, body = 404, b"not found"
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        """Sin logs por pedido: el keep-alive pega cada 10 minutos."""


def start_health_server() -> ThreadingHTTPServer | None:
    """Levanta `/health` en `0.0.0.0:$PORT` en un thread daemon.

    Render free solo ofrece Web Services, y un Web Service tiene que abrir
    `$PORT` o el deploy falla. Sin `PORT` (en local o como Background Worker)
    no abre nada y devuelve `None`.

    El thread vive en el proceso padre de RQ: `Worker` hace fork por cada
    trabajo, pero el padre sigue corriendo y atendiendo `/health` mientras el
    hijo escanea.
    """
    port = os.environ.get("PORT")
    if not port:
        return None
    server = ThreadingHTTPServer(("0.0.0.0", int(port)), _HealthHandler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, name="health", daemon=True).start()
    logging.getLogger(__name__).info("Health check en el puerto %s", port)
    return server


def main(burst: bool = False) -> None:
    logging.basicConfig(level=logging.INFO)
    start_health_server()
    worker = worker_class()([QUEUE_NAME], connection=get_connection(), serializer=JSONSerializer)
    worker.work(burst=burst, with_scheduler=False)


if __name__ == "__main__":
    main()
