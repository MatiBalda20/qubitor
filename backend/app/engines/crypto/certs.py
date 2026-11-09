"""Certificados y claves versionados en el repo (Módulo D).

Lee los archivos `.pem`, `.crt`, `.cer`, `.der` y `.key`, y los keystores
PKCS#12 (`.p12`, `.pfx`) sin contraseña, con la librería `cryptography`, y
reporta:

- claves RSA, de curva elíptica, DSA o Ed25519: las rompe Shor;
- claves RSA de menos de 2048 bits: se factorizan hoy;
- certificados firmados con SHA-1 o MD5;
- certificados vencidos o que vencen pronto.

Que una clave privada esté commiteada lo reporta el motor de secretos (Módulo
C): acá solo se mira qué algoritmo usa. Nunca se copia el contenido del archivo
al hallazgo, solo una descripción.
"""

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import (
    dsa,
    ec,
    ed448,
    ed25519,
    rsa,
    x448,
    x25519,
)
from cryptography.hazmat.primitives.serialization import pkcs12

from app.engines.base import Finding, Severity
from app.engines.crypto.files import iter_repo_files

KEYSTORE_SUFFIXES = (".p12", ".pfx")
CERT_SUFFIXES = (".pem", ".crt", ".cer", ".der", ".key", *KEYSTORE_SUFFIXES)
MAX_FILE_BYTES = 1_000_000
EXPIRING_DAYS = 30
MIN_RSA_BITS = 2048
WEAK_SIGNATURE_HASHES = {"sha1", "md5"}

_PEM_BLOCK = re.compile(rb"-----BEGIN ([A-Z0-9 ]+)-----.+?-----END \1-----", re.DOTALL)

_SHOR = (
    "{algorithm} es vulnerable al algoritmo de Shor: una computadora cuántica suficientemente "
    "grande podría romperla. Planificar la migración a ML-DSA (FIPS 204) para firmas y "
    "certificados, y a ML-KEM (FIPS 203) para intercambio de claves."
)


def scan_certs(repo_path: str, now: datetime | None = None) -> list[Finding]:
    repo = Path(repo_path)
    now = now or datetime.now(timezone.utc)
    findings: list[Finding] = []
    for path in iter_repo_files(repo, lambda p: p.suffix in CERT_SUFFIXES):
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                continue
            data = path.read_bytes()
        except OSError:
            continue
        file_path = path.relative_to(repo).as_posix()
        for line, kind, obj in _load_objects(data, path.suffix):
            findings.extend(_check(obj, kind, file_path, line, now))
    return findings


def _load_objects(data: bytes, suffix: str) -> list[tuple[int, str, object]]:
    """Certificados y claves del archivo: (línea, tipo, objeto). Lo que no se puede leer se saltea."""
    if suffix in KEYSTORE_SUFFIXES:
        return _load_keystore(data)
    objects = []
    for match in _PEM_BLOCK.finditer(data):
        line = data.count(b"\n", 0, match.start()) + 1
        loaded = _load_pem(match.group(1).decode(), match.group(0))
        if loaded is not None:
            objects.append((line, *loaded))
    if not objects and suffix in (".crt", ".cer", ".der"):
        try:
            objects.append((1, "certificate", x509.load_der_x509_certificate(data)))
        except ValueError:
            pass
    return objects


def _load_keystore(data: bytes) -> list[tuple[int, str, object]]:
    """Certificados de un keystore PKCS#12, o su clave si no trae ninguno.

    Con contraseña no se puede leer y se saltea, como una clave cifrada. Un
    archivo binario no tiene líneas: todo se reporta en la línea 1.
    """
    try:
        store = pkcs12.load_pkcs12(data, password=None)
    except (ValueError, TypeError):
        return []
    certificates = ([store.cert] if store.cert else []) + store.additional_certs
    if certificates:
        return [(1, "certificate", entry.certificate) for entry in certificates]
    return [(1, "private_key", store.key.public_key())] if store.key else []


def _load_pem(label: str, block: bytes) -> tuple[str, object] | None:
    try:
        if label in ("CERTIFICATE", "X509 CERTIFICATE"):
            return "certificate", x509.load_pem_x509_certificate(block)
        if label in ("PUBLIC KEY", "RSA PUBLIC KEY"):
            return "public_key", serialization.load_pem_public_key(block)
        if label == "OPENSSH PRIVATE KEY":
            return "private_key", serialization.load_ssh_private_key(block, password=None).public_key()
        if label.endswith("PRIVATE KEY") and not label.startswith("ENCRYPTED"):
            return "private_key", serialization.load_pem_private_key(block, password=None).public_key()
    except (ValueError, TypeError):
        # Clave cifrada con contraseña, formato no soportado o archivo roto: se saltea.
        return None
    return None


def _check(obj: object, kind: str, file_path: str, line: int, now: datetime) -> list[Finding]:
    certificate = obj if kind == "certificate" else None
    key = certificate.public_key() if certificate else obj
    algorithm, bits = _describe_key(key)
    noun = {"certificate": "Certificado", "private_key": "Clave privada", "public_key": "Clave pública"}[kind]

    metadata: dict = {"algorithm": algorithm, "kind": kind}
    if bits:
        metadata["key_size"] = bits
    label = f"{algorithm}-{bits}" if bits and algorithm in ("RSA", "DSA") else algorithm
    details = [label]
    if certificate:
        metadata["subject"] = certificate.subject.rfc4514_string()[:200]
        metadata["not_after"] = certificate.not_valid_after_utc.isoformat()
        signature_hash = _signature_hash(certificate)
        if signature_hash:
            metadata["signature_hash"] = signature_hash
        details.append(f"vence {certificate.not_valid_after_utc.date().isoformat()}")
    snippet = f"{noun} {metadata.get('subject', '')} ({', '.join(details)})".replace("  ", " ")

    def finding(rule: str, title: str, severity: Severity, description: str, cwe: str) -> Finding:
        return Finding(
            engine="crypto", rule_id=f"crypto.pqc.{rule}", title=title, severity=severity,
            file_path=file_path, line=line, snippet=snippet, description=description,
            cwe=cwe, metadata=metadata,
        )

    findings = []
    if algorithm == "RSA" and bits and bits < MIN_RSA_BITS:
        findings.append(finding(
            "cert-weak-key", f"{noun} con clave RSA de {bits} bits", Severity.HIGH,
            f"Una clave RSA de {bits} bits se puede factorizar hoy con recursos clásicos, y además la "
            "rompe Shor. Reemplazarla ya por RSA de 3072 bits y planificar la migración a ML-DSA.",
            "CWE-326",
        ))
    elif _breaks_with_shor(key):
        findings.append(finding(
            "cert-quantum-vulnerable", f"{noun} {label} vulnerable a computación cuántica", Severity.MEDIUM,
            _SHOR.format(algorithm=label), "CWE-327",
        ))

    if certificate:
        signature_hash = metadata.get("signature_hash")
        if signature_hash in WEAK_SIGNATURE_HASHES:
            name = signature_hash.upper().replace("SHA1", "SHA-1")
            findings.append(finding(
                "cert-weak-signature", f"Certificado firmado con {name}", Severity.HIGH,
                f"{name} tiene colisiones prácticas: se puede fabricar otro certificado con la misma "
                "firma. Volver a emitirlo firmado con SHA-256 o superior.",
                "CWE-327",
            ))
        not_after = certificate.not_valid_after_utc
        if not_after < now:
            findings.append(finding(
                "cert-expired", "Certificado vencido", Severity.MEDIUM,
                f"El certificado venció el {not_after.date().isoformat()}. Renovarlo o quitarlo del repo.",
                "CWE-298",
            ))
        elif not_after < now + timedelta(days=EXPIRING_DAYS):
            findings.append(finding(
                "cert-expiring", "Certificado por vencer", Severity.LOW,
                f"El certificado vence el {not_after.date().isoformat()}, en menos de {EXPIRING_DAYS} días.",
                "CWE-298",
            ))
    return findings


def _describe_key(key: object) -> tuple[str, int | None]:
    if isinstance(key, rsa.RSAPublicKey):
        return "RSA", key.key_size
    if isinstance(key, ec.EllipticCurvePublicKey):
        return f"EC {key.curve.name}", key.key_size
    if isinstance(key, dsa.DSAPublicKey):
        return "DSA", key.key_size
    if isinstance(key, ed25519.Ed25519PublicKey):
        return "Ed25519", None
    if isinstance(key, ed448.Ed448PublicKey):
        return "Ed448", None
    if isinstance(key, x25519.X25519PublicKey):
        return "X25519", None
    if isinstance(key, x448.X448PublicKey):
        return "X448", None
    return type(key).__name__, None


def _breaks_with_shor(key: object) -> bool:
    return isinstance(key, (
        rsa.RSAPublicKey, ec.EllipticCurvePublicKey, dsa.DSAPublicKey,
        ed25519.Ed25519PublicKey, ed448.Ed448PublicKey, x25519.X25519PublicKey, x448.X448PublicKey,
    ))


def _signature_hash(certificate: x509.Certificate) -> str | None:
    try:
        algorithm = certificate.signature_hash_algorithm
    except UnsupportedAlgorithm:
        # Algoritmo de firma que la librería no conoce: no se puede decir nada.
        return None
    return algorithm.name if algorithm else None
