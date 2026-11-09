"""GET /scans/{id}/summary contra un Postgres real (Módulo E)."""

import os
import time
import uuid

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app.api import auth

TEST_DATABASE_URL = os.getenv("QUBITOR_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_DATABASE_URL, reason="necesita un Postgres (QUBITOR_TEST_DATABASE_URL)")

ISSUER = "https://test.clerk.example"
CLAVE = rsa.generate_private_key(public_exponent=65537, key_size=2048)

RESUMEN = {
    "status": "at_risk",
    "headline": "Una credencial expuesta requiere atención inmediata",
    "summary": "El repositorio tiene una clave de AWS expuesta.",
    "top_risks": [{"title": "Clave de AWS", "impact": "Acceso a la nube", "priority": "inmediata"}],
    "priorities": ["Rotar la clave"],
    "generated_by": "gemini",
    "generated_at": "2026-11-08T23:00:00+00:00",
    "triage_status": "completed",
    "triage_reason": None,
}


class _Jwks:
    def get_signing_key_from_jwt(self, token):
        return type("Clave", (), {"key": CLAVE.public_key()})()


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
def client(db, monkeypatch):
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


def _escaneo(client, db, resumen):
    """Crea el repo con la API (así queda en la organización del usuario) y le pone un resumen."""
    from app.models.models import Repository, Scan

    client.post("/repositories", json={"url": "https://github.com/acme/demo"}, headers=headers())
    with db() as session, session.begin():
        repo = session.query(Repository).one()
        scan = Scan(repository_id=repo.id, ai_summary=resumen)
        session.add(scan)
        session.flush()
        return str(scan.id)


def test_devuelve_el_resumen_del_escaneo(client, db):
    scan_id = _escaneo(client, db, RESUMEN)

    respuesta = client.get(f"/scans/{scan_id}/summary", headers=headers())

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["available"] is True
    assert cuerpo["headline"] == RESUMEN["headline"]
    assert cuerpo["top_risks"][0]["priority"] == "inmediata"
    assert cuerpo["generated_by"] == "gemini"


def test_escaneo_sin_resumen(client, db):
    scan_id = _escaneo(client, db, None)

    cuerpo = client.get(f"/scans/{scan_id}/summary", headers=headers()).json()

    assert cuerpo == {**cuerpo, "available": False, "headline": None, "top_risks": []}


def test_otra_organizacion_recibe_404(client, db):
    scan_id = _escaneo(client, db, RESUMEN)

    respuesta = client.get(f"/scans/{scan_id}/summary", headers=headers("user_2", "org_2"))

    assert respuesta.status_code == 404


def test_escaneo_inexistente_y_sin_sesion(client):
    assert client.get(f"/scans/{uuid.uuid4()}/summary", headers=headers()).status_code == 404
    assert client.get(f"/scans/{uuid.uuid4()}/summary").status_code == 401
    assert client.get("/scans/no-es-uuid/summary", headers=headers()).status_code == 422
