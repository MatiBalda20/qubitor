"""Cliente mínimo de la API REST de GitHub con el token OAuth del usuario.

Se usa `urllib` de la librería estándar, como el cliente de OSV, para no sumar
dependencias. Solo se leen los campos que necesita Qubitor de cada repo.
"""

import json
import re
import time
import urllib.request
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode

from app.integrations.github.errors import (
    GitHubError,
    GitHubForbidden,
    GitHubNotFound,
    GitHubNotLinked,
    GitHubRateLimited,
    GitHubUnavailable,
)
from app.worker.clone import is_github_url

GITHUB_API = "https://api.github.com"
API_VERSION = "2022-11-28"
TIMEOUT_SECONDS = 10
MAX_PER_PAGE = 100

_FULL_NAME = re.compile(r"(?!\.)[A-Za-z0-9_.-]{1,100}/(?!\.)[A-Za-z0-9_.-]{1,100}")
_NEXT_LINK = re.compile(r'<[^>]+>;\s*rel="next"')


@dataclass(frozen=True)
class GitHubRepo:
    full_name: str
    url: str  # https://github.com/<owner>/<repo>, lo que clona el worker
    private: bool
    description: str | None
    default_branch: str
    size_bytes: int
    updated_at: str | None
    archived: bool
    can_read: bool


@dataclass(frozen=True)
class RepoPage:
    items: list[GitHubRepo]
    page: int
    has_next: bool


def is_valid_full_name(full_name: str) -> bool:
    return bool(_FULL_NAME.fullmatch(full_name or "")) and ".." not in full_name


class GitHubClient:
    def __init__(self, token: str, timeout: float = TIMEOUT_SECONDS):
        self._token = token
        self.timeout = timeout

    def list_repositories(self, page: int = 1, per_page: int = 30) -> RepoPage:
        """Repos que el usuario puede leer: propios, de colaborador y de sus organizaciones."""
        page = max(1, page)
        per_page = min(max(1, per_page), MAX_PER_PAGE)
        query = urlencode({
            "per_page": per_page,
            "page": page,
            "sort": "updated",
            "affiliation": "owner,collaborator,organization_member",
        })
        payload, headers = self._get(f"/user/repos?{query}")
        if not isinstance(payload, list):
            raise GitHubUnavailable("GitHub devolvió una respuesta inesperada")
        items = [repo for repo in (_parse_repo(item) for item in payload) if repo is not None]
        return RepoPage(items=items, page=page, has_next=bool(_NEXT_LINK.search(headers.get("Link", ""))))

    def get_repository(self, full_name: str) -> GitHubRepo:
        if not is_valid_full_name(full_name):
            raise GitHubNotFound("El nombre del repositorio no es válido")
        owner, name = full_name.split("/")
        payload, _ = self._get(f"/repos/{quote(owner)}/{quote(name)}")
        repo = _parse_repo(payload)
        if repo is None:
            raise GitHubUnavailable("GitHub devolvió una respuesta inesperada")
        return repo

    def _get(self, path: str) -> tuple[object, dict]:
        request = urllib.request.Request(
            f"{GITHUB_API}{path}",
            headers={
                "Authorization": f"Bearer {self._token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": API_VERSION,
                "User-Agent": "Qubitor",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.load(response), dict(response.headers)
        except HTTPError as error:
            raise _translate(error) from None
        except (URLError, TimeoutError, ValueError):
            raise GitHubUnavailable("No se pudo consultar GitHub") from None


def _translate(error: HTTPError) -> GitHubError:
    headers = error.headers or {}
    if error.code == 401:
        return GitHubNotLinked("Tu sesión de GitHub venció: volvé a iniciar sesión con GitHub")
    if error.code == 429 or (error.code == 403 and headers.get("x-ratelimit-remaining") == "0"):
        return GitHubRateLimited("Se agotó la cuota de la API de GitHub, probá en unos minutos", _retry_after(headers))
    if error.code == 403:
        return GitHubForbidden("GitHub no permite acceder a ese repositorio con tu cuenta")
    if error.code == 404:
        return GitHubNotFound("El repositorio no existe o tu cuenta no tiene acceso")
    return GitHubUnavailable(f"GitHub respondió con un error ({error.code})")


def _retry_after(headers) -> int | None:
    try:
        if headers.get("retry-after"):
            return max(0, int(headers["retry-after"]))
        if headers.get("x-ratelimit-reset"):
            return max(0, int(headers["x-ratelimit-reset"]) - int(time.time()))
    except (TypeError, ValueError):
        return None
    return None


def _parse_repo(item: object) -> GitHubRepo | None:
    """Toma solo los campos que se usan y descarta lo que no sea un repo de github.com."""
    if not isinstance(item, dict):
        return None
    full_name = item.get("full_name")
    if not isinstance(full_name, str) or not is_valid_full_name(full_name):
        return None
    url = f"https://github.com/{full_name}"
    if not is_github_url(url):
        return None
    permissions = item.get("permissions") if isinstance(item.get("permissions"), dict) else {}
    description = item.get("description")
    return GitHubRepo(
        full_name=full_name,
        url=url,
        private=bool(item.get("private")),
        description=description[:300] if isinstance(description, str) else None,
        default_branch=str(item.get("default_branch") or "main"),
        # GitHub informa el tamaño en KB (aproximado: lo exacto lo mide el clonado).
        size_bytes=int(item.get("size") or 0) * 1024,
        updated_at=item.get("updated_at") if isinstance(item.get("updated_at"), str) else None,
        archived=bool(item.get("archived")),
        can_read=bool(permissions.get("pull", True)),
    )
