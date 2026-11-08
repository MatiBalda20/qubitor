import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, rsa
from cryptography.x509.oid import NameOID

from app.engines.crypto.certs import scan_certs
from app.engines.crypto.pqc import scan_pqc

AHORA = datetime(2026, 11, 8, tzinfo=timezone.utc)
FIXTURES = Path(__file__).parent / "fixtures"


def _clave_rsa(bits=2048):
    return rsa.generate_private_key(public_exponent=65537, key_size=bits)


def _certificado(clave=None, hash_firma=hashes.SHA256(), vence=AHORA + timedelta(days=365), cn="demo.qubitor.invalid"):
    clave = clave or _clave_rsa()
    nombre = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])
    certificado = (
        x509.CertificateBuilder()
        .subject_name(nombre).issuer_name(nombre)
        .public_key(clave.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(vence - timedelta(days=400))
        .not_valid_after(vence)
        .sign(clave, hash_firma)
    )
    return certificado.public_bytes(serialization.Encoding.PEM)


def _pem_privada(clave, cifrada=False):
    cifrado = serialization.BestAvailableEncryption(b"clave-falsa") if cifrada else serialization.NoEncryption()
    return clave.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, cifrado)


def _escanear(tmp_path, archivos):
    for nombre, contenido in archivos.items():
        ruta = tmp_path / nombre
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_bytes(contenido)
    return scan_certs(str(tmp_path), now=AHORA)


def _reglas(hallazgos):
    return sorted(h.rule_id for h in hallazgos)


def test_certificado_rsa_2048_con_sha256_solo_es_vulnerable_a_shor(tmp_path):
    hallazgos = _escanear(tmp_path, {"certs/server.pem": _certificado()})

    assert _reglas(hallazgos) == ["crypto.pqc.cert-quantum-vulnerable"]
    hallazgo = hallazgos[0]
    assert hallazgo.severity.value == "medium"
    assert (hallazgo.file_path, hallazgo.line) == ("certs/server.pem", 1)
    assert hallazgo.metadata["algorithm"] == "RSA"
    assert hallazgo.metadata["key_size"] == 2048
    assert hallazgo.metadata["subject"] == "CN=demo.qubitor.invalid"
    assert hallazgo.metadata["signature_hash"] == "sha256"


def test_certificado_del_repo_de_demo_rsa_1024_con_sha1(tmp_path):
    # `cryptography` ya no firma con SHA-1: el certificado se generó una vez con
    # `openssl req -x509 -newkey rsa:1024 -sha1` y tiene datos falsos.
    pem = (FIXTURES / "rsa1024-sha1.pem").read_bytes()

    hallazgos = _escanear(tmp_path, {"certs/server.pem": pem})

    # La clave débil reemplaza al hallazgo de Shor, como hace CryptoEngine con el código.
    assert _reglas(hallazgos) == ["crypto.pqc.cert-weak-key", "crypto.pqc.cert-weak-signature"]
    assert {h.severity.value for h in hallazgos} == {"high"}
    assert "1024" in next(h for h in hallazgos if h.rule_id.endswith("weak-key")).title


def test_certificado_de_curva_eliptica(tmp_path):
    hallazgos = _escanear(tmp_path, {"ec.crt": _certificado(ec.generate_private_key(ec.SECP256R1()))})

    assert _reglas(hallazgos) == ["crypto.pqc.cert-quantum-vulnerable"]
    assert hallazgos[0].metadata["algorithm"] == "EC secp256r1"


def test_certificado_vencido_y_por_vencer(tmp_path):
    hallazgos = _escanear(tmp_path, {
        "vencido.pem": _certificado(vence=AHORA - timedelta(days=1)),
        "por-vencer.pem": _certificado(vence=AHORA + timedelta(days=10)),
        "vigente.pem": _certificado(vence=AHORA + timedelta(days=31)),
    })

    por_archivo = {h.file_path: h for h in hallazgos if "expir" in h.rule_id}
    assert por_archivo["vencido.pem"].rule_id == "crypto.pqc.cert-expired"
    assert por_archivo["por-vencer.pem"].rule_id == "crypto.pqc.cert-expiring"
    assert por_archivo["por-vencer.pem"].severity.value == "low"
    assert "vigente.pem" not in por_archivo


def test_varios_certificados_en_un_archivo_con_su_linea(tmp_path):
    cadena = _certificado(cn="hoja.invalid") + _certificado(cn="raiz.invalid")

    hallazgos = _escanear(tmp_path, {"cadena.pem": cadena})

    segunda_linea = cadena[: cadena.index(b"-----BEGIN", 10)].count(b"\n") + 1
    assert [h.line for h in hallazgos] == [1, segunda_linea]
    assert [h.metadata["subject"] for h in hallazgos] == ["CN=hoja.invalid", "CN=raiz.invalid"]


def test_certificado_en_formato_der(tmp_path):
    der = x509.load_pem_x509_certificate(_certificado()).public_bytes(serialization.Encoding.DER)

    hallazgos = _escanear(tmp_path, {"server.cer": der})

    assert _reglas(hallazgos) == ["crypto.pqc.cert-quantum-vulnerable"]


def test_clave_privada_reporta_el_algoritmo_sin_copiar_la_clave(tmp_path):
    pem = _pem_privada(_clave_rsa(1024))

    hallazgos = _escanear(tmp_path, {"server.key": pem})

    assert _reglas(hallazgos) == ["crypto.pqc.cert-weak-key"]
    hallazgo = hallazgos[0]
    assert hallazgo.title == "Clave privada con clave RSA de 1024 bits"
    assert "BEGIN" not in hallazgo.snippet and pem.decode().splitlines()[1] not in hallazgo.snippet


def test_clave_ed25519(tmp_path):
    hallazgos = _escanear(tmp_path, {"firma.key": _pem_privada(ed25519.Ed25519PrivateKey.generate())})

    assert _reglas(hallazgos) == ["crypto.pqc.cert-quantum-vulnerable"]
    assert hallazgos[0].metadata["algorithm"] == "Ed25519"


def test_clave_publica(tmp_path):
    pem = _clave_rsa().public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )

    hallazgos = _escanear(tmp_path, {"publica.pem": pem})

    assert _reglas(hallazgos) == ["crypto.pqc.cert-quantum-vulnerable"]
    assert hallazgos[0].metadata["kind"] == "public_key"


@pytest.mark.parametrize("contenido", [
    b"esto no es un certificado",
    b"-----BEGIN CERTIFICATE-----\nAAAA\n-----END CERTIFICATE-----\n",
    b"\x00\x01\x02\xff" * 10,
])
def test_archivos_rotos_no_rompen_el_escaneo(tmp_path, contenido):
    assert _escanear(tmp_path, {"roto.pem": contenido, "roto.crt": contenido}) == []


def test_clave_cifrada_con_contrasena_se_saltea(tmp_path):
    assert _escanear(tmp_path, {"cifrada.key": _pem_privada(_clave_rsa(), cifrada=True)}) == []


def test_ignora_otras_extensiones_y_carpetas_de_dependencias(tmp_path):
    pem = _certificado()
    assert _escanear(tmp_path, {"cert.txt": pem, "node_modules/paquete/cert.pem": pem}) == []


def test_archivo_demasiado_grande_se_saltea(tmp_path):
    assert _escanear(tmp_path, {"enorme.pem": _certificado() + b"\n" * 1_000_001}) == []


def test_scan_pqc_incluye_los_certificados(tmp_path):
    (tmp_path / "server.pem").write_bytes(_certificado())

    assert [h.rule_id for h in scan_pqc(str(tmp_path))] == ["crypto.pqc.cert-quantum-vulnerable"]


@pytest.mark.skipif(os.environ.get("QUBITOR_TESTS_RED") != "1",
                    reason="clona el repo de demo; correr con QUBITOR_TESTS_RED=1")
def test_detecta_el_certificado_plantado_en_el_repo_de_demo(tmp_path):
    import subprocess

    destino = tmp_path / "demo"
    subprocess.run(["git", "clone", "--depth", "1", "--quiet",
                    "https://github.com/ValentinaPertile/qubitor-demo-vulnerable.git", str(destino)],
                   check=True, timeout=60)

    hallazgos = scan_certs(str(destino), now=AHORA)

    assert {(h.rule_id, h.file_path) for h in hallazgos} == {
        ("crypto.pqc.cert-weak-key", "certs/server.pem"),
        ("crypto.pqc.cert-weak-signature", "certs/server.pem"),
    }
