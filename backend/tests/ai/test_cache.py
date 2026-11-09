"""Caché del triage en Postgres (Módulo E)."""

import os

import pytest

from app.ai.cache import SqlTriageCache
from app.ai.triage import content_key
from app.engines.base import Finding, Severity

TEST_DATABASE_URL = os.getenv("QUBITOR_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_DATABASE_URL, reason="necesita un Postgres (QUBITOR_TEST_DATABASE_URL)")


@pytest.fixture
def db():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    import app.models.models  # noqa: F401 (registra las tablas en Base.metadata)
    from app.models.database import Base

    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.drop_all(engine)
    engine.dispose()


def _hallazgo(snippet="eval(x)"):
    return Finding(
        engine="sast", rule_id="sast.bandit.B307", title="Uso de eval()", severity=Severity.HIGH,
        file_path="app/utils.py", line=3, snippet=snippet, description="eval ejecuta código",
    )


def _repo_con_escaneos(db, org_id="org_1", url="https://github.com/acme/demo"):
    """Un repo con un escaneo viejo ya evaluado por la IA y uno nuevo sin evaluar."""
    from app.models.models import Finding as Fila
    from app.models.models import Organization, Repository, Scan, ScanStatus

    viejo = _hallazgo()
    with db() as session, session.begin():
        org = Organization(name=org_id, clerk_org_id=org_id)
        repo = Repository(organization=org, full_name="acme/demo", url=url)
        anterior = Scan(repository=repo, status=ScanStatus.COMPLETED)
        nuevo = Scan(repository=repo)
        session.add_all([org, repo, anterior, nuevo])
        session.flush()
        session.add(Fila(
            scan_id=anterior.id, fingerprint="fp-eval", engine=viejo.engine, rule_id=viejo.rule_id,
            title=viejo.title, severity=viejo.severity, file_path=viejo.file_path, line=viejo.line,
            snippet=viejo.snippet, description=viejo.description, metadata_={},
            ai_is_false_positive=False, ai_adjusted_severity=Severity.CRITICAL,
            ai_explanation="Ejecuta código del usuario", ai_remediation="Usar ast.literal_eval",
        ))
        return str(nuevo.id)


def test_reutiliza_la_evaluacion_de_un_escaneo_anterior_del_mismo_repo(db):
    scan_id = _repo_con_escaneos(db)
    clave = content_key("fp-eval", _hallazgo())

    encontrados = SqlTriageCache(scan_id, db).get_many([clave])

    resultado = encontrados[clave]
    assert resultado.adjusted_severity == Severity.CRITICAL
    assert resultado.remediation == "Usar ast.literal_eval"


def test_si_cambio_el_codigo_no_hay_cache(db):
    scan_id = _repo_con_escaneos(db)

    assert SqlTriageCache(scan_id, db).get_many([content_key("fp-eval", _hallazgo("eval(y)"))]) == {}


def test_no_comparte_evaluaciones_entre_organizaciones(db):
    _repo_con_escaneos(db, org_id="org_1")
    scan_de_otra_org = _repo_con_escaneos(db, org_id="org_2", url="https://github.com/acme/demo")
    clave = content_key("fp-eval", _hallazgo())

    from app.models.models import Finding as Fila

    with db() as session:
        # Cada org tiene su propia evaluación; la búsqueda solo ve la de su repo.
        assert session.query(Fila).count() == 2

    encontrados = SqlTriageCache(scan_de_otra_org, db).get_many([clave])
    assert len(encontrados) == 1


def test_escaneo_inexistente_o_id_invalido(db):
    import uuid

    clave = content_key("fp-eval", _hallazgo())

    assert SqlTriageCache(str(uuid.uuid4()), db).get_many([clave]) == {}
    assert SqlTriageCache("no-es-uuid", db).get_many([clave]) == {}
