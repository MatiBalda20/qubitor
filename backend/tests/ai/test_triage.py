"""Triage de hallazgos con un Gemini simulado (Módulo E)."""

import json

import pytest

from app.ai.gemini import GeminiInvalidResponse, GeminiQuotaExceeded, GeminiUnavailable
from app.ai.triage import (
    BATCH_SIZE,
    MAX_FINDINGS_PER_SCAN,
    TRIAGE_SCHEMA,
    TriageCache,
    TriageResult,
    content_key,
    triage_findings,
)
from app.engines.base import Finding, Severity


def _finding(n, engine="sast", severity=Severity.HIGH, snippet="eval(x)", **cambios):
    datos = dict(
        engine=engine, rule_id=f"{engine}.regla.{n}", title=f"Hallazgo {n}", severity=severity,
        file_path=f"app/f{n}.py", line=n, snippet=snippet, description="Descripción",
    )
    datos.update(cambios)
    return Finding(**datos)


def _hallazgos(cantidad, **kwargs):
    return {f"fp{n}": _finding(n, **kwargs) for n in range(cantidad)}


class _Modelo:
    """Responde por cada fingerprint del prompt; `respuesta` puede personalizar cada uno."""

    def __init__(self, respuesta=None, errores=None):
        self.respuesta = respuesta or (lambda fp: {"is_false_positive": False, "adjusted_severity": "medium"})
        self.errores = list(errores or [])
        self.prompts = []

    def generate_json(self, *, system, prompt, schema):
        self.prompts.append(prompt)
        assert schema is TRIAGE_SCHEMA
        if self.errores:
            error = self.errores.pop(0)
            if error is not None:
                raise error
        fps = [h["fingerprint"] for h in json.loads(prompt.split("\n", 1)[1])["hallazgos"]]
        return {"results": [
            {"fingerprint": fp, "explanation": f"Explicación de {fp}", "remediation": "Paso 1", **self.respuesta(fp)}
            for fp in fps
        ]}


def _enviados(modelo):
    return [h for p in modelo.prompts for h in json.loads(p.split("\n", 1)[1])["hallazgos"]]


def test_evalua_todos_y_asocia_por_fingerprint():
    modelo = _Modelo(lambda fp: {"is_false_positive": fp == "fp1", "adjusted_severity": "low" if fp == "fp2" else "high"})

    resultado = triage_findings(_hallazgos(3), modelo)

    assert resultado.status == "completed"
    assert set(resultado.results) == {"fp0", "fp1", "fp2"}
    assert resultado.results["fp1"].is_false_positive is True
    assert resultado.results["fp2"].adjusted_severity == Severity.LOW
    assert resultado.results["fp0"].explanation == "Explicación de fp0"


def test_procesa_en_lotes():
    modelo = _Modelo()

    triage_findings(_hallazgos(BATCH_SIZE * 2 + 1), modelo)

    assert len(modelo.prompts) == 3


def test_no_envia_el_inventario_y_respeta_el_tope_por_escaneo():
    hallazgos = _hallazgos(MAX_FINDINGS_PER_SCAN + 10)
    hallazgos["inventario"] = _finding(999, engine="crypto", severity=Severity.INFO)
    modelo = _Modelo()

    resultado = triage_findings(hallazgos, modelo)

    enviados = {h["fingerprint"] for h in _enviados(modelo)}
    assert "inventario" not in enviados
    assert len(enviados) == MAX_FINDINGS_PER_SCAN
    assert resultado.candidates == MAX_FINDINGS_PER_SCAN


def test_prioriza_los_mas_graves_cuando_hay_tope():
    hallazgos = {f"bajo{n}": _finding(n, severity=Severity.LOW) for n in range(MAX_FINDINGS_PER_SCAN)}
    hallazgos["critico"] = _finding(500, severity=Severity.CRITICAL)
    modelo = _Modelo()

    triage_findings(hallazgos, modelo)

    assert _enviados(modelo)[0]["fingerprint"] == "critico"


def test_nunca_envia_secretos_sin_enmascarar_ni_archivos_completos():
    snippet = "\n".join([f"linea {i}" for i in range(30)] + ["AWS = 'AKIAABCDEFGHIJKLMNOP'"])
    hallazgos = {
        "a": _finding(1, snippet="token = 'ghp_" + "a1B2" * 9 + "'"),
        "b": _finding(2, snippet=snippet),
        "c": _finding(3, description="url postgresql://admin:Clave123@db/x"),
    }
    modelo = _Modelo()

    triage_findings(hallazgos, modelo)

    todo = "\n".join(modelo.prompts)
    assert "ghp_" + "a1B2" * 9 not in todo
    assert "Clave123" not in todo
    enviados = {h["fingerprint"]: h for h in _enviados(modelo)}
    assert len(enviados["b"]["fragmento"].splitlines()) == 5


def test_sin_gemini_configurado_no_pierde_hallazgos():
    resultado = triage_findings(_hallazgos(3), model=None)

    assert resultado.status == "disabled"
    assert resultado.results == {}


def test_cuota_agotada_corta_y_deja_el_resto_con_la_severidad_original():
    modelo = _Modelo(errores=[None, GeminiQuotaExceeded("429")])

    resultado = triage_findings(_hallazgos(BATCH_SIZE * 3), modelo)

    assert resultado.status == "quota_exceeded"
    assert len(resultado.results) == BATCH_SIZE
    assert len(modelo.prompts) == 2


def test_un_lote_fallido_no_frena_los_siguientes():
    modelo = _Modelo(errores=[GeminiUnavailable("caído"), None])

    resultado = triage_findings(_hallazgos(BATCH_SIZE * 2), modelo)

    assert resultado.status == "partial"
    assert len(resultado.results) == BATCH_SIZE


def test_dos_errores_seguidos_cortan_el_triage():
    modelo = _Modelo(errores=[GeminiInvalidResponse("x"), GeminiUnavailable("y"), None])

    resultado = triage_findings(_hallazgos(BATCH_SIZE * 3), modelo)

    assert resultado.status == "unavailable"
    assert len(modelo.prompts) == 2


def test_corta_por_tiempo():
    tiempos = iter([0, 0, 1000, 1000])
    modelo = _Modelo()

    resultado = triage_findings(_hallazgos(BATCH_SIZE * 2), modelo, clock=lambda: next(tiempos))

    assert resultado.status == "partial"
    assert len(modelo.prompts) == 1


@pytest.mark.parametrize(
    "item",
    [
        {"fingerprint": "otro", "is_false_positive": False, "adjusted_severity": "low", "explanation": "x", "remediation": ""},
        {"fingerprint": "fp0", "is_false_positive": "sí", "adjusted_severity": "low", "explanation": "x", "remediation": ""},
        {"fingerprint": "fp0", "is_false_positive": False, "adjusted_severity": "gravísima", "explanation": "x", "remediation": ""},
        {"fingerprint": "fp0", "is_false_positive": False, "adjusted_severity": "low", "explanation": "  ", "remediation": ""},
        "no es un objeto",
    ],
)
def test_descarta_respuestas_invalidas(item):
    class _Fijo:
        def generate_json(self, **_):
            return {"results": [item]}

    resultado = triage_findings(_hallazgos(1), _Fijo())

    assert resultado.results == {}
    assert resultado.status == "unavailable"


def test_un_fingerprint_repetido_cuenta_una_sola_vez():
    class _Repetido:
        def generate_json(self, **_):
            item = {"fingerprint": "fp0", "is_false_positive": False, "explanation": "e", "remediation": "r"}
            return {"results": [{**item, "adjusted_severity": "low"}, {**item, "adjusted_severity": "critical"}]}

    resultado = triage_findings(_hallazgos(1, severity=Severity.MEDIUM), _Repetido())

    assert resultado.results["fp0"].adjusted_severity == Severity.LOW


def test_un_secreto_nunca_es_falso_positivo_ni_baja_de_severidad():
    hallazgos = {"s": _finding(1, engine="secrets", severity=Severity.CRITICAL)}
    modelo = _Modelo(lambda fp: {"is_false_positive": True, "adjusted_severity": "info"})

    resultado = triage_findings(hallazgos, modelo)

    assert resultado.results["s"].is_false_positive is False
    assert resultado.results["s"].adjusted_severity == Severity.CRITICAL


def test_un_secreto_si_puede_subir_de_severidad():
    hallazgos = {"s": _finding(1, engine="secrets", severity=Severity.HIGH)}

    resultado = triage_findings(hallazgos, _Modelo(lambda fp: {"is_false_positive": False, "adjusted_severity": "critical"}))

    assert resultado.results["s"].adjusted_severity == Severity.CRITICAL


def test_ningun_hallazgo_baja_mas_de_dos_niveles():
    hallazgos = {"x": _finding(1, severity=Severity.CRITICAL)}

    resultado = triage_findings(hallazgos, _Modelo(lambda fp: {"is_false_positive": False, "adjusted_severity": "info"}))

    assert resultado.results["x"].adjusted_severity == Severity.MEDIUM


def test_el_texto_de_la_ia_se_enmascara():
    class _Eco:
        def generate_json(self, **_):
            return {"results": [{
                "fingerprint": "fp0", "is_false_positive": False, "adjusted_severity": "high",
                "explanation": "La clave AKIAABCDEFGHIJKLMNOP está expuesta", "remediation": "Rotala",
            }]}

    resultado = triage_findings(_hallazgos(1), _Eco())

    assert "AKIAABCDEFGHIJKLMNOP" not in resultado.results["fp0"].explanation


class _CacheEnMemoria(TriageCache):
    def __init__(self):
        self.datos = {}

    def get_many(self, keys):
        return {k: self.datos[k] for k in keys if k in self.datos}

    def put_many(self, entries):
        self.datos.update(entries)


def test_la_cache_evita_volver_a_preguntar():
    cache = _CacheEnMemoria()
    hallazgos = _hallazgos(3)
    triage_findings(hallazgos, _Modelo(), cache=cache)
    segundo = _Modelo()

    resultado = triage_findings(hallazgos, segundo, cache=cache)

    assert segundo.prompts == []
    assert resultado.status == "completed"
    assert resultado.from_cache == 3


def test_si_cambia_el_codigo_la_cache_no_vale():
    cache = _CacheEnMemoria()
    triage_findings({"fp0": _finding(0, snippet="eval(a)")}, _Modelo(), cache=cache)
    segundo = _Modelo()

    triage_findings({"fp0": _finding(0, snippet="eval(b)")}, segundo, cache=cache)

    assert len(segundo.prompts) == 1


def test_cache_sin_gemini_devuelve_lo_que_tiene():
    cache = _CacheEnMemoria()
    hallazgos = _hallazgos(2)
    triage_findings({"fp0": hallazgos["fp0"]}, _Modelo(), cache=cache)

    resultado = triage_findings(hallazgos, model=None, cache=cache)

    assert resultado.status == "partial"
    assert set(resultado.results) == {"fp0"}


def test_una_cache_rota_no_frena_el_triage():
    class _Rota(TriageCache):
        def get_many(self, keys):
            raise RuntimeError("base caída")

        def put_many(self, entries):
            raise RuntimeError("base caída")

    resultado = triage_findings(_hallazgos(2), _Modelo(), cache=_Rota())

    assert resultado.status == "completed"


def test_la_clave_de_cache_incluye_fingerprint_y_contenido():
    a = content_key("fp", _finding(1))
    b = content_key("fp", _finding(1, snippet="otro"))

    assert a.startswith("fp:") and a != b


def test_sin_hallazgos_no_llama_a_gemini():
    modelo = _Modelo()

    resultado = triage_findings({}, modelo)

    assert resultado.status == "skipped" and modelo.prompts == []


def test_el_resultado_es_un_dataclass_inmutable():
    resultado = TriageResult(False, Severity.LOW, "e", "r")

    with pytest.raises(AttributeError):
        resultado.explanation = "otra"
