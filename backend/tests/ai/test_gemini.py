"""Cliente de Gemini con el SDK simulado (Módulo E)."""

import json

import pytest

from app.ai import gemini as gemini_module
from app.ai.gemini import (
    GeminiClient,
    GeminiInvalidResponse,
    GeminiQuotaExceeded,
    GeminiUnavailable,
    get_gemini_client,
)


class _Interaccion:
    def __init__(self, output_text):
        self.output_text = output_text


class _ErrorHttp(Exception):
    def __init__(self, status_code):
        super().__init__(f"HTTP {status_code}")
        self.status_code = status_code


class _Interactions:
    def __init__(self, respuesta):
        self.respuesta = respuesta
        self.pedidos = []

    def create(self, **kwargs):
        self.pedidos.append(kwargs)
        if isinstance(self.respuesta, Exception):
            raise self.respuesta
        return self.respuesta


class _Sdk:
    def __init__(self, respuesta):
        self.interactions = _Interactions(respuesta)


def _cliente(respuesta):
    sdk = _Sdk(respuesta)
    return GeminiClient("clave", model="gemini-de-prueba", sdk_client=sdk), sdk


SCHEMA = {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]}


def test_pide_json_con_esquema_y_sin_guardar_la_interaccion():
    cliente, sdk = _cliente(_Interaccion(json.dumps({"ok": True})))

    assert cliente.generate_json(system="sistema", prompt="datos", schema=SCHEMA) == {"ok": True}

    pedido = sdk.interactions.pedidos[0]
    assert pedido["model"] == "gemini-de-prueba"
    assert pedido["input"] == "datos"
    assert pedido["system_instruction"] == "sistema"
    assert pedido["response_format"] == {"type": "text", "mime_type": "application/json", "schema": SCHEMA}
    assert pedido["store"] is False
    assert pedido["timeout"] == cliente.timeout


def test_cuota_agotada():
    cliente, _ = _cliente(_ErrorHttp(429))

    with pytest.raises(GeminiQuotaExceeded):
        cliente.generate_json(system="s", prompt="p", schema=SCHEMA)


@pytest.mark.parametrize("error", [_ErrorHttp(500), _ErrorHttp(400), TimeoutError(), ConnectionError()])
def test_errores_del_servicio(error):
    cliente, _ = _cliente(error)

    with pytest.raises(GeminiUnavailable):
        cliente.generate_json(system="s", prompt="p", schema=SCHEMA)


@pytest.mark.parametrize("texto", [None, "", "esto no es json", "[1, 2, 3]", '"texto"'])
def test_respuestas_invalidas(texto):
    cliente, _ = _cliente(_Interaccion(texto))

    with pytest.raises(GeminiInvalidResponse):
        cliente.generate_json(system="s", prompt="p", schema=SCHEMA)


def test_sin_api_key_no_hay_cliente(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    assert get_gemini_client() is None


def test_el_modelo_se_configura_por_variable(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "clave-de-prueba")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.8-flash")

    cliente = get_gemini_client()

    assert cliente.model == "gemini-3.8-flash"


def test_modelo_por_defecto(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "clave-de-prueba")
    monkeypatch.delenv("GEMINI_MODEL", raising=False)

    assert get_gemini_client().model == gemini_module.DEFAULT_MODEL
