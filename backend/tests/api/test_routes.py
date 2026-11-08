"""Endpoints contra un Postgres real (ver tests/worker/test_sql_store.py)."""

import os
import time
import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app.api import auth, routes
from app.engines.base import Severity

TEST_DATABASE_URL = os.getenv("QUBITOR_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_DATABASE_URL, reason="necesita un Postgres (QUBITOR_TEST_DATABASE_URL)")

ISSUER = "https://test.clerk.example"
CLAVE = rsa.generate_private_key(public_exponent=65537, key_size=2048)
URL = "https://github.com/acme/demo"


class _Jwks:
    def get_signing_key_from_jwt(self, token):
        return type("Clave", (), {"key": CLAVE.public_key()})()


@pytest.fixture
def db():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.models.database import Base

    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def encolados(monkeypatch):
    llamadas = []
    monkeypatch.setattr(routes, "enqueue_scan", lambda scan_id, url: llamadas.append((scan_id, url)))
    return llamadas


@pytest.fixture
def client(db, monkeypatch, encolados):
    from app.main import app
    from app.models.database import get_db

    monkeypatch.setenv("CLERK_ISSUER", ISSUER)
    monkeypatch.delenv("AUTH_DISABLED", raising=False)
    monkeypatch.setattr(auth, "_jwks_client", lambda issuer: _Jwks())

    def sesion():
        with db() as session:
            yield session

    app.dependency_overrides[get_db] = sesion
    yield TestClient(app)
    app.dependency_overrides.clear()


def headers(sub="user_1", org="org_1"):
    ahora = int(time.time())
    claims = {"iss": ISSUER, "sub": sub, "iat": ahora, "exp": ahora + 60, "org_id": org}
    return {"Authorization": f"Bearer {jwt.encode(claims, CLAVE, algorithm='RS256')}"}


OTRA_ORG = {"sub": "user_2", "org": "org_2"}


def _conectar(client, url=URL, **quien):
    return client.post("/repositories", json={"url": url}, headers=headers(**quien))


def _escanear(client, repo_id, **quien):
    return client.post(f"/repositories/{repo_id}/scans", headers=headers(**quien))


def _terminar(db, scan_id, *hallazgos, segundos=12):
    """Simula lo que hace el worker: completa el escaneo y guarda hallazgos."""
    from app.models.models import Finding, Scan, ScanStatus

    with db() as session, session.begin():
        scan = session.get(Scan, uuid.UUID(scan_id))
        inicio = datetime.now(timezone.utc)
        scan.status, scan.started_at = ScanStatus.COMPLETED, inicio
        scan.finished_at = inicio + timedelta(seconds=segundos)
        scan.risk_score, scan.grade, scan.commit_sha = 85.0, "B", "a" * 40
        for i, (severidad, extra) in enumerate(hallazgos):
            session.add(Finding(
                scan_id=scan.id, fingerprint=f"fp{i}", engine="sast", rule_id=f"r{i}", title=f"t{i}",
                severity=severidad, file_path=f"f{i}.py", line=i, snippet="s", description="d",
                metadata_={"n": i}, **extra,
            ))


# Autenticación


def test_sin_token_responde_401(client):
    assert client.get("/repositories").status_code == 401


def test_token_invalido_responde_401(client):
    respuesta = client.get("/repositories", headers={"Authorization": "Bearer basura"})
    assert respuesta.status_code == 401


def test_sin_clerk_configurado_responde_503(client, monkeypatch):
    monkeypatch.delenv("CLERK_ISSUER")
    assert client.get("/repositories", headers=headers()).status_code == 503


def test_modo_demo_sin_login(client, monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "true")
    assert client.get("/repositories").status_code == 200


def test_crea_el_usuario_y_la_organizacion_una_sola_vez(client, db):
    from app.models.models import Organization, User

    client.get("/repositories", headers=headers())
    client.get("/repositories", headers=headers())

    with db() as session:
        assert session.query(User).count() == 1
        assert session.query(Organization).one().clerk_org_id == "org_1"


# Repositorios


def test_conectar_repositorio(client):
    respuesta = _conectar(client)

    assert respuesta.status_code == 201
    repo = respuesta.json()
    assert (repo["full_name"], repo["url"], repo["provider"]) == ("acme/demo", URL, "github")
    assert repo["connected_at"]


def test_conectar_dos_veces_devuelve_el_mismo(client):
    primero = _conectar(client).json()
    segundo = _conectar(client, url=URL + ".git/")

    assert segundo.status_code == 200
    assert segundo.json()["id"] == primero["id"]


@pytest.mark.parametrize("url", ["https://gitlab.com/a/b", "git@github.com:a/b.git", "file:///etc/passwd", ""])
def test_conectar_url_invalida_responde_422(client, url):
    assert _conectar(client, url=url).status_code == 422


def test_cada_organizacion_ve_solo_sus_repositorios(client):
    _conectar(client)
    _conectar(client, url="https://github.com/otra/cosa", **OTRA_ORG)

    mios = client.get("/repositories", headers=headers()).json()
    assert [r["full_name"] for r in mios] == ["acme/demo"]


# Escaneos


def test_lanzar_escaneo_lo_crea_en_cola_y_lo_encola(client, encolados):
    repo = _conectar(client).json()

    respuesta = _escanear(client, repo["id"])

    assert respuesta.status_code == 202
    scan = respuesta.json()
    assert (scan["status"], scan["repository_id"]) == ("queued", repo["id"])
    assert scan["engines"] == ["sast", "sca", "secrets", "crypto"]
    assert scan["started_at"] and scan["progress"] is None
    assert encolados == [(scan["id"], URL)]


def test_no_lanza_otro_escaneo_si_hay_uno_activo(client, encolados):
    repo = _conectar(client).json()
    primero = _escanear(client, repo["id"]).json()

    segundo = _escanear(client, repo["id"])

    assert segundo.status_code == 200
    assert segundo.json()["id"] == primero["id"]
    assert len(encolados) == 1


def test_si_la_cola_no_responde_el_escaneo_queda_fallido(client, monkeypatch, db):
    from app.models.models import Scan, ScanStatus

    def sin_redis(scan_id, url):
        raise ConnectionError("Redis caído")

    monkeypatch.setattr(routes, "enqueue_scan", sin_redis)
    repo = _conectar(client).json()

    assert _escanear(client, repo["id"]).status_code == 503
    with db() as session:
        assert session.query(Scan).one().status is ScanStatus.FAILED


def test_estado_del_escaneo_terminado(client, db):
    repo = _conectar(client).json()
    scan_id = _escanear(client, repo["id"]).json()["id"]
    _terminar(db, scan_id, segundos=12)

    scan = client.get(f"/scans/{scan_id}", headers=headers()).json()

    assert (scan["status"], scan["progress"], scan["grade"], scan["risk_score"]) == ("completed", 100, "B", 85.0)
    assert scan["duration_seconds"] == 12.0


def test_historial_del_mas_nuevo_al_mas_viejo(client, db):
    repo = _conectar(client).json()
    viejo = _escanear(client, repo["id"]).json()["id"]
    _terminar(db, viejo)
    nuevo = _escanear(client, repo["id"]).json()["id"]

    historial = client.get(f"/repositories/{repo['id']}/history", headers=headers()).json()

    assert [s["id"] for s in historial] == [nuevo, viejo]


# Hallazgos


def test_hallazgos_ordenados_por_severidad_con_triage(client, db):
    repo = _conectar(client).json()
    scan_id = _escanear(client, repo["id"]).json()["id"]
    _terminar(
        db, scan_id,
        (Severity.LOW, {}),
        (Severity.CRITICAL, {}),
        (Severity.MEDIUM, {"ai_is_false_positive": True, "ai_adjusted_severity": Severity.INFO,
                           "ai_explanation": "e", "ai_remediation": "r"}),
    )

    hallazgos = client.get(f"/scans/{scan_id}/findings", headers=headers()).json()

    assert [h["severity"] for h in hallazgos] == ["critical", "low", "medium"]
    assert hallazgos[0]["triage"] is None
    assert hallazgos[0]["metadata"] == {"n": 1}
    assert hallazgos[2]["triage"] == {
        "is_false_positive": True, "adjusted_severity": "info", "explanation": "e", "remediation": "r",
    }


def test_marcar_resuelto_recalcula_el_score(client, db):
    repo = _conectar(client).json()
    scan_id = _escanear(client, repo["id"]).json()["id"]
    _terminar(db, scan_id, (Severity.CRITICAL, {}), (Severity.HIGH, {}))
    critico = client.get(f"/scans/{scan_id}/findings", headers=headers()).json()[0]

    respuesta = client.patch(f"/findings/{critico['id']}", json={"status": "resolved"}, headers=headers())

    assert respuesta.status_code == 200
    assert respuesta.json()["status"] == "resolved"
    scan = client.get(f"/scans/{scan_id}", headers=headers()).json()
    assert (scan["risk_score"], scan["grade"]) == (95.0, "A")  # solo cuenta el high


def test_estado_invalido_responde_422(client, db):
    repo = _conectar(client).json()
    scan_id = _escanear(client, repo["id"]).json()["id"]
    _terminar(db, scan_id, (Severity.HIGH, {}))
    hallazgo = client.get(f"/scans/{scan_id}/findings", headers=headers()).json()[0]

    respuesta = client.patch(f"/findings/{hallazgo['id']}", json={"status": "borrado"}, headers=headers())
    assert respuesta.status_code == 422


def test_otra_organizacion_recibe_404_en_todo(client, db):
    repo = _conectar(client).json()
    scan_id = _escanear(client, repo["id"]).json()["id"]
    _terminar(db, scan_id, (Severity.HIGH, {}))
    hallazgo = client.get(f"/scans/{scan_id}/findings", headers=headers()).json()[0]
    ajeno = headers(**OTRA_ORG)

    assert client.post(f"/repositories/{repo['id']}/scans", headers=ajeno).status_code == 404
    assert client.get(f"/repositories/{repo['id']}/history", headers=ajeno).status_code == 404
    assert client.get(f"/scans/{scan_id}", headers=ajeno).status_code == 404
    assert client.get(f"/scans/{scan_id}/findings", headers=ajeno).status_code == 404
    assert client.patch(f"/findings/{hallazgo['id']}", json={"status": "resolved"}, headers=ajeno).status_code == 404
    # Y no se modificó nada.
    assert client.get(f"/scans/{scan_id}/findings", headers=headers()).json()[0]["status"] == "open"


def test_ids_inexistentes_responden_404(client):
    client.get("/repositories", headers=headers())
    for ruta in (f"/scans/{uuid.uuid4()}", f"/repositories/{uuid.uuid4()}/history"):
        assert client.get(ruta, headers=headers()).status_code == 404


def test_mismo_repo_con_otras_mayusculas_es_el_mismo(client):
    # GitHub no distingue mayúsculas en owner/repo.
    primero = _conectar(client, url="https://github.com/Acme/Demo").json()
    segundo = _conectar(client, url="https://github.com/acme/demo")

    assert segundo.status_code == 200
    assert segundo.json()["id"] == primero["id"]


def test_un_escaneo_trabado_no_bloquea_el_repo(client, db, encolados):
    # Si el worker se cae o el trabajo vence, el escaneo queda en curso para siempre.
    from app.models.models import Scan, ScanStatus

    repo = _conectar(client).json()
    trabado = _escanear(client, repo["id"]).json()["id"]
    with db() as session, session.begin():
        scan = session.get(Scan, uuid.UUID(trabado))
        scan.status = ScanStatus.RUNNING
        scan.created_at = scan.started_at = datetime.now(timezone.utc) - timedelta(hours=2)

    nuevo = _escanear(client, repo["id"])

    assert nuevo.status_code == 202
    assert nuevo.json()["id"] != trabado
    viejo = client.get(f"/scans/{trabado}", headers=headers()).json()
    assert viejo["status"] == "failed"
    assert "no terminó" in viejo["error"]
    assert len(encolados) == 2


def test_un_escaneo_reciente_en_curso_no_se_corta(client, db, encolados):
    from app.models.models import Scan, ScanStatus

    repo = _conectar(client).json()
    en_curso = _escanear(client, repo["id"]).json()["id"]
    with db() as session, session.begin():
        scan = session.get(Scan, uuid.UUID(en_curso))
        scan.status = ScanStatus.RUNNING
        scan.started_at = datetime.now(timezone.utc) - timedelta(minutes=5)

    assert _escanear(client, repo["id"]).json()["id"] == en_curso
