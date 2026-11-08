import json
import zlib

import fakeredis
import pytest

from app import config
from app.worker.queue import MAX_RETRIES, QUEUE_NAME, SCAN_JOB, enqueue_scan, get_queue


@pytest.fixture
def redis():
    return fakeredis.FakeStrictRedis()


def test_encola_el_escaneo_en_la_cola_de_escaneos(redis):
    trabajo = enqueue_scan("abc", "https://github.com/a/b", connection=redis)

    assert trabajo.id == "scan-abc"
    assert trabajo.origin == QUEUE_NAME
    assert trabajo.func_name == SCAN_JOB
    assert list(trabajo.args) == ["abc", "https://github.com/a/b"]
    assert get_queue(redis).job_ids == ["scan-abc"]


def test_configura_reintentos_y_cola_de_errores(redis):
    trabajo = enqueue_scan("abc", "https://github.com/a/b", connection=redis)

    assert trabajo.retries_left == MAX_RETRIES
    assert trabajo.failure_ttl == 7 * 24 * 60 * 60


def test_los_datos_se_guardan_como_json(redis):
    enqueue_scan("abc", "https://github.com/a/b", connection=redis)

    guardado = zlib.decompress(redis.hget("rq:job:scan-abc", "data"))
    assert json.loads(guardado)[2] == ["abc", "https://github.com/a/b"]


def test_no_encola_dos_veces_el_mismo_escaneo(redis):
    primero = enqueue_scan("123", "https://github.com/a/b", connection=redis)
    segundo = enqueue_scan("123", "https://github.com/a/b", connection=redis)

    assert segundo.id == primero.id
    assert get_queue(redis).job_ids == ["scan-123"]


def test_escaneos_distintos_se_encolan_los_dos(redis):
    enqueue_scan("1", "https://github.com/a/b", connection=redis)
    enqueue_scan("2", "https://github.com/a/b", connection=redis)

    assert get_queue(redis).job_ids == ["scan-1", "scan-2"]


def test_se_puede_volver_a_encolar_si_el_trabajo_ya_no_existe(redis):
    enqueue_scan("123", "https://github.com/a/b", connection=redis).delete()

    enqueue_scan("123", "https://github.com/a/b", connection=redis)

    assert get_queue(redis).job_ids == ["scan-123"]


def test_falla_claro_si_falta_redis_url(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    with pytest.raises(RuntimeError, match="REDIS_URL"):
        config.redis_url()
