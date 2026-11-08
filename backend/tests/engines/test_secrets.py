import time

import pytest
from app.engines.base import Severity
from app.engines.secrets.engine import SecretsEngine

def _escribir(repo, ruta, contenido):
    archivo = repo / ruta
    archivo.parent.mkdir(parents=True, exist_ok=True)
    archivo.write_text(contenido, encoding="utf-8")

def test_detecta_token_aws_y_enmascara_valor(tmp_path):
    _escribir(tmp_path, "config.py", "AWS_KEY = 'AKIA1234567890ABCDEF'")
    hallazgos = SecretsEngine().scan(str(tmp_path))
    assert len(hallazgos) == 1
    assert "AKIA1234567890ABCDEF" not in hallazgos[0].snippet
    assert "***" in hallazgos[0].snippet

def test_detecta_secreto_por_entropia(tmp_path):
    # Usando el string sugerido de 32 caracteres para asegurar entropía > 4.5
    _escribir(tmp_path, "settings.py", "password = 'qL7xV2mR9tK4wZ8pN3sF6hJ1cB5dG0yE'")
    hallazgos = SecretsEngine().scan(str(tmp_path))
    assert len(hallazgos) == 1
    assert hallazgos[0].rule_id == "secrets.generic.entropy"

def test_ignora_baja_entropia(tmp_path):
    _escribir(tmp_path, "baja_entropia.py", "password = 'aaaaaaaaaaaaaaaaaaaaaaaaa'")
    hallazgos = SecretsEngine().scan(str(tmp_path))
    assert len(hallazgos) == 0

def test_enmascara_multiples_secretos_en_una_linea(tmp_path):
    _escribir(tmp_path, "multi.py", "AWS_KEY = 'AKIA1234567890ABCDEF'; OTHER = 'AKIA0987654321UVWXYZ'")
    hallazgos = SecretsEngine().scan(str(tmp_path))
    assert len(hallazgos) == 2
    # El snippet de ambos debe tener los dos secretos censurados
    assert "AKIA" not in hallazgos[0].snippet
    assert hallazgos[0].snippet.count("***") == 2

def test_no_duplica_hallazgos_por_token_conocido(tmp_path):
    _escribir(tmp_path, "github.py", "GITHUB_TOKEN = 'ghp_123456789012345678901234567890123456'")
    hallazgos = SecretsEngine().scan(str(tmp_path))
    assert len(hallazgos) == 1
    assert hallazgos[0].rule_id == "secrets.github"

def test_detecta_secretos_genericos_sin_comillas_y_en_diccionarios(tmp_path):
    _escribir(tmp_path, ".env", "secret_value=qL7xV2mR9tK4wZ8pN3sF6hJ1cB5dG0yE")
    _escribir(tmp_path, "config.json", "{'api_token': 'qL7xV2mR9tK4wZ8pN3sF6hJ1cB5dG0yE'}")
    hallazgos = SecretsEngine().scan(str(tmp_path))
    assert len(hallazgos) == 2

def test_linea_larga_no_cuelga_el_motor(tmp_path):
    _escribir(tmp_path, "blob.txt", "a" * 20000)
    inicio = time.monotonic()
    hallazgos = SecretsEngine().scan(str(tmp_path))
    assert time.monotonic() - inicio < 1
    assert len(hallazgos) == 0

@pytest.mark.parametrize("linea", [
    "TOKEN_URL=https://auth.Example.com/oauth2/V1/Token?client=ABC123xyz&scope=Read_Write&aud=Zq9",
    "secret_key=Settings.getSecretValue(Vault.Client(URL_X),Path.join(BASE,'a'))",
    "const tokenMap:Record<string,AuthTokenResponse|RefreshPayload|Null_Value>=new Map();",
    "--key: data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk",
])
def test_no_reporta_urls_ni_codigo_como_secreto(tmp_path, linea):
    _escribir(tmp_path, "config.txt", linea)
    hallazgos = SecretsEngine().scan(str(tmp_path))
    assert len(hallazgos) == 0

@pytest.mark.parametrize("separador", ["}", "]"])
def test_enmascara_entero_un_secreto_con_llaves_o_corchetes(tmp_path, separador):
    _escribir(tmp_path, "settings.py", f"password = 'aB3dE6gH9jK2mN5pQ8sT1vW4yZ7cF0{separador}SECRETORESTANTE'")
    hallazgos = SecretsEngine().scan(str(tmp_path))
    assert len(hallazgos) == 1
    assert "SECRETORESTANTE" not in hallazgos[0].snippet
