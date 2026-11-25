"""Organizaciones con varios miembros y roles, contra un Postgres real (ver tests/worker/test_sql_store.py)."""

import io
import json
import os
import time
import urllib.request

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app.api import auth, clerk_users, organization, routes
from app.api.auth import organization_name, organization_role
from app.api.clerk_users import ClerkProfile, fetch_profiles
from app.models.models import MemberRole

ISSUER = "https://test.clerk.example"
CLAVE = rsa.generate_private_key(public_exponent=65537, key_size=2048)
URL = "https://github.com/acme/demo"

necesita_postgres = pytest.mark.skipif(
    not os.getenv("QUBITOR_TEST_DATABASE_URL"), reason="necesita un Postgres (QUBITOR_TEST_DATABASE_URL)"
)


# Rol y nombre a partir del token de Clerk (sin base)


@pytest.mark.parametrize(
    ("claims", "rol"),
    [
        ({"sub": "u", "org_id": "org_1", "org_role": "org:admin"}, MemberRole.ADMIN),  # v1
        ({"sub": "u", "org_id": "org_1", "org_role": "admin"}, MemberRole.ADMIN),  # v1 sin prefijo
        ({"sub": "u", "org_id": "org_1", "org_role": "org:member"}, MemberRole.MEMBER),
        ({"sub": "u", "org_id": "org_1", "org_role": "org:auditor"}, MemberRole.MEMBER),  # rol propio
        ({"sub": "u", "org_id": "org_1"}, MemberRole.MEMBER),  # sin rol: no se asume admin
        ({"sub": "u", "o": {"id": "org_1", "rol": "admin"}}, MemberRole.ADMIN),  # v2
        ({"sub": "u", "o": {"id": "org_1", "rol": "member"}}, MemberRole.MEMBER),
        ({"sub": "u"}, MemberRole.ADMIN),  # organización personal
    ],
)
def test_rol_desde_el_token(claims, rol):
    assert organization_role(claims) is rol


@pytest.mark.parametrize(
    ("claims", "nombre"),
    [({"org_slug": "acme"}, "acme"), ({"o": {"id": "x", "slg": "acme-v2"}}, "acme-v2"), ({}, None)],
)
def test_nombre_de_la_organizacion(claims, nombre):
    assert organization_name(claims) == nombre


# Perfiles de Clerk


def test_sin_clave_secreta_no_consulta_a_clerk(monkeypatch):
    monkeypatch.delenv("CLERK_SECRET_KEY", raising=False)
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: pytest.fail("no debería consultar"))
    assert fetch_profiles(["user_abc"]) == {}


def test_la_clave_solo_viaja_por_https(monkeypatch):
    monkeypatch.setenv("CLERK_SECRET_KEY", "sk_test")
    monkeypatch.setenv("CLERK_API_URL", "http://api.clerk.com/v1")
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: pytest.fail("no debería consultar"))
    assert fetch_profiles(["user_abc"]) == {}


def test_arma_el_perfil_y_descarta_ids_raros(monkeypatch):
    pedidos = []

    def urlopen(request, timeout):
        pedidos.append(request)
        cuerpo = [
            {"id": "user_abc", "first_name": "Ana", "last_name": "Gómez", "image_url": "https://img/ana"},
            {"id": "user_def", "first_name": None, "last_name": None, "username": "dev", "image_url": None},
        ]
        return io.BytesIO(json.dumps(cuerpo).encode())

    monkeypatch.setenv("CLERK_SECRET_KEY", "sk_test")
    monkeypatch.delenv("CLERK_API_URL", raising=False)
    monkeypatch.setattr(urllib.request, "urlopen", urlopen)

    perfiles = fetch_profiles(["user_abc", "user_def", "demo-user", "user_x/../../admin"])

    assert perfiles == {
        "user_abc": ClerkProfile("Ana Gómez", "https://img/ana"),
        "user_def": ClerkProfile("dev", None),
    }
    [pedido] = pedidos
    assert "demo-user" not in pedido.full_url and "admin" not in pedido.full_url
    assert pedido.get_header("User-agent") == "Qubitor"


def test_si_clerk_falla_devuelve_vacio(monkeypatch):
    def caido(*a, **k):
        raise urllib.error.URLError("sin red")

    monkeypatch.setenv("CLERK_SECRET_KEY", "sk_test")
    monkeypatch.setattr(urllib.request, "urlopen", caido)
    assert fetch_profiles(["user_abc"]) == {}


# Endpoints y permisos (con Postgres)


class _Jwks:
    def get_signing_key_from_jwt(self, token):
        return type("Clave", (), {"key": CLAVE.public_key()})()


@pytest.fixture
def db():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.models.database import Base

    engine = create_engine(os.environ["QUBITOR_TEST_DATABASE_URL"])
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
    monkeypatch.setattr(routes, "enqueue_scan", lambda scan_id, url: None)
    monkeypatch.setattr(organization, "fetch_profiles", lambda ids: {})

    def sesion():
        with db() as session:
            yield session

    app.dependency_overrides[get_db] = sesion
    yield TestClient(app)
    app.dependency_overrides.clear()


def token(sub, org=None, role=None, slug=None):
    ahora = int(time.time())
    claims = {"iss": ISSUER, "sub": sub, "iat": ahora, "exp": ahora + 60}
    if org:
        claims |= {"org_id": org, "org_role": role or "org:member"}
    if slug:
        claims["org_slug"] = slug
    return {"Authorization": f"Bearer {jwt.encode(claims, CLAVE, algorithm='RS256')}"}


ADMIN = {"sub": "user_admin", "org": "org_acme", "role": "org:admin", "slug": "acme"}
MIEMBRO = {"sub": "user_miembro", "org": "org_acme", "role": "org:member", "slug": "acme"}


@necesita_postgres
def test_sin_organizacion_es_admin_de_la_personal(client):
    yo = client.get("/me", headers=token("user_solo")).json()

    assert yo["role"] == "admin"
    assert yo["organization"]["personal"] is True
    assert yo["organization"]["name"] == "Personal"
    assert yo["permissions"] == {"connect_repositories": True, "start_scans": True, "update_findings": True}


@necesita_postgres
def test_el_rol_y_el_nombre_salen_de_clerk(client):
    admin = client.get("/me", headers=token(**ADMIN)).json()
    miembro = client.get("/me", headers=token(**MIEMBRO)).json()

    assert (admin["role"], miembro["role"]) == ("admin", "member")
    assert admin["organization"] == miembro["organization"]
    assert admin["organization"]["name"] == "acme"
    assert miembro["permissions"]["connect_repositories"] is False


@necesita_postgres
def test_un_miembro_no_puede_conectar_repos_pero_si_escanear(client):
    assert client.post("/repositories", json={"url": URL}, headers=token(**MIEMBRO)).status_code == 403
    repo = client.post("/repositories", json={"url": URL}, headers=token(**ADMIN)).json()

    # El miembro ve el repo que conectó el admin y lo puede escanear.
    assert [r["id"] for r in client.get("/repositories", headers=token(**MIEMBRO)).json()] == [repo["id"]]
    assert client.post(f"/repositories/{repo['id']}/scans", headers=token(**MIEMBRO)).status_code == 202


@necesita_postgres
def test_el_403_explica_el_motivo(client):
    respuesta = client.post("/repositories", json={"url": URL}, headers=token(**MIEMBRO))
    assert "administrador" in respuesta.json()["detail"]


@necesita_postgres
def test_un_miembro_no_puede_conectar_repos_de_github(client, monkeypatch):
    from app.integrations.github import routes as github_routes

    llamadas = []
    monkeypatch.setattr(github_routes, "get_github_token", lambda clerk_user_id: llamadas.append(clerk_user_id) or "t")

    respuesta = client.post("/github/repositories", json={"full_name": "acme/demo"}, headers=token(**MIEMBRO))

    assert respuesta.status_code == 403
    assert llamadas == []  # ni siquiera se pidió su token de GitHub


@necesita_postgres
def test_si_clerk_le_cambia_el_rol_se_aplica_en_el_proximo_pedido(client):
    assert client.post("/repositories", json={"url": URL}, headers=token(**MIEMBRO)).status_code == 403

    ascendido = MIEMBRO | {"role": "org:admin"}
    assert client.post("/repositories", json={"url": URL}, headers=token(**ascendido)).status_code == 201

    [miembro] = [m for m in client.get("/organization/members", headers=token(**ascendido)).json() if m["is_you"]]
    assert miembro["role"] == "admin"


@necesita_postgres
def test_lista_los_miembros_de_la_organizacion(client, monkeypatch):
    monkeypatch.setattr(
        organization, "fetch_profiles", lambda ids: {"user_admin": ClerkProfile("Ana Gómez", "https://img/ana")}
    )
    client.get("/me", headers=token(**MIEMBRO))
    client.get("/me", headers=token(**ADMIN))
    client.get("/me", headers=token("user_otra", org="org_otra", role="org:admin"))

    miembros = client.get("/organization/members", headers=token(**MIEMBRO)).json()

    assert [(m["role"], m["name"], m["is_you"]) for m in miembros] == [
        ("admin", "Ana Gómez", False),
        ("member", None, True),
    ]
    assert all(m["joined_at"] and m["last_seen_at"] for m in miembros)


@necesita_postgres
def test_cambiar_de_organizacion_conserva_las_membresias(client):
    client.get("/me", headers=token(**ADMIN))
    # La misma persona pasa a trabajar en otra organización de Clerk.
    otra = client.get("/me", headers=token("user_admin", org="org_beta", role="org:member", slug="beta")).json()
    assert (otra["organization"]["name"], otra["role"]) == ("beta", "member")

    # Sigue figurando como admin en acme, y ve solo los repos de la organización activa.
    miembros_acme = client.get("/organization/members", headers=token(**MIEMBRO)).json()
    assert ("admin", False) in [(m["role"], m["is_you"]) for m in miembros_acme]
    assert client.get("/repositories", headers=token("user_admin", org="org_beta", role="org:member")).json() == []


@necesita_postgres
def test_los_miembros_de_otra_organizacion_no_se_ven(client):
    client.get("/me", headers=token(**ADMIN))
    ajenos = client.get("/organization/members", headers=token("user_otra", org="org_otra", role="org:admin")).json()
    assert [m["is_you"] for m in ajenos] == [True]


@necesita_postgres
def test_modo_demo_es_admin(client, monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "true")
    assert client.get("/me").json()["role"] == "admin"
