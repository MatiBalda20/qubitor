"""Criptografía post-cuántica (Módulo D).

Detecta algoritmos vulnerables a una computadora cuántica: RSA, ECDSA, ECDH y
DH (algoritmo de Shor) y AES-128 (algoritmo de Grover). Todo uso de
criptografía, aunque sea seguro, se registra con severidad `info` para armar
el inventario criptográfico (CBOM).

Las reglas llevan el prefijo `crypto.pqc.*`. CryptoEngine (compartido con el
Módulo C) llama a `scan_pqc` y junta sus resultados con los de `classic.py`.
"""

import ast
import copy
import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

from app.engines.base import Finding, Severity

# Carpetas que no son código del usuario: dependencias, entornos y builds.
IGNORED_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build"}

PYTHON_SUFFIXES = (".py",)
JS_SUFFIXES = (".js", ".mjs", ".cjs", ".ts")

# Largo máximo del fragmento de código que se guarda en cada hallazgo.
MAX_SNIPPET_CHARS = 200


@dataclass(frozen=True)
class _Rule:
    rule_id: str
    algorithm: str
    title: str
    severity: Severity
    description: str


_SHOR_DESCRIPTION = (
    "{algorithm} es vulnerable al algoritmo de Shor: una computadora cuántica "
    "suficientemente grande podría romperlo. Los datos cifrados hoy pueden "
    "guardarse y descifrarse en el futuro (riesgo «cosechar ahora, descifrar "
    "después»). Planificar la migración a ML-KEM (FIPS 203) para intercambio "
    "de claves y a ML-DSA (FIPS 204) para firmas."
)

def _shor_rule(rule_id: str, algorithm: str, title: str) -> _Rule:
    return _Rule(
        rule_id=rule_id,
        algorithm=algorithm,
        title=title,
        severity=Severity.MEDIUM,
        description=_SHOR_DESCRIPTION.format(algorithm=algorithm),
    )


_AES_128 = _Rule(
    rule_id="crypto.pqc.aes-128",
    algorithm="AES-128",
    title="Cifrado AES-128 debilitado por computación cuántica",
    severity=Severity.LOW,
    description=(
        "AES-128 es vulnerable al algoritmo de Grover: una computadora cuántica "
        "reduciría su seguridad efectiva a la mitad (de 128 a 64 bits). Para "
        "datos que deben seguir siendo secretos por muchos años, preferir AES-256."
    ),
)


_INVENTORY_DESCRIPTION = (
    "Uso de {algorithm} registrado en el inventario criptográfico (CBOM). "
    "No tiene un riesgo post-cuántico conocido."
)


def _inventory_rule(kind: str, algorithm: str, description: str = _INVENTORY_DESCRIPTION) -> _Rule:
    """Uso de criptografía sin riesgo post-cuántico conocido: solo va al inventario (CBOM)."""
    return _Rule(
        rule_id=f"crypto.pqc.inventory.{kind}",
        algorithm=algorithm,
        title=f"Uso de {algorithm} (inventario criptográfico)",
        severity=Severity.INFO,
        description=description.format(algorithm=algorithm),
    )


def _aes_inventory(algorithm: str) -> _Rule:
    return _inventory_rule("aes", algorithm, (
        "Uso de {algorithm} registrado en el inventario criptográfico (CBOM). "
        "Si el tamaño de clave no se pudo determinar, verificar que sea de 256 bits."
    ))


def _aes_by_key_size(node: ast.Call) -> _Rule:
    """Elige la regla de AES según el tamaño de clave pedido: generate_key(bit_length=N)."""
    bits = _int_argument(node, position=0, keyword="bit_length")
    if bits == 128:
        return _AES_128
    if bits is None:
        return _aes_inventory("AES")
    return _aes_inventory(f"AES-{bits}")


_RSA_KEYGEN = _shor_rule(
    "crypto.pqc.rsa-keygen", "RSA",
    "Generación de clave RSA vulnerable a computación cuántica",
)
_EC_KEYGEN = _shor_rule(
    "crypto.pqc.ec-keygen", "ECC",
    "Generación de clave de curva elíptica vulnerable a computación cuántica",
)
_ECDSA = _shor_rule(
    "crypto.pqc.ecdsa", "ECDSA",
    "Firma ECDSA vulnerable a computación cuántica",
)
_ECDH = _shor_rule(
    "crypto.pqc.ecdh", "ECDH",
    "Intercambio de claves ECDH vulnerable a computación cuántica",
)
_DH = _shor_rule(
    "crypto.pqc.dh", "DH",
    "Intercambio de claves Diffie-Hellman vulnerable a computación cuántica",
)
_DSA_KEYGEN = _shor_rule(
    "crypto.pqc.dsa-keygen", "DSA",
    "Generación de clave DSA vulnerable a computación cuántica",
)
_EDDSA = _shor_rule(
    "crypto.pqc.eddsa", "EdDSA",
    "Firma EdDSA (Ed25519 / Ed448) vulnerable a computación cuántica",
)

_ASYMMETRIC = "cryptography.hazmat.primitives.asymmetric"
_CIPHERS = "cryptography.hazmat.primitives.ciphers"

# Reglas por llamada: nombre completo de la función → regla que dispara, o una
# función que mira los argumentos de la llamada y elige la regla.
CALL_RULES: dict[str, _Rule | Callable[[ast.Call], _Rule]] = {
    # cryptography
    f"{_ASYMMETRIC}.rsa.generate_private_key": _RSA_KEYGEN,
    f"{_ASYMMETRIC}.ec.generate_private_key": _EC_KEYGEN,
    f"{_ASYMMETRIC}.ec.ECDSA": _ECDSA,
    f"{_ASYMMETRIC}.ec.ECDH": _ECDH,
    f"{_ASYMMETRIC}.dh.generate_parameters": _DH,
    f"{_ASYMMETRIC}.dh.DHParameterNumbers": _DH,
    f"{_ASYMMETRIC}.dsa.generate_private_key": _DSA_KEYGEN,
    # pycryptodome (se importa como `Crypto`)
    "Crypto.PublicKey.RSA.generate": _RSA_KEYGEN,
    "Crypto.PublicKey.ECC.generate": _EC_KEYGEN,
    "Crypto.PublicKey.DSA.generate": _DSA_KEYGEN,
    "Crypto.Cipher.AES.new": _aes_inventory("AES"),
    # rsa (python-rsa)
    "rsa.newkeys": _RSA_KEYGEN,
    # ecdsa
    "ecdsa.SigningKey.generate": _ECDSA,
    # cryptography: curvas de Edwards y Montgomery (también las rompe Shor).
    # X25519 y X448 son ECDH sobre otras curvas.
    f"{_ASYMMETRIC}.ed25519.Ed25519PrivateKey.generate": _EDDSA,
    f"{_ASYMMETRIC}.ed448.Ed448PrivateKey.generate": _EDDSA,
    f"{_ASYMMETRIC}.x25519.X25519PrivateKey.generate": _ECDH,
    f"{_ASYMMETRIC}.x448.X448PrivateKey.generate": _ECDH,
    # cryptography: cifrado simétrico e inventario
    f"{_CIPHERS}.algorithms.AES128": _AES_128,
    f"{_CIPHERS}.algorithms.AES256": _aes_inventory("AES-256"),
    f"{_CIPHERS}.algorithms.AES": _aes_inventory("AES"),
    f"{_CIPHERS}.aead.AESGCM.generate_key": _aes_by_key_size,
    f"{_CIPHERS}.aead.ChaCha20Poly1305": _inventory_rule("chacha20", "ChaCha20-Poly1305"),
    "argon2.PasswordHasher": _inventory_rule("password-hash", "Argon2"),
    "cryptography.hazmat.primitives.kdf.argon2.Argon2id": _inventory_rule("password-hash", "Argon2"),
}

# Hashes seguros: (nombre en `cryptography`, nombre en `hashlib`, nombre para el reporte).
# MD5 y SHA-1 no van acá: están rotos hoy y los reporta classic.py (Módulo C).
_SAFE_HASHES = [
    ("SHA256", "sha256", "SHA-256"),
    ("SHA384", "sha384", "SHA-384"),
    ("SHA512", "sha512", "SHA-512"),
    ("SHA3_256", "sha3_256", "SHA3-256"),
    ("SHA3_384", "sha3_384", "SHA3-384"),
    ("SHA3_512", "sha3_512", "SHA3-512"),
    ("BLAKE2b", "blake2b", "BLAKE2b"),
]
for _crypto_name, _hashlib_name, _algorithm in _SAFE_HASHES:
    CALL_RULES[f"cryptography.hazmat.primitives.hashes.{_crypto_name}"] = _inventory_rule("hash", _algorithm)
    CALL_RULES[f"hashlib.{_hashlib_name}"] = _inventory_rule("hash", _algorithm)


# --- JavaScript (módulo `crypto` de Node.js) ---
# No hay un `ast` en la librería estándar de Python para JavaScript, así que se
# usan expresiones regulares sobre el código sin comentarios.

_JS_KEY_PAIR_TYPES = {
    "rsa": _RSA_KEYGEN,
    "rsa-pss": _RSA_KEYGEN,
    "ec": _EC_KEYGEN,
    "dsa": _DSA_KEYGEN,
    "dh": _DH,
    "ed25519": _EDDSA,
    "ed448": _EDDSA,
    "x25519": _ECDH,
    "x448": _ECDH,
}

# Nombres de hash de Node.js → nombre para el reporte. MD5 y SHA-1 son del Módulo C.
_JS_SAFE_HASHES = {
    "sha256": "SHA-256",
    "sha384": "SHA-384",
    "sha512": "SHA-512",
    "sha3-256": "SHA3-256",
    "sha3-384": "SHA3-384",
    "sha3-512": "SHA3-512",
    "blake2b512": "BLAKE2b",
}


def _js_key_pair(match: re.Match) -> _Rule | None:
    return _JS_KEY_PAIR_TYPES.get(match["algo"].lower())


def _js_aes(match: re.Match) -> _Rule:
    bits = int(match["bits"])
    if bits == 128:
        return _AES_128
    return _aes_inventory(f"AES-{bits}")


def _js_hash(match: re.Match) -> _Rule | None:
    algorithm = _JS_SAFE_HASHES.get(match["algo"].lower())
    if algorithm is None:
        return None
    return _inventory_rule("hash", algorithm)


_QUOTE = r"""['"`]"""

# Firmar o verificar con el módulo crypto de Node.js. Si el archivo genera una
# clave EC y además firma, esa clave es de ECDSA: va a ML-DSA, no a ML-KEM.
_JS_SIGNING = re.compile(r"\bcrypto\.(?:sign|verify)\s*\(|\bcreate(?:Sign|Verify)\s*\(")

# Cada regla: patrón a buscar → regla que dispara, o una función que mira lo
# encontrado y elige la regla (igual que CALL_RULES para Python).
JS_RULES: list[tuple[re.Pattern, _Rule | Callable[[re.Match], _Rule | None]]] = [
    (re.compile(rf"\bgenerateKeyPair(?:Sync)?\s*\(\s*{_QUOTE}(?P<algo>[\w-]+){_QUOTE}"), _js_key_pair),
    (re.compile(r"\bcreateECDH\s*\("), _ECDH),
    (re.compile(r"\b(?:createDiffieHellman|createDiffieHellmanGroup|getDiffieHellman)\s*\("), _DH),
    (re.compile(rf"\bcreateCipheriv\s*\(\s*{_QUOTE}aes-(?P<bits>128|192|256)", re.IGNORECASE), _js_aes),
    (re.compile(rf"\bcreateCipheriv\s*\(\s*{_QUOTE}chacha20-poly1305{_QUOTE}", re.IGNORECASE),
     _inventory_rule("chacha20", "ChaCha20-Poly1305")),
    (re.compile(rf"\bcreateHash\s*\(\s*{_QUOTE}(?P<algo>[\w-]+){_QUOTE}"), _js_hash),
]


def scan_pqc(repo_path: str) -> list[Finding]:
    repo = Path(repo_path)
    findings: list[Finding] = []
    for path in _iter_files(repo, PYTHON_SUFFIXES):
        tree = _parse_python(path)
        if tree is None:
            continue
        findings.extend(_scan_python_tree(tree, path.relative_to(repo).as_posix()))
    for path in _iter_files(repo, JS_SUFFIXES):
        source = _read_text(path)
        if source is None:
            continue
        findings.extend(_scan_js_source(source, path.relative_to(repo).as_posix()))
    return findings


def _iter_files(repo: Path, suffixes: tuple[str, ...]) -> Iterator[Path]:
    repo_root = repo.resolve()
    for path in repo.rglob("*"):
        if path.suffix not in suffixes:
            continue
        # El repo no es de confianza: un enlace simbólico podría apuntar a un
        # archivo del servidor y filtrar su contenido en el reporte.
        if path.is_symlink() or not path.resolve().is_relative_to(repo_root):
            continue
        if not path.is_file():
            continue
        if any(part in IGNORED_DIRS for part in path.relative_to(repo).parts):
            continue
        yield path


def _read_text(path: Path) -> str | None:
    """Devuelve el contenido del archivo, o None si no se puede leer.

    El contrato pide no lanzar excepciones por archivos ilegibles: se saltean.
    """
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _parse_python(path: Path) -> ast.Module | None:
    """Devuelve el AST del archivo, o None si no se puede leer o parsear."""
    source = _read_text(path)
    if source is None:
        return None
    try:
        return ast.parse(source, filename=str(path))
    except (SyntaxError, ValueError, RecursionError):
        return None


def _scan_python_tree(tree: ast.Module, file_path: str) -> list[Finding]:
    aliases = _collect_imports(tree)
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        rule = CALL_RULES.get(_qualified_name(node.func, aliases))
        if callable(rule):
            rule = rule(node)
        if rule is not None:
            findings.append(_make_finding(rule, file_path, node.lineno, _snippet(node)))
    return findings


def _collect_imports(tree: ast.Module) -> dict[str, str]:
    """Mapea cada nombre importado al módulo real del que viene.

    `from cryptography.hazmat.primitives.asymmetric import rsa`
    → {"rsa": "cryptography.hazmat.primitives.asymmetric.rsa"}
    """
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname:
                    aliases[alias.asname] = alias.name
                else:
                    top = alias.name.split(".")[0]
                    aliases[top] = top
        elif isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                aliases[alias.asname or alias.name] = f"{node.module}.{alias.name}"
    return aliases


def _qualified_name(func: ast.expr, aliases: dict[str, str]) -> str | None:
    """Arma el nombre completo de la función llamada, resolviendo los imports.

    `rsa.generate_private_key` → "cryptography...rsa.generate_private_key".
    Devuelve None si el nombre no viene de un import (por ejemplo, una
    variable propia del usuario que casualmente se llama `rsa`).
    """
    parts: list[str] = []
    while isinstance(func, ast.Attribute):
        parts.append(func.attr)
        func = func.value
    if not isinstance(func, ast.Name):
        return None
    base = aliases.get(func.id)
    if base is None:
        return None
    return ".".join([base, *reversed(parts)])


def _int_argument(node: ast.Call, position: int, keyword: str) -> int | None:
    """Devuelve un argumento entero escrito literalmente en la llamada.

    Lo busca por nombre (`bit_length=128`) o por posición (`generate_key(128)`).
    Si el valor es una variable o no está, devuelve None: no se puede saber.
    """
    value = None
    for kw in node.keywords:
        if kw.arg == keyword:
            value = kw.value
    if value is None and len(node.args) > position:
        value = node.args[position]
    if isinstance(value, ast.Constant) and isinstance(value.value, int):
        return value.value
    return None


def _scan_js_source(source: str, file_path: str) -> list[Finding]:
    code = _strip_js_comments(source)
    signs = _JS_SIGNING.search(code) is not None
    findings: list[Finding] = []
    for pattern, rule in JS_RULES:
        for match in pattern.finditer(code):
            found = rule(match) if callable(rule) else rule
            if found is None:
                continue
            if found is _EC_KEYGEN and signs:
                found = _ECDSA
            line = code.count("\n", 0, match.start()) + 1
            # Solo hasta el nombre del algoritmo: lo que sigue (claves, IVs)
            # puede ser secreto y no debe quedar en el reporte.
            snippet = " ".join(match[0].split()) + "…"
            findings.append(_make_finding(found, file_path, line, snippet))
    findings.sort(key=lambda finding: finding.line)
    return findings


def _strip_js_comments(source: str) -> str:
    """Reemplaza los comentarios `//` y `/* */` por espacios.

    Respeta los textos entre comillas (`'http://...'` no es un comentario) y
    conserva los saltos de línea, para que los números de línea no cambien.
    """
    result: list[str] = []
    quote = None
    i = 0
    while i < len(source):
        char = source[i]
        if quote:
            result.append(char)
            if char == "\\":
                result.append(source[i + 1:i + 2])
                i += 2
                continue
            if char == quote:
                quote = None
            i += 1
        elif char in "'\"`":
            quote = char
            result.append(char)
            i += 1
        elif source.startswith("//", i):
            end = source.find("\n", i)
            end = len(source) if end == -1 else end
            result.append(" " * (end - i))
            i = end
        elif source.startswith("/*", i):
            end = source.find("*/", i + 2)
            end = len(source) if end == -1 else end + 2
            result.append(re.sub(r"[^\n]", " ", source[i:end]))
            i = end
        else:
            result.append(char)
            i += 1
    return "".join(result)


def _make_finding(rule: _Rule, file_path: str, line: int, snippet: str) -> Finding:
    return Finding(
        engine="crypto",
        rule_id=rule.rule_id,
        title=rule.title,
        severity=rule.severity,
        file_path=file_path,
        line=line,
        snippet=snippet,
        description=rule.description,
        cwe="CWE-327",
        metadata={"algorithm": rule.algorithm},
    )


class _MaskStrings(ast.NodeTransformer):
    """Reemplaza cada texto o bytes del código por '***'.

    Las claves suelen escribirse como texto (`AES.new(b'mi-clave')`), y el
    snippet se guarda en la base y se envía a la IA: nunca debe incluirlas.
    """

    def visit_Constant(self, node: ast.Constant) -> ast.Constant:
        if isinstance(node.value, (str, bytes)):
            return ast.copy_location(ast.Constant(value="***"), node)
        return node


def _snippet(node: ast.Call) -> str:
    masked = _MaskStrings().visit(copy.deepcopy(node))
    text = ast.unparse(masked)
    if len(text) > MAX_SNIPPET_CHARS:
        text = text[:MAX_SNIPPET_CHARS] + "…"
    return text
