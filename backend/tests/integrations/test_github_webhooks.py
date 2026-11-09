"""Endpoint interno que recibe los push del Worker de webhooks (Módulo E)."""

import hashlib
import hmac
import json
import os
import time

import fakeredis
import pytest
from fastapi.testclient import TestClient

from app.integrations.github import webhooks
from app.integrations.github.webhooks import verify_signature

TEST_DATABASE_URL = os.getenv("QUBITOR_TEST_DATABASE_URL")
necesita_postgres = pytest.mark.skipif(not TEST_DATABASE_URL, reason="necesita un Postgres (QUBITOR_TEST_DATABASE_URL)")

SECRETO = "s" * 40
URL = "https://github.com/acme/demo"
SHA = "a" * 40


def _firmar(cuerpo: bytes, ts=None, secreto=SECRETO):
    ts = str(int(time.time()) if ts is None else ts)
    firma = hmac.new(secreto.encode(), ts.encode() + b"." + cuerpo, hashlib.sha256).hexdigest()
    return {"X-Qubitor-Timestamp": ts, "X-Qubitor-Signature": f"sha256={firma}", "Content-Type": "application/json"}


def _evento(**cambios):
    datos = {"delivery_id": "72d3162e-cc78-11e3-81ab-4c9367dc0958", "repository_url": URL, "commit_sha": SHA,
             "ref": "refs/heads/main"}
    datos.update(cambios)
    return json.dumps(datos).encode()


# Firma


def test_firma_valida():
    cuerpo = _evento()
    h = _firmar(cuerpo)

    assert verify_signature(SECRETO, h["X-Qubitor-Timestamp"], h["X-Qubitor-Signature"], cuerpo)


def test_firma_con_otro_secreto_o_cuerpo_modificado():
    cuerpo = _evento()
    h = _firmar(cuerpo, secreto="otro" * 10)

    assert not verify_signature(SECRETO, h["X-Qubitor-Timestamp"], h["X-Qubitor-Signature"], cuerpo)
    h = _firmar(cuerpo)
    assert not verify_signature(SECRETO, h["X-Qubitor-Timestamp"], h["X-Qubitor-Signature"], cuerpo + b" ")


def test_una_firma_vieja_no_se_puede_reusar():
    cuerpo = _evento()
    h = _firmar(cuerpo, ts=int(time.time()) - 600)

    assert not verify_signature(SECRETO, h["X-Qubitor-Timestamp"], h["X-Qubitor-Signature"], cuerpo)


@pytest.mark.parametrize("ts,firma", [(None, "sha256=x"), ("123", None), ("abc", "sha256=x"), ("", "")])
def test_cabeceras_faltantes_o_raras(ts, firma):
    assert not verify_signature(SECRETO, ts, firma, b"{}")


# Endpoint


@pytest.fixture
def db():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    import app.models.models  # noqa: F401
    from app.models.database import Base

    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def entorno(db, monkeypatch):
    from app.main import app
    from app.models.database import get_db

    redis = fakeredis.FakeRedis()
    encolados = []
    monkeypatch.setenv("INTERNAL_WEBHOOK_SECRET", SECRETO)
    monkeypatch.setattr(webhooks, "get_connection", lambda: redis)
    monkeypatch.setattr(webhooks, "enqueue_scan", lambda scan_id, url: encolados.append((scan_id, url)))

    def sesion():
        with db() as session:
            yield session

    app.dependency_overrides[get_db] = sesion
    yield TestClient(app), encolados
    app.dependency_overrides.clear()


def _repo(db, org="org_1", url=URL):
    from app.models.models import Organization, Repository

    with db() as session, session.begin():
        organizacion = Organization(name=org, clerk_org_id=org)
        repo = Repository(organization=organizacion, full_name="acme/demo", url=url)
        session.add_all([organizacion, repo])
        session.flush()
        return str(repo.id)


def _push(client, cuerpo=None, headers=None):
    cuerpo = cuerpo if cuerpo is not None else _evento()
    return client.post("/internal/github/push", content=cuerpo, headers=headers or _firmar(cuerpo))


@necesita_postgres
def test_un_push_encola_un_escaneo_del_repo(entorno, db):
    client, encolados = entorno
    _repo(db)

    respuesta = _push(client)

    assert respuesta.status_code == 202
    assert len(respuesta.json()["scans"]) == 1
    assert encolados == [(respuesta.json()["scans"][0], URL)]


@necesita_postgres
def test_escanea_el_repo_en_cada_organizacion_que_lo_conecto(entorno, db):
    client, encolados = entorno
    _repo(db, org="org_1")
    _repo(db, org="org_2", url="https://github.com/Acme/Demo")

    respuesta = _push(client)

    assert len(respuesta.json()["scans"]) == 2
    assert len(encolados) == 2


@necesita_postgres
def test_una_entrega_repetida_no_vuelve_a_escanear(entorno, db):
    client, encolados = entorno
    _repo(db)

    _push(client)
    segunda = _push(client)

    assert segunda.status_code == 202
    assert segunda.json()["duplicate"] is True
    assert len(encolados) == 1


@necesita_postgres
def test_si_hay_un_escaneo_activo_no_lanza_otro(entorno, db):
    client, encolados = entorno
    _repo(db)
    _push(client, _evento(delivery_id="entrega-1"))

    respuesta = _push(client, _evento(delivery_id="entrega-2"))

    assert respuesta.json() == {"duplicate": False, "scans": [], "skipped": 1}
    assert len(encolados) == 1


@necesita_postgres
def test_repo_no_conectado_no_hace_nada(entorno):
    client, encolados = entorno

    respuesta = _push(client)

    assert respuesta.status_code == 202
    assert respuesta.json()["scans"] == [] and encolados == []


@necesita_postgres
def test_firma_invalida_responde_401(entorno, db):
    client, encolados = entorno
    _repo(db)
    cuerpo = _evento()

    respuesta = _push(client, cuerpo, headers=_firmar(cuerpo, secreto="incorrecto" * 4))

    assert respuesta.status_code == 401
    assert encolados == []


@necesita_postgres
@pytest.mark.parametrize(
    "cuerpo",
    [
        _evento(repository_url="https://gitlab.com/a/b"),
        _evento(repository_url="https://github.com/a/b\n"),
        _evento(commit_sha="no-es-un-sha"),
        _evento(delivery_id="../../x"),
        b"esto no es json",
        json.dumps({"repository_url": URL}).encode(),
    ],
)
def test_eventos_invalidos_responden_422(entorno, cuerpo):
    client, encolados = entorno

    assert _push(client, cuerpo).status_code == 422
    assert encolados == []


@necesita_postgres
def test_cuerpo_demasiado_grande(entorno):
    client, _ = entorno
    cuerpo = _evento(ref="x" * (webhooks.MAX_BODY_BYTES + 10))

    assert _push(client, cuerpo).status_code == 413


@necesita_postgres
def test_sin_secreto_configurado_responde_503(entorno, monkeypatch):
    client, _ = entorno
    monkeypatch.setenv("INTERNAL_WEBHOOK_SECRET", "corto")

    assert _push(client).status_code == 503


@necesita_postgres
def test_si_la_cola_no_responde_el_escaneo_queda_fallido(entorno, db, monkeypatch):
    from app.models.models import Scan, ScanStatus

    client, _ = entorno
    _repo(db)

    def cola_caida(scan_id, url):
        raise ConnectionError("Redis caído")

    monkeypatch.setattr(webhooks, "enqueue_scan", cola_caida)

    respuesta = _push(client)

    assert respuesta.json()["scans"] == []
    with db() as session:
        assert session.query(Scan).one().status == ScanStatus.FAILED
