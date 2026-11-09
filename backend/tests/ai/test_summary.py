"""Resumen ejecutivo del escaneo (Módulo E)."""

import json

from app.ai.gemini import GeminiQuotaExceeded
from app.ai.summary import SUMMARY_SCHEMA, build_summary
from app.ai.triage import TriageOutcome, TriageResult
from app.engines.base import Finding, Severity


def _finding(n, engine="sast", severity=Severity.HIGH, title=None, snippet="eval(x)"):
    return Finding(
        engine=engine, rule_id=f"{engine}.r{n}", title=title or f"Hallazgo {n}", severity=severity,
        file_path=f"app/f{n}.py", line=n, snippet=snippet, description="d",
    )


HALLAZGOS = {
    "s": _finding(1, engine="secrets", severity=Severity.CRITICAL, title="AWS Access Key expuesta",
                  snippet="KEY = 'AKIAABCDEFGHIJKLMNOP'"),
    "q": _finding(2, title="Consulta SQL armada con strings"),
    "d": _finding(3, engine="sca", severity=Severity.MEDIUM, title="requests 2.19.0 vulnerable"),
    "i": _finding(4, engine="crypto", severity=Severity.INFO, title="Uso de SHA-256"),
}


class _Modelo:
    def __init__(self, respuesta=None, error=None):
        self.respuesta = respuesta
        self.error = error
        self.prompts = []

    def generate_json(self, *, system, prompt, schema):
        assert schema is SUMMARY_SCHEMA
        self.prompts.append(prompt)
        if self.error:
            raise self.error
        return self.respuesta


RESPUESTA = {
    "headline": "Una credencial expuesta pone en riesgo la nube",
    "summary": "El repositorio tiene una clave de AWS expuesta y una inyección SQL.",
    "top_risks": [
        {"title": "Clave de AWS expuesta", "impact": "Acceso a la cuenta de AWS", "priority": "inmediata"},
        {"title": "Inyección SQL", "impact": "Robo de datos de clientes", "priority": "alta"},
        {"title": "Dependencia vulnerable", "impact": "Explotación conocida", "priority": "media"},
    ],
    "priorities": ["Rotar la clave", "Parametrizar la consulta", "Actualizar requests"],
}


def test_resumen_con_gemini():
    modelo = _Modelo(RESPUESTA)

    resumen = build_summary(HALLAZGOS, 83.0, "B", TriageOutcome(status="completed"), modelo)

    assert resumen["generated_by"] == "gemini"
    assert resumen["headline"] == RESPUESTA["headline"]
    assert len(resumen["top_risks"]) == 3
    assert resumen["status"] == "acceptable" and resumen["grade"] == "B"
    assert resumen["triage_status"] == "completed"


def test_a_gemini_solo_le_llegan_datos_agregados_sin_codigo():
    modelo = _Modelo(RESPUESTA)

    build_summary(HALLAZGOS, 83.0, "B", TriageOutcome(), modelo)

    prompt = modelo.prompts[0]
    assert "AKIAABCDEFGHIJKLMNOP" not in prompt
    assert "eval(x)" not in prompt
    datos = json.loads(prompt.split("\n", 1)[1])
    assert datos["open_findings"] == 3  # el inventario no cuenta
    assert datos["by_severity"] == {"critical": 1, "high": 1, "medium": 1}
    assert datos["top_findings"][0]["severity"] == "critical"


def test_usa_la_severidad_ajustada_y_descarta_falsos_positivos():
    triage = TriageOutcome(results={
        "q": TriageResult(True, Severity.HIGH, "e", "r"),
        "d": TriageResult(False, Severity.CRITICAL, "e", "r"),
    })
    modelo = _Modelo(RESPUESTA)

    build_summary(HALLAZGOS, 80.0, "B", triage, modelo)

    datos = json.loads(modelo.prompts[0].split("\n", 1)[1])
    assert datos["by_severity"] == {"critical": 2}


def test_si_gemini_falla_usa_el_resumen_heuristico():
    resumen = build_summary(HALLAZGOS, 83.0, "B", TriageOutcome(), _Modelo(error=GeminiQuotaExceeded("429")))

    assert resumen["generated_by"] == "heuristic"
    assert "crítico" in resumen["headline"]
    assert resumen["top_risks"][0]["priority"] == "inmediata"
    assert resumen["top_risks"][0]["title"] == "AWS Access Key expuesta"
    assert resumen["priorities"][0].startswith("Rotar")


def test_sin_gemini_configurado_usa_el_heuristico():
    resumen = build_summary(HALLAZGOS, 83.0, "B", TriageOutcome(status="disabled"), None)

    assert resumen["generated_by"] == "heuristic"
    assert len(resumen["top_risks"]) == 3
    assert resumen["triage_status"] == "disabled"


def test_respuesta_invalida_de_gemini_usa_el_heuristico():
    resumen = build_summary(HALLAZGOS, 83.0, "B", TriageOutcome(), _Modelo({"headline": "", "summary": 3}))

    assert resumen["generated_by"] == "heuristic"


def test_filtra_riesgos_mal_formados_de_gemini():
    respuesta = dict(RESPUESTA, top_risks=[
        {"title": "Bien", "impact": "Impacto", "priority": "alta"},
        {"title": "Prioridad inventada", "impact": "x", "priority": "urgentísima"},
        "texto suelto",
    ])

    resumen = build_summary(HALLAZGOS, 83.0, "B", TriageOutcome(), _Modelo(respuesta))

    assert [r["title"] for r in resumen["top_risks"]] == ["Bien"]


def test_sin_hallazgos_abiertos_no_llama_a_gemini():
    modelo = _Modelo(RESPUESTA)

    resumen = build_summary({"i": HALLAZGOS["i"]}, 100.0, "A", TriageOutcome(), modelo)

    assert modelo.prompts == []
    assert resumen["status"] == "good"
    assert resumen["top_risks"] == []


def test_el_texto_de_gemini_se_enmascara():
    respuesta = dict(RESPUESTA, summary="La clave AKIAABCDEFGHIJKLMNOP quedó expuesta en el repo.")

    resumen = build_summary(HALLAZGOS, 83.0, "B", TriageOutcome(), _Modelo(respuesta))

    assert "AKIAABCDEFGHIJKLMNOP" not in resumen["summary"]


def test_el_resumen_se_puede_guardar_como_json():
    resumen = build_summary(HALLAZGOS, 83.0, "B", TriageOutcome(), None)

    assert json.loads(json.dumps(resumen)) == resumen
