"""Enmascarado defensivo de lo que se manda a Gemini.

Los motores ya enmascaran los secretos del snippet (contrato de `base.py`), pero
el texto que sale de Qubitor hacia un servicio externo se vuelve a revisar acá:
si un motor nuevo se olvida, el secreto igual no sale. También se recorta el
fragmento a las 5 líneas del contrato: nunca se envían archivos completos.
"""

import math
import re

MAX_SNIPPET_LINES = 5
MAX_SNIPPET_CHARS = 600
MAX_FIELD_CHARS = 500
MASK = "***"

_KNOWN_SECRETS = re.compile(
    r"AKIA[0-9A-Z]{16}"
    r"|gh[pousr]_[A-Za-z0-9]{36,}"
    r"|github_pat_[A-Za-z0-9_]{20,}"
    r"|AIza[0-9A-Za-z_\-]{35}"
    r"|xox[baprs]-[0-9A-Za-z\-]{10,}"
    r"|sk_(?:live|test)_[0-9A-Za-z]{10,}"
    r"|eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{5,}"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?(?:-----END [A-Z ]*PRIVATE KEY-----|$)"
)
# Credenciales dentro de una URL: esquema://usuario:contraseña@host
_URL_CREDENTIALS = re.compile(r"(?P<scheme>[a-z][a-z0-9+.\-]*://)[^\s:/@]+:[^\s@/]+@", re.IGNORECASE)
# Tiras largas sin espacios que pueden ser un secreto aunque no tengan un formato conocido.
_CANDIDATE = re.compile(r"[A-Za-z0-9+/=_\-]{24,}")


def mask_secrets(text: str) -> str:
    if not text:
        return ""
    text = _KNOWN_SECRETS.sub(MASK, text)
    text = _URL_CREDENTIALS.sub(lambda m: f"{m['scheme']}{MASK}@", text)
    return _CANDIDATE.sub(lambda m: MASK if _looks_random(m.group(0)) else m.group(0), text)


def safe_snippet(snippet: str) -> str:
    """Máximo 5 líneas y 600 caracteres, con los secretos enmascarados."""
    lines = (snippet or "").splitlines()[:MAX_SNIPPET_LINES]
    return mask_secrets("\n".join(lines))[:MAX_SNIPPET_CHARS]


def safe_text(text: str | None, limit: int = MAX_FIELD_CHARS) -> str:
    return mask_secrets(text or "")[:limit]


def _looks_random(value: str) -> bool:
    """Alta entropía y mezcla de clases de caracteres: probablemente un token o una clave."""
    if len(set(value)) < 10:
        return False
    classes = sum(bool(re.search(pattern, value)) for pattern in (r"[a-z]", r"[A-Z]", r"\d"))
    return classes >= 2 and _entropy(value) > 4.0


def _entropy(value: str) -> float:
    return -sum((value.count(c) / len(value)) * math.log2(value.count(c) / len(value)) for c in set(value))
