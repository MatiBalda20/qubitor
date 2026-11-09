"""Enmascarado de lo que se envía a Gemini (Módulo E)."""

import pytest

from app.ai.masking import safe_snippet, safe_text, mask_secrets


@pytest.mark.parametrize(
    "secreto",
    [
        "AKIAABCDEFGHIJKLMNOP",
        "ghp_" + "a1B2" * 9,
        "AIza" + "x" * 35,
        "xoxb-1234567890-abcdefghij",
        "sk_live_" + "Ab3" * 6,
        "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.c2lnbmF0dXJhLXByb2JhYmxl",
    ],
)
def test_enmascara_secretos_conocidos(secreto):
    texto = f"token = '{secreto}'"

    assert secreto not in mask_secrets(texto)
    assert "***" in mask_secrets(texto)


def test_enmascara_credenciales_en_urls():
    texto = "DATABASE_URL = 'postgresql://admin:SuperClave123@db.example.com:5432/app'"

    resultado = mask_secrets(texto)

    assert "SuperClave123" not in resultado
    assert "postgresql://***@db.example.com" in resultado


def test_enmascara_tiras_de_alta_entropia():
    clave = "Xk9fP2qLmR7vT4wZ8nB3cH6jD1sA5gE0"

    assert clave not in mask_secrets(f"api_key = {clave}")


def test_no_toca_codigo_comun():
    codigo = "def calcular_total_de_la_factura(items):\n    return sum(i.precio for i in items)"

    assert mask_secrets(codigo) == codigo


def test_enmascara_claves_privadas_completas():
    texto = "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA\nabc\n-----END RSA PRIVATE KEY-----"

    assert "MIIEowIBAAKCAQEA" not in mask_secrets(texto)


def test_el_snippet_se_recorta_a_5_lineas():
    snippet = "\n".join(f"linea {i}" for i in range(20))

    assert safe_snippet(snippet).splitlines() == [f"linea {i}" for i in range(5)]


def test_el_snippet_no_supera_600_caracteres():
    assert len(safe_snippet("x" * 5000)) <= 600


def test_textos_vacios():
    assert safe_snippet("") == ""
    assert safe_text(None) == ""
