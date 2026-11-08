"""Token OAuth de GitHub del usuario, que Clerk guarda al iniciar sesión con GitHub.

No es el JWT de sesión de Clerk: ese solo prueba quién es el usuario ante la
API de Qubitor. El token de GitHub lo pide el backend a la Backend API de Clerk
con la clave secreta y nunca se manda al frontend ni se guarda en la base.

Requiere credenciales propias de GitHub en Clerk (no las compartidas de
desarrollo, que no permiten leer el token) y los scopes `read:user` y
`public_repo`, o `repo` si se habilitan repos privados.
"""

import json
import os
import re
import urllib.request
from urllib.error import HTTPError, URLError
from urllib.parse import quote

from app.integrations.github.errors import GitHubNotLinked, GitHubUnavailable

DEFAULT_CLERK_API_URL = "https://api.clerk.com/v1"
# Clerk nombra al proveedor `oauth_github` en su API histórica y `github` en la actual.
DEFAULT_PROVIDERS = ("oauth_github", "github")
TIMEOUT_SECONDS = 10

_CLERK_USER_ID = re.compile(r"user_[A-Za-z0-9]{1,64}")


def get_github_token(clerk_user_id: str) -> str:
    """Token OAuth de GitHub del usuario de Clerk. Lanza GitHubNotLinked si no tiene."""
    if not _CLERK_USER_ID.fullmatch(clerk_user_id or ""):
        raise GitHubNotLinked("La cuenta no está vinculada con GitHub")
    secret_key = os.getenv("CLERK_SECRET_KEY")
    if not secret_key:
        raise GitHubUnavailable("La integración con GitHub no está configurada (falta CLERK_SECRET_KEY)")

    base_url = os.getenv("CLERK_API_URL", DEFAULT_CLERK_API_URL).rstrip("/")
    for provider in _providers():
        url = f"{base_url}/users/{quote(clerk_user_id)}/oauth_access_tokens/{quote(provider)}"
        tokens = _request(url, secret_key)
        if tokens is None:
            continue  # Clerk no reconoce este nombre de proveedor: se prueba el otro.
        for entry in tokens:
            token = entry.get("token") if isinstance(entry, dict) else None
            if isinstance(token, str) and token:
                return token
        break
    raise GitHubNotLinked("Conectá tu cuenta de GitHub para ver tus repositorios")


def _providers() -> tuple[str, ...]:
    configured = os.getenv("CLERK_GITHUB_PROVIDER")
    return (configured,) if configured else DEFAULT_PROVIDERS


def _request(url: str, secret_key: str) -> list | None:
    """Lista de tokens que devuelve Clerk, o None si el proveedor no existe."""
    request = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {secret_key}", "Accept": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            payload = json.load(response)
    except HTTPError as error:
        if error.code in (400, 404, 422):
            return None
        if error.code in (401, 403):
            raise GitHubUnavailable("Clerk rechazó la clave secreta del backend") from None
        raise GitHubUnavailable(f"Clerk respondió con un error ({error.code})") from None
    except (URLError, TimeoutError, ValueError):
        raise GitHubUnavailable("No se pudo consultar Clerk") from None
    # La API devuelve una lista; algunas versiones la envuelven en {"data": [...]}.
    if isinstance(payload, dict):
        payload = payload.get("data")
    return payload if isinstance(payload, list) else []
