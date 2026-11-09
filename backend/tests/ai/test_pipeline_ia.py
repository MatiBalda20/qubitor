"""Etapa de IA dentro del pipeline del escaneo (Módulo E)."""

import json
import os
import uuid
from pathlib import Path

import pytest

from app.ai import pipeline as ai_pipeline
from app.ai.gemini import GeminiQuotaExceeded
from app.ai.pipeline import adjusted_risk_score, apply_ai
from app.ai.triage import TriageOutcome, TriageResult
from app.engines.base import Finding, Severity
from app.orchestrator.pipeline import ScanResult
from app.orchestrator.risk import grade, risk_score
from app.worker import job as job_module

TEST_DATABASE_URL = os.getenv("QUBITOR_TEST_DATABASE_URL")


def _finding(n, engine="sast", severity=Severity.HIGH):
    return Finding(
        engine=engine, rule_id=f"{engine}.r{n}", title=f"Hallazgo {n}", severity=severity,
        file_path=f"app/f{n}.py", line=n, snippet="eval(x)", description="d",
    )


def _resultado(findings):
    score = risk_score(f.severity for f in findings.values())
    return ScanResult(findings=findings, errors={}, risk_score=score, grade=grade(score), duration_seconds=1.0, engine_count=4)


class _Gemini:
    """Responde el triage y el resumen según el esquema que le piden."""

    def __init__(self, triage=None, error=None):
        self.triage = triage or {}
        self.error = error
        self.llamadas = 0

    def generate_json(self, *, system, prompt, schema):
        self.llamadas += 1
        if self.error:
            raise self.error
        if "results" in schema["properties"]:
            fps = [h["fingerprint"] for h in json.loads(prompt.split("\n", 1)[1])["hallazgos"]]
            return {"results": [
                {"fingerprint": fp, "explanation": "e", "remediation": "r",
                 **self.triage.get(fp, {"is_false_positive": False, "adjusted_severity": "high"})}
                for fp in fps
            ]}
        return {"headline": "Titular", "summary": "Resumen", "top_risks": [], "priorities": []}


def test_recalcula_el_score_con_el_triage():
    hallazgos = {"a": _finding(1), "b": _finding(2), "c": _finding(3)}
    gemini = _Gemini({
        "a": {"is_false_positive": True, "adjusted_severity": "high"},
        "b": {"is_false_positive": False, "adjusted_severity": "critical"},
    })

    resultado = apply_ai("scan-1", _resultado(hallazgos), model=gemini)

    # a es falso positivo (no cuenta), b pasa a critical (10) y c sigue high (5).
    assert resultado.risk_score == 85.0
    assert resultado.grade == "B"
    assert set(resultado.triage) == {"a", "b", "c"}
    assert resultado.summary["generated_by"] == "gemini"
    assert resultado.findings == hallazgos  # no se pierde ni se modifica ningún hallazgo


def test_si_gemini_no_responde_se_conservan_hallazgos_y_score():
    hallazgos = {"a": _finding(1), "b": _finding(2)}
    original = _resultado(hallazgos)

    resultado = apply_ai("scan-1", original, model=_Gemini(error=GeminiQuotaExceeded("429")))

    assert resultado.findings == hallazgos
    assert resultado.risk_score == original.risk_score
    assert resultado.triage == {}
    assert resultado.summary["generated_by"] == "heuristic"
    assert resultado.summary["triage_status"] == "quota_exceeded"


def test_sin_gemini_configurado_igual_hay_resumen(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    resultado = apply_ai("scan-1", _resultado({"a": _finding(1)}))

    assert resultado.triage == {}
    assert resultado.summary["generated_by"] == "heuristic"
    assert resultado.summary["triage_status"] == "disabled"


def test_un_error_inesperado_no_rompe_el_escaneo(monkeypatch):
    def explota(*_, **__):
        raise RuntimeError("bug")

    monkeypatch.setattr(ai_pipeline, "triage_findings", explota)
    original = _resultado({"a": _finding(1)})

    assert apply_ai("scan-1", original, model=_Gemini()) is original


def test_score_ajustado_ignora_falsos_positivos_y_usa_la_severidad_de_la_ia():
    resultado = _resultado({"a": _finding(1, severity=Severity.LOW), "b": _finding(2)})
    outcome = TriageOutcome(results={
        "a": TriageResult(False, Severity.CRITICAL, "e", "r"),
        "b": TriageResult(True, Severity.HIGH, "e", "r"),
    })

    assert adjusted_risk_score(resultado, outcome) == 90.0


# El job del worker con la etapa de IA


@pytest.fixture
def job(monkeypatch, tmp_path):
    guardados = []

    class _Store:
        def mark_running(self, scan_id):
            pass

        def save_result(self, scan_id, commit_sha, result):
            guardados.append(result)

        def mark_failed(self, scan_id, error):
            guardados.append(("failed", error))

    def clon(url, destino, **_):
        os.makedirs(destino)
        Path(destino, "app.py").write_text("x = eval(input())\n")
        return "c" * 40

    class _Motor:
        name = "sast"

        def scan(self, repo_path):
            return [_finding(1, severity=Severity.HIGH)]

    monkeypatch.setattr(job_module, "get_store", lambda: _Store())
    monkeypatch.setattr(job_module, "clone_repository", clon)
    monkeypatch.setattr(job_module, "clone_token_for_scan", lambda scan_id: None)
    monkeypatch.setattr(job_module, "default_engines", lambda: [_Motor()])
    monkeypatch.setattr(job_module, "archive_scan", lambda *args: False)
    monkeypatch.setenv("REPOS_DIR", str(tmp_path))
    return guardados


def test_el_job_guarda_el_triage_y_el_resumen(job, monkeypatch):
    monkeypatch.setattr(ai_pipeline, "_default_model", lambda: _Gemini({}))
    monkeypatch.setattr(ai_pipeline, "_default_cache", lambda scan_id: None)

    resumen = job_module.run_scan("scan-1", "https://github.com/acme/demo")

    guardado = job[0]
    assert len(guardado.triage) == 1
    assert guardado.summary["headline"] == "Titular"
    assert resumen["status"] == "completed" and resumen["triaged"] == 1


def test_el_job_termina_aunque_gemini_falle(job, monkeypatch):
    monkeypatch.setattr(ai_pipeline, "_default_model", lambda: _Gemini(error=GeminiQuotaExceeded("429")))
    monkeypatch.setattr(ai_pipeline, "_default_cache", lambda scan_id: None)

    resumen = job_module.run_scan("scan-2", "https://github.com/acme/demo")

    assert resumen["status"] == "completed"
    assert resumen["findings"] == 1 and resumen["triaged"] == 0


# Persistencia en Postgres


@pytest.mark.skipif(not TEST_DATABASE_URL, reason="necesita un Postgres (QUBITOR_TEST_DATABASE_URL)")
def test_sql_store_guarda_el_triage_y_el_resumen():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    import app.models.models  # noqa: F401
    from app.models.database import Base
    from app.models.models import Finding as Fila
    from app.models.models import Organization, Repository, Scan
    from app.worker.sql_store import SqlScanStore

    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        with db() as session, session.begin():
            org = Organization(name="Acme", clerk_org_id="org_1")
            scan = Scan(repository=Repository(organization=org, full_name="acme/demo", url="https://github.com/acme/demo"))
            session.add_all([org, scan])
            session.flush()
            scan_id = str(scan.id)

        resultado = apply_ai(scan_id, _resultado({"a": _finding(1), "b": _finding(2)}), model=_Gemini({
            "a": {"is_false_positive": True, "adjusted_severity": "medium"},
        }), cache=None)
        SqlScanStore(db).save_result(scan_id, "d" * 40, resultado)

        with db() as session:
            filas = {f.fingerprint: f for f in session.query(Fila).all()}
            guardado = session.get(Scan, uuid.UUID(scan_id))
            assert filas["a"].ai_is_false_positive is True
            assert filas["a"].ai_adjusted_severity == Severity.MEDIUM
            assert filas["b"].ai_explanation == "e" and filas["b"].ai_remediation == "r"
            assert guardado.ai_summary["headline"] == "Titular"
            assert guardado.risk_score == 95.0
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()
