"""Nombre y foto de los usuarios, pedidos a la Backend API de Clerk.

La base no guarda datos personales de los usuarios, solo su id de Clerk. Para
mostrar quiénes son los miembros de una organización se piden a Clerk en el
momento. Si Clerk no responde o falta la clave, la lista se muestra igual, sin
nombres.
"""

import json
import os
import re
import urllib.request
from dataclasses import dataclass
from urllib.error import URLError
from urllib.parse import urlencode

DEFAULT_CLERK_API_URL = "https://api.clerk.com/v1"
TIMEOUT_SECONDS = 5
MAX_USERS = 100

_CLERK_USER_ID = re.compile(r"user_[A-Za-z0-9]{1,64}")


@dataclass(frozen=True)
class ClerkProfile:
    name: str | None
    image_url: str | None


def fetch_profiles(clerk_user_ids: list[str]) -> dict[str, ClerkProfile]:
    """Perfil público de cada usuario por su id de Clerk. Nunca lanza."""
    ids = [i for i in clerk_user_ids if _CLERK_USER_ID.fullmatch(i)][:MAX_USERS]
    secret_key = os.getenv("CLERK_SECRET_KEY")
    base_url = os.getenv("CLERK_API_URL", DEFAULT_CLERK_API_URL).rstrip("/")
    # La clave secreta solo viaja por HTTPS.
    if not ids or not secret_key or not base_url.startswith("https://"):
        return {}

    query = urlencode([("user_id", i) for i in ids] + [("limit", MAX_USERS)])
    request = urllib.request.Request(
        f"{base_url}/users?{query}",
        headers={
            "Authorization": f"Bearer {secret_key}",
            "Accept": "application/json",
            # Cloudflare, delante de la API de Clerk, bloquea el User-Agent de urllib.
            "User-Agent": "Qubitor",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            payload = json.load(response)
    except (URLError, TimeoutError, ValueError):
        return {}
    users = payload.get("data") if isinstance(payload, dict) else payload
    if not isinstance(users, list):
        return {}
    return {user["id"]: _profile(user) for user in users if isinstance(user, dict) and isinstance(user.get("id"), str)}


def _profile(user: dict) -> ClerkProfile:
    full_name = " ".join(part for part in (user.get("first_name"), user.get("last_name")) if part)
    name = full_name or user.get("username") or None
    image_url = user.get("image_url")
    return ClerkProfile(name=name, image_url=image_url if isinstance(image_url, str) else None)
