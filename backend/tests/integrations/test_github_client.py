"""Cliente de la API de GitHub (Módulo E), con GitHub simulado."""

import io
import json
from email.message import Message
from urllib.error import HTTPError, URLError

import pytest

from app.integrations.github import client as client_module
from app.integrations.github.client import GitHubClient, is_valid_full_name
from app.integrations.github.errors import (
    GitHubForbidden,
    GitHubNotFound,
    GitHubNotLinked,
    GitHubRateLimited,
    GitHubUnavailable,
)


def _repo(full_name="org/demo", **cambios):
    repo = {
        "full_name": full_name,
        "private": False,
        "description": "Repo de demo",
        "default_branch": "main",
        "size": 120,
        "updated_at": "2026-11-08T10:00:00Z",
        "archived": False,
        "permissions": {"pull": True, "push": False},
        "html_url": f"https://github.com/{full_name}",
    }
    repo.update(cambios)
    return repo


class _Respuesta(io.BytesIO):
    def __init__(self, body, headers=None):
        super().__init__(json.dumps(body).encode())
        self.headers = Message()
        for key, value in (headers or {}).items():
            self.headers[key] = value

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def _http_error(code, headers=None):
    message = Message()
    for key, value in (headers or {}).items():
        message[key] = value
    return HTTPError("https://api.github.com/x", code, "error", message, io.BytesIO(b"{}"))


@pytest.fixture
def github(monkeypatch):
    pedidos = []
    cola = []

    def urlopen(request, timeout):
        pedidos.append(request)
        respuesta = cola.pop(0)
        if isinstance(respuesta, Exception):
            raise respuesta
        return respuesta

    monkeypatch.setattr(client_module.urllib.request, "urlopen", urlopen)
    return pedidos, cola


def test_lista_los_repos_del_usuario_con_el_token(github):
    pedidos, cola = github
    cola.append(_Respuesta([_repo("org/a"), _repo("org/b", private=True)]))

    pagina = GitHubClient("gho_token").list_repositories(page=1, per_page=30)

    assert [r.full_name for r in pagina.items] == ["org/a", "org/b"]
    assert pagina.items[1].private is True
    assert pagina.items[0].url == "https://github.com/org/a"
    assert pagina.items[0].size_bytes == 120 * 1024
    assert pagina.has_next is False
    pedido = pedidos[0]
    assert pedido.get_header("Authorization") == "Bearer gho_token"
    assert "page=1" in pedido.full_url and "per_page=30" in pedido.full_url
    assert "affiliation=owner%2Ccollaborator%2Corganization_member" in pedido.full_url


def test_paginacion_por_cabecera_link(github):
    _, cola = github
    link = '<https://api.github.com/user/repos?page=3>; rel="next", <https://api.github.com/user/repos?page=9>; rel="last"'
    cola.append(_Respuesta([_repo()], {"Link": link}))

    pagina = GitHubClient("t").list_repositories(page=2)

    assert pagina.page == 2
    assert pagina.has_next is True


def test_limita_el_tamano_de_pagina(github):
    pedidos, cola = github
    cola.append(_Respuesta([]))

    GitHubClient("t").list_repositories(page=0, per_page=1000)

    assert "per_page=100" in pedidos[0].full_url and "page=1" in pedidos[0].full_url


def test_descarta_entradas_raras(github):
    _, cola = github
    cola.append(_Respuesta([_repo("org/ok"), {"full_name": "../../etc"}, "texto", _repo("sin-barra")]))

    pagina = GitHubClient("t").list_repositories()

    assert [r.full_name for r in pagina.items] == ["org/ok"]


def test_detalle_de_un_repo(github):
    pedidos, cola = github
    cola.append(_Respuesta(_repo("org/demo", private=True, permissions={"pull": True})))

    repo = GitHubClient("t").get_repository("org/demo")

    assert repo.private and repo.can_read
    assert pedidos[0].full_url == "https://api.github.com/repos/org/demo"


@pytest.mark.parametrize("nombre", ["org", "org/demo/extra", "../x", "org/..", ".git/x", ""])
def test_nombres_invalidos_no_llaman_a_github(github, nombre):
    pedidos, _ = github

    assert not is_valid_full_name(nombre)
    with pytest.raises(GitHubNotFound):
        GitHubClient("t").get_repository(nombre)
    assert pedidos == []


@pytest.mark.parametrize(
    ("error", "esperado"),
    [
        (_http_error(401), GitHubNotLinked),
        (_http_error(403), GitHubForbidden),
        (_http_error(404), GitHubNotFound),
        (_http_error(500), GitHubUnavailable),
        (URLError("sin red"), GitHubUnavailable),
    ],
)
def test_traduce_los_errores_de_github(github, error, esperado):
    _, cola = github
    cola.append(error)

    with pytest.raises(esperado):
        GitHubClient("t").list_repositories()


def test_cuota_agotada_informa_cuando_reintentar(github):
    _, cola = github
    cola.append(_http_error(403, {"x-ratelimit-remaining": "0", "retry-after": "60"}))

    with pytest.raises(GitHubRateLimited) as error:
        GitHubClient("t").list_repositories()
    assert error.value.retry_after == 60


def test_el_token_no_aparece_en_los_mensajes_de_error(github):
    _, cola = github
    cola.append(_http_error(500))

    with pytest.raises(GitHubUnavailable) as error:
        GitHubClient("gho_secreto").list_repositories()
    assert "gho_secreto" not in str(error.value)
