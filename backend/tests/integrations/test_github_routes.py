"""Endpoints /github del Módulo E contra un Postgres real, con GitHub simulado."""

import os
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app.api import auth
from app.integrations.github import routes as github_routes
from app.integrations.github.client import GitHubRepo, RepoPage
from app.integrations.github.errors import GitHubNotLinked, GitHubNotFound, GitHubRateLimited

TEST_DATABASE_URL = os.getenv("QUBITOR_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_DATABASE_URL, reason="necesita un Postgres (QUBITOR_TEST_DATABASE_URL)")

ISSUER = "https://test.clerk.example"
CLAVE = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class _Jwks:
    def get_signing_key_from_jwt(self, token):
        return type("Clave", (), {"key": CLAVE.public_key()})()


def _repo(full_name="acme/demo", **cambios):
    datos = dict(
        full_name=full_name, url=f"https://github.com/{full_name}", private=False, description="d",
        default_branch="main", size_bytes=1024, updated_at="2026-11-08T10:00:00Z", archived=False, can_read=True,
    )
    datos.update(cambios)
    return GitHubRepo(**datos)


class _GitHubFalso:
    def __init__(self):
        self.repos = {"acme/demo": _repo(), "acme/privado": _repo("acme/privado", private=True)}
        self.error = None
        self.pedidos = []

    def list_repositories(self, page=1, per_page=30):
        self.pedidos.append(("list", page, per_page))
        if self.error:
            raise self.error
        return RepoPage(items=list(self.repos.values()), page=page, has_next=page < 2)

    def get_repository(self, full_name):
        self.pedidos.append(("get", full_name))
        if self.error:
            raise self.error
        if full_name not in self.repos:
            raise GitHubNotFound("El repositorio no existe o tu cuenta no tiene acceso")
        return self.repos[full_name]


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
def github():
    return _GitHubFalso()


@pytest.fixture
def client(db, monkeypatch, github):
    from app.main import app
    from app.models.database import get_db

    monkeypatch.setenv("CLERK_ISSUER", ISSUER)
    monkeypatch.delenv("AUTH_DISABLED", raising=False)
    monkeypatch.delenv("GITHUB_PRIVATE_REPOS", raising=False)
    monkeypatch.setattr(auth, "_jwks_client", lambda issuer: _Jwks())

    def sesion():
        with db() as session:
            yield session

    app.dependency_overrides[get_db] = sesion
    app.dependency_overrides[github_routes.get_github_client] = lambda: github
    yield TestClient(app)
    app.dependency_overrides.clear()


def headers(sub="user_1", org="org_1"):
    ahora = int(time.time())
    claims = {"iss": ISSUER, "sub": sub, "iat": ahora, "exp": ahora + 60, "org_id": org}
    return {"Authorization": f"Bearer {jwt.encode(claims, CLAVE, algorithm='RS256')}"}


def test_sin_sesion_responde_401(client):
    assert client.get("/github/repositories").status_code == 401
    assert client.post("/github/repositories", json={"full_name": "acme/demo"}).status_code == 401


def test_lista_los_repos_con_paginacion(client, github):
    respuesta = client.get("/github/repositories?page=1&per_page=20", headers=headers())

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert [r["full_name"] for r in cuerpo["items"]] == ["acme/demo", "acme/privado"]
    assert cuerpo["page"] == 1 and cuerpo["has_next"] is True
    assert github.pedidos == [("list", 1, 20)]
    # Ninguna respuesta incluye el token de GitHub.
    assert "token" not in respuesta.text.lower()


def test_los_privados_no_se_pueden_conectar_si_no_estan_habilitados(client):
    items = client.get("/github/repositories", headers=headers()).json()["items"]
    privado = next(r for r in items if r["full_name"] == "acme/privado")

    assert privado["connectable"] is False
    assert "privados" in privado["reason"]


def test_marca_los_repos_ya_conectados_por_la_organizacion(client):
    client.post("/github/repositories", json={"full_name": "acme/demo"}, headers=headers())

    propios = client.get("/github/repositories", headers=headers()).json()["items"]
    de_otra_org = client.get("/github/repositories", headers=headers("user_2", "org_2")).json()["items"]

    assert next(r for r in propios if r["full_name"] == "acme/demo")["connected"] is True
    assert next(r for r in de_otra_org if r["full_name"] == "acme/demo")["connected"] is False


def test_conectar_un_repo_publico(client, db):
    from app.models.models import Repository, User

    respuesta = client.post("/github/repositories", json={"full_name": "acme/demo"}, headers=headers())

    assert respuesta.status_code == 201
    assert respuesta.json()["url"] == "https://github.com/acme/demo"
    with db() as session:
        repo = session.query(Repository).one()
        usuario = session.query(User).one()
        assert repo.is_private is False
        assert repo.connected_by_user_id == usuario.id


def test_conectar_dos_veces_devuelve_el_mismo(client):
    primero = client.post("/github/repositories", json={"full_name": "acme/demo"}, headers=headers())
    segundo = client.post("/github/repositories", json={"full_name": "acme/demo"}, headers=headers())

    assert segundo.status_code == 200
    assert segundo.json()["id"] == primero.json()["id"]


def test_conectar_un_privado_con_la_opcion_habilitada(client, db, monkeypatch):
    from app.models.models import Repository

    monkeypatch.setenv("GITHUB_PRIVATE_REPOS", "true")

    respuesta = client.post("/github/repositories", json={"full_name": "acme/privado"}, headers=headers())

    assert respuesta.status_code == 201
    with db() as session:
        assert session.query(Repository).one().is_private is True


def test_conectar_un_privado_sin_la_opcion_responde_422(client):
    respuesta = client.post("/github/repositories", json={"full_name": "acme/privado"}, headers=headers())

    assert respuesta.status_code == 422


def test_repo_sin_permiso_de_lectura(client, github):
    github.repos["acme/ajeno"] = _repo("acme/ajeno", can_read=False)

    respuesta = client.post("/github/repositories", json={"full_name": "acme/ajeno"}, headers=headers())

    assert respuesta.status_code == 422
    assert "permiso" in respuesta.json()["detail"]


def test_repo_de_mas_de_50_mb(client, github):
    github.repos["acme/enorme"] = _repo("acme/enorme", size_bytes=60 * 1024 * 1024)

    respuesta = client.post("/github/repositories", json={"full_name": "acme/enorme"}, headers=headers())

    assert respuesta.status_code == 422
    assert "50 MB" in respuesta.json()["detail"]


def test_repo_inexistente_responde_404(client):
    respuesta = client.post("/github/repositories", json={"full_name": "acme/no-existe"}, headers=headers())

    assert respuesta.status_code == 404


@pytest.mark.parametrize("nombre", ["acme", "../etc/passwd", "acme/demo/extra", "a" * 250])
def test_nombres_invalidos_responden_422_sin_llamar_a_github(client, github, nombre):
    respuesta = client.post("/github/repositories", json={"full_name": nombre}, headers=headers())

    assert respuesta.status_code == 422
    assert not [p for p in github.pedidos if p[0] == "get"]


def test_cuenta_sin_github_conectado_responde_409(client, github):
    github.error = GitHubNotLinked("Conectá tu cuenta de GitHub para ver tus repositorios")

    respuesta = client.get("/github/repositories", headers=headers())

    assert respuesta.status_code == 409
    assert "GitHub" in respuesta.json()["detail"]


def test_cuota_de_github_agotada_responde_429_con_retry_after(client, github):
    github.error = GitHubRateLimited("Se agotó la cuota", retry_after=30)

    respuesta = client.get("/github/repositories", headers=headers())

    assert respuesta.status_code == 429
    assert respuesta.headers["Retry-After"] == "30"


def test_el_token_se_pide_a_clerk_con_el_usuario_de_la_sesion(db, monkeypatch):
    """Sin reemplazar get_github_client: se usa el clerk_user_id de quien hizo el request."""
    from app.main import app
    from app.models.database import get_db

    monkeypatch.setenv("CLERK_ISSUER", ISSUER)
    monkeypatch.delenv("AUTH_DISABLED", raising=False)
    monkeypatch.setattr(auth, "_jwks_client", lambda issuer: _Jwks())
    pedidos = []

    def token_falso(clerk_user_id):
        pedidos.append(clerk_user_id)
        raise GitHubNotLinked("Conectá tu cuenta de GitHub para ver tus repositorios")

    monkeypatch.setattr(github_routes, "get_github_token", token_falso)

    def sesion():
        with db() as session:
            yield session

    app.dependency_overrides[get_db] = sesion
    try:
        respuesta = TestClient(app).get("/github/repositories", headers=headers("user_42", "org_9"))
    finally:
        app.dependency_overrides.clear()

    assert respuesta.status_code == 409
    assert pedidos == ["user_42"]
