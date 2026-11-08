"""Token OAuth de GitHub desde la Backend API de Clerk (Módulo E)."""

import io
import json
from urllib.error import HTTPError, URLError

import pytest

from app.integrations.github import clerk
from app.integrations.github.clerk import get_github_token
from app.integrations.github.errors import GitHubNotLinked, GitHubUnavailable


class _Respuesta(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def _http_error(url, code):
    return HTTPError(url, code, "error", {}, io.BytesIO(b"{}"))


@pytest.fixture
def clerk_falso(monkeypatch):
    """Reemplaza urlopen: cada proveedor responde lo que diga `respuestas`."""
    monkeypatch.setenv("CLERK_SECRET_KEY", "sk_test_clave")
    monkeypatch.delenv("CLERK_GITHUB_PROVIDER", raising=False)
    pedidos = []
    respuestas = {}

    def urlopen(request, timeout):
        pedidos.append(request)
        provider = request.full_url.rsplit("/", 1)[-1]
        respuesta = respuestas.get(provider, 404)
        if isinstance(respuesta, Exception):
            raise respuesta
        if isinstance(respuesta, int):
            raise _http_error(request.full_url, respuesta)
        return _Respuesta(json.dumps(respuesta).encode())

    monkeypatch.setattr(clerk.urllib.request, "urlopen", urlopen)
    return pedidos, respuestas


def test_devuelve_el_token_del_proveedor_github(clerk_falso):
    pedidos, respuestas = clerk_falso
    respuestas["oauth_github"] = [{"object": "oauth_access_token", "token": "gho_abc", "scopes": ["repo"]}]

    assert get_github_token("user_123") == "gho_abc"
    assert pedidos[0].full_url == "https://api.clerk.com/v1/users/user_123/oauth_access_tokens/oauth_github"
    assert pedidos[0].get_header("Authorization") == "Bearer sk_test_clave"


def test_si_clerk_no_reconoce_oauth_github_prueba_github(clerk_falso):
    pedidos, respuestas = clerk_falso
    respuestas["oauth_github"] = 422
    respuestas["github"] = {"data": [{"token": "gho_nuevo"}]}

    assert get_github_token("user_123") == "gho_nuevo"
    assert [p.full_url.rsplit("/", 1)[-1] for p in pedidos] == ["oauth_github", "github"]


def test_usuario_sin_github_conectado(clerk_falso):
    _, respuestas = clerk_falso
    respuestas["oauth_github"] = []

    with pytest.raises(GitHubNotLinked):
        get_github_token("user_123")


def test_proveedor_configurado_por_variable(clerk_falso, monkeypatch):
    pedidos, respuestas = clerk_falso
    monkeypatch.setenv("CLERK_GITHUB_PROVIDER", "github")
    respuestas["github"] = [{"token": "gho_x"}]

    assert get_github_token("user_1") == "gho_x"
    assert len(pedidos) == 1


@pytest.mark.parametrize("user_id", ["", "../admin", "user_1/../../x", "org_123"])
def test_rechaza_ids_de_usuario_raros_sin_llamar_a_clerk(clerk_falso, user_id):
    pedidos, _ = clerk_falso

    with pytest.raises(GitHubNotLinked):
        get_github_token(user_id)
    assert pedidos == []


def test_sin_clave_secreta_la_integracion_no_esta_disponible(clerk_falso, monkeypatch):
    monkeypatch.delenv("CLERK_SECRET_KEY")

    with pytest.raises(GitHubUnavailable):
        get_github_token("user_1")


def test_clave_secreta_rechazada(clerk_falso):
    _, respuestas = clerk_falso
    respuestas["oauth_github"] = 401

    with pytest.raises(GitHubUnavailable) as error:
        get_github_token("user_1")
    assert "sk_test_clave" not in str(error.value)


def test_clerk_caido(clerk_falso):
    _, respuestas = clerk_falso
    respuestas["oauth_github"] = URLError("timeout")

    with pytest.raises(GitHubUnavailable):
        get_github_token("user_1")
