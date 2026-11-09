"""Cliente de Gemini con salida estructurada (Interactions API, SDK `google-genai`).

Es una capa fina sobre el SDK oficial: pide JSON que cumpla un esquema,
desactiva el guardado de la interacción (`store=False`, así Google no conserva
los fragmentos de código) y traduce los errores a tres casos que el triage
sabe manejar: cuota agotada, servicio no disponible y respuesta inválida.
"""

import json
import os
from typing import Any, Protocol

DEFAULT_MODEL = "gemini-3.5-flash-lite"
TIMEOUT_SECONDS = 30
TEMPERATURE = 0.2


class GeminiError(Exception):
    """Base de los errores de Gemini."""


class GeminiQuotaExceeded(GeminiError):
    """Gemini respondió 429: se agotó la cuota. No tiene sentido seguir pidiendo en este escaneo."""


class GeminiUnavailable(GeminiError):
    """Gemini no respondió, tardó demasiado o rechazó el pedido."""


class GeminiInvalidResponse(GeminiError):
    """La respuesta no es un JSON válido."""


class JsonModel(Protocol):
    """Lo que el triage necesita de un modelo: JSON que cumpla un esquema."""

    def generate_json(self, *, system: str, prompt: str, schema: dict) -> dict: ...


class GeminiClient:
    def __init__(self, api_key: str, model: str = DEFAULT_MODEL, timeout: float = TIMEOUT_SECONDS, sdk_client: Any = None):
        if sdk_client is None:
            # Se importa acá: sin GEMINI_API_KEY el worker no carga el SDK.
            from google import genai

            sdk_client = genai.Client(api_key=api_key)
        self._client = sdk_client
        self.model = model
        self.timeout = timeout

    def generate_json(self, *, system: str, prompt: str, schema: dict) -> dict:
        try:
            interaction = self._client.interactions.create(
                model=self.model,
                input=prompt,
                system_instruction=system,
                response_format={"type": "text", "mime_type": "application/json", "schema": schema},
                response_mime_type="application/json",
                generation_config={"temperature": TEMPERATURE},
                store=False,
                timeout=self.timeout,
            )
        except Exception as error:  # el SDK lanza errores de distintas jerarquías según la versión
            if _status_code(error) == 429:
                raise GeminiQuotaExceeded("Se agotó la cuota de Gemini") from None
            raise GeminiUnavailable(f"Gemini no respondió ({type(error).__name__})") from None

        text = getattr(interaction, "output_text", None)
        if not isinstance(text, str) or not text.strip():
            raise GeminiInvalidResponse("Gemini devolvió una respuesta vacía")
        try:
            payload = json.loads(text)
        except ValueError:
            raise GeminiInvalidResponse("Gemini devolvió algo que no es JSON") from None
        if not isinstance(payload, dict):
            raise GeminiInvalidResponse("Gemini devolvió un JSON que no es un objeto")
        return payload


def get_gemini_client() -> GeminiClient | None:
    """El cliente configurado por variables de entorno, o None si no hay GEMINI_API_KEY."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    return GeminiClient(api_key, model=os.getenv("GEMINI_MODEL") or DEFAULT_MODEL)


def _status_code(error: Exception) -> int | None:
    for attribute in ("status_code", "code"):
        value = getattr(error, attribute, None)
        if isinstance(value, int):
            return value
    return None
