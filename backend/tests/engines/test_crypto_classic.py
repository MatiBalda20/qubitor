import pytest
from app.engines.base import Severity
from app.engines.crypto.classic import scan_classic
from app.engines.crypto import CryptoEngine

def _escribir(repo, ruta, contenido):
    archivo = repo / ruta
    archivo.parent.mkdir(parents=True, exist_ok=True)
    archivo.write_text(contenido, encoding="utf-8")

def test_python_detecta_rsa_posicional(tmp_path):
    codigo = """
from cryptography.hazmat.primitives.asymmetric import rsa
# Exponente 65537 pos 0, size 1024 pos 1
key = rsa.generate_private_key(65537, 1024)
"""
    _escribir(tmp_path, "app.py", codigo)
    hallazgos = scan_classic(str(tmp_path))
    assert len(hallazgos) == 1
    assert hallazgos[0].rule_id == "crypto.classic.rsa-weak-key"
    assert hallazgos[0].severity == Severity.HIGH

def test_python_detecta_aes_modes_ecb(tmp_path):
    codigo = """
from Crypto.Cipher import AES
from Crypto.Cipher import modes
cipher = AES.new(b'clave', modes.ECB())
"""
    _escribir(tmp_path, "utils.py", codigo)
    hallazgos = scan_classic(str(tmp_path))
    assert "crypto.classic.aes-ecb" in [h.rule_id for h in hallazgos]

def test_deduplicacion_rsa_cryptoengine(tmp_path):
    codigo = """
from cryptography.hazmat.primitives.asymmetric import rsa
key = rsa.generate_private_key(65537, 1024)
"""
    _escribir(tmp_path, "dedup.py", codigo)
    # CryptoEngine junta classic y pqc
    hallazgos = CryptoEngine().scan(str(tmp_path))
    
    reglas = [h.rule_id for h in hallazgos]
    # Debería quedarse con la versión HIGH de classic y descartar la MEDIUM de pqc
    assert "crypto.classic.rsa-weak-key" in reglas
    assert "crypto.pqc.rsa-keygen" not in reglas

def test_recursion_error_evitado(tmp_path):
    # Genera un AST excesivamente anidado que tira RecursionError
    codigo = "x = " + " + ".join(["1"] * 2500)
    _escribir(tmp_path, "roto.py", codigo)
    hallazgos = scan_classic(str(tmp_path))
    assert len(hallazgos) == 0

def test_casos_negativos_no_disparan_falsos_positivos(tmp_path):
    codigo = """
from cryptography.hazmat.primitives.asymmetric import rsa
from Crypto.Cipher import AES
key = rsa.generate_private_key(65537, 3072) # RSA seguro
cipher = AES.new(b'clave', AES.MODE_GCM) # AES seguro
"""
    _escribir(tmp_path, "seguro.py", codigo)
    hallazgos = scan_classic(str(tmp_path))
    assert len(hallazgos) == 0