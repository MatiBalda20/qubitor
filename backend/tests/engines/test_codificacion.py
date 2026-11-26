"""Archivos que no son UTF-8 (F-06 / QUB-01).

Un solo carácter latin-1 hacía que los motores descartaran el archivo entero en
silencio: con código heredado en español, un escaneo "limpio" no era confiable.
"""

from app.engines.config.engine import ConfigEngine
from app.engines.crypto import CryptoEngine
from app.engines.crypto.files import decode_source
from app.engines.secrets.engine import SecretsEngine

# Comentario con "ñ" y "é" en latin-1: no es UTF-8 válido.
_LATIN1_PY = (
    "# configuración del módulo de contraseñas\n"
    "import hashlib\n"
    "AWS_KEY = 'AKIAIOSFODNN7EXAMPLE'\n"
    "clave = hashlib.md5(b'x').hexdigest()\n"
).encode("latin-1")


def test_un_archivo_latin1_no_se_descarta_en_secretos_ni_criptografia(tmp_path):
    (tmp_path / "config.py").write_bytes(_LATIN1_PY)

    secretos = SecretsEngine().scan(str(tmp_path))
    cripto = CryptoEngine().scan(str(tmp_path))

    assert "secrets.aws" in {h.rule_id for h in secretos}
    assert "crypto.classic.weak-hash" in {h.rule_id for h in cripto}


def test_un_dockerfile_latin1_se_analiza(tmp_path):
    (tmp_path / "Dockerfile").write_bytes("# imagen de producción\nFROM python:3.11\nUSER root\n".encode("latin-1"))

    hallazgos = ConfigEngine().scan(str(tmp_path))

    assert hallazgos, "el Dockerfile en latin-1 se descartó"


def test_los_binarios_se_siguen_salteando():
    assert decode_source(b"\x89PNG\r\n\x1a\n\x00\x00AKIAIOSFODNN7EXAMPLE") is None


def test_utf8_se_decodifica_igual_que_antes():
    assert decode_source("contraseña = 1\n".encode("utf-8")) == "contraseña = 1\n"
