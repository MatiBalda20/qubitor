"""Token para clonar repos privados desde el worker (Módulo E)."""

import os
import subprocess
import sys
import uuid

import pytest

from app.integrations.github import tokens
from app.integrations.github.errors import GitHubNotLinked, GitHubUnavailable
from app.integrations.github.tokens import clone_token_for_scan
from app.worker.clone import CloneError, CloneRejected

TEST_DATABASE_URL = os.getenv("QUBITOR_TEST_DATABASE_URL")
necesita_postgres = pytest.mark.skipif(not TEST_DATABASE_URL, reason="necesita un Postgres (QUBITOR_TEST_DATABASE_URL)")


def test_el_worker_importa_sin_database_url():
    """El scan-worker puede correr sin base (LogScanStore): el Módulo E no debe romperlo."""
    env = {k: v for k, v in os.environ.items() if k != "DATABASE_URL"}
    env["PYTHONPATH"] = os.getcwd()
    proceso = subprocess.run(
        [sys.executable, "-c", "import app.worker.job"],
        env=env, capture_output=True, text=True, timeout=60,
    )
    assert proceso.returncode == 0, proceso.stderr


def test_sin_repos_privados_habilitados_no_consulta_nada(monkeypatch):
    monkeypatch.delenv("GITHUB_PRIVATE_REPOS", raising=False)

    def explota():
        raise AssertionError("no debería abrir una sesión")

    assert clone_token_for_scan(str(uuid.uuid4()), session_factory=explota) is None


@pytest.fixture
def db(monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.models.database import Base

    monkeypatch.setenv("GITHUB_PRIVATE_REPOS", "true")
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.drop_all(engine)
    engine.dispose()


def _escaneo(db, privado=True, con_usuario=True):
    from app.models.models import Organization, Repository, Scan, User

    with db() as session, session.begin():
        org = Organization(name="Acme", clerk_org_id="org_1")
        usuario = User(clerk_user_id="user_7", organization=org) if con_usuario else None
        session.add(org)
        if usuario:
            session.add(usuario)
        session.flush()
        repo = Repository(
            organization=org, full_name="acme/privado", url="https://github.com/acme/privado",
            is_private=privado, connected_by_user_id=usuario.id if usuario else None,
        )
        scan = Scan(repository=repo)
        session.add_all([repo, scan])
        session.flush()
        return str(scan.id)


@necesita_postgres
def test_repo_publico_no_necesita_token(db, monkeypatch):
    monkeypatch.setattr(tokens, "get_github_token", lambda _: pytest.fail("no debería pedir token"))

    assert clone_token_for_scan(_escaneo(db, privado=False), session_factory=db) is None


@necesita_postgres
def test_repo_privado_usa_el_token_de_quien_lo_conecto(db, monkeypatch):
    pedidos = []
    monkeypatch.setattr(tokens, "get_github_token", lambda uid: pedidos.append(uid) or "gho_privado")

    assert clone_token_for_scan(_escaneo(db), session_factory=db) == "gho_privado"
    assert pedidos == ["user_7"]


@necesita_postgres
def test_repo_privado_sin_usuario_no_se_reintenta(db):
    with pytest.raises(CloneRejected):
        clone_token_for_scan(_escaneo(db, con_usuario=False), session_factory=db)


@necesita_postgres
def test_usuario_que_desvinculo_github_no_se_reintenta(db, monkeypatch):
    def sin_github(_):
        raise GitHubNotLinked("sin GitHub")

    monkeypatch.setattr(tokens, "get_github_token", sin_github)

    with pytest.raises(CloneRejected):
        clone_token_for_scan(_escaneo(db), session_factory=db)


@necesita_postgres
def test_clerk_caido_es_una_falla_transitoria(db, monkeypatch):
    def caido(_):
        raise GitHubUnavailable("Clerk no responde")

    monkeypatch.setattr(tokens, "get_github_token", caido)

    with pytest.raises(CloneError) as error:
        clone_token_for_scan(_escaneo(db), session_factory=db)
    assert not isinstance(error.value, CloneRejected)


@necesita_postgres
def test_escaneo_inexistente_o_id_invalido(db):
    assert clone_token_for_scan(str(uuid.uuid4()), session_factory=db) is None
    assert clone_token_for_scan("no-es-un-uuid", session_factory=db) is None
