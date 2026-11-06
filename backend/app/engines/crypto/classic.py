import ast
import re
from pathlib import Path

from app.engines.base import Finding, Severity
from app.engines.crypto.pqc import (
    _collect_imports, _qualified_name, _int_argument, _snippet as pqc_snippet, IGNORED_DIRS
)

PYTHON_SUFFIXES = (".py",)
JS_SUFFIXES = (".js", ".ts", ".jsx", ".tsx")

def _create_finding(rule: str, title: str, severity: Severity, file_path: str, line: int, snippet: str, desc: str) -> Finding:
    return Finding(
        engine="crypto",
        rule_id=f"crypto.classic.{rule}",
        title=title,
        severity=severity,
        file_path=file_path,
        line=line,
        snippet=snippet,
        description=desc,
        cwe="CWE-327",
    )

def scan_classic(repo_path: str) -> list[Finding]:
    repo = Path(repo_path).resolve()
    findings = []
    for path in repo.rglob("*"):
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(repo):
            continue
        if any(part in IGNORED_DIRS for part in path.relative_to(repo).parts):
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
            
        rel_path = path.relative_to(repo).as_posix()
        if path.suffix in PYTHON_SUFFIXES:
            findings.extend(_scan_python(content, rel_path))
        elif path.suffix in JS_SUFFIXES:
            findings.extend(_scan_js(content, rel_path))
    return findings

def _scan_python(content: str, file_path: str) -> list[Finding]:
    findings = []
    try:
        tree = ast.parse(content, filename=file_path)
    except (SyntaxError, ValueError):
        return findings

    aliases = _collect_imports(tree)

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            try:
                snippet = pqc_snippet(node)
            except RecursionError:
                continue

            func_name = _qualified_name(node.func, aliases)
            if not func_name:
                if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                    func_name = f"{node.func.value.id}.{node.func.attr}"
                elif isinstance(node.func, ast.Name):
                    func_name = node.func.id
                else:
                    continue

            # MD5 / SHA1
            if func_name in (
                "hashlib.md5", "hashlib.sha1", "MD5.new", "SHA1.new", "md5", "sha1",
                "cryptography.hazmat.primitives.hashes.MD5",
                "cryptography.hazmat.primitives.hashes.SHA1",
                "Crypto.Hash.MD5.new", "Crypto.Hash.SHA1.new"
            ):
                findings.append(_create_finding("weak-hash", "Uso de algoritmo de hash roto (MD5/SHA-1)", Severity.HIGH, file_path, node.lineno, snippet, "Usar SHA-256 para integridad."))
            
            # DES / 3DES / RC4 / Blowfish
            elif func_name in (
                "Crypto.Cipher.DES.new", "Crypto.Cipher.DES3.new", "Crypto.Cipher.ARC4.new", "Crypto.Cipher.Blowfish.new",
                "cryptography.hazmat.primitives.ciphers.algorithms.TripleDES", 
                "cryptography.hazmat.primitives.ciphers.algorithms.Blowfish",
                "cryptography.hazmat.primitives.ciphers.algorithms.ARC4",
                "DES.new", "DES3.new", "ARC4.new", "Blowfish.new", "TripleDES"
            ):
                findings.append(_create_finding("weak-cipher", "Uso de cifrado obsoleto (DES/RC4/Blowfish)", Severity.HIGH, file_path, node.lineno, snippet, "Migrar a AES-256-GCM."))
            
            # RSA < 2048
            elif func_name in (
                "cryptography.hazmat.primitives.asymmetric.rsa.generate_private_key",
                "Crypto.PublicKey.RSA.generate", "rsa.newkeys", "rsa.generate_private_key", "RSA.generate", "newkeys"
            ):
                size = _int_argument(node, 0, "key_size") or _int_argument(node, 0, "bits") or _int_argument(node, 1, "key_size") or _int_argument(node, 0, "")
                if isinstance(size, int) and size < 2048:
                    findings.append(_create_finding("rsa-weak-key", "Clave RSA menor a 2048 bits", Severity.HIGH, file_path, node.lineno, snippet, "Mínimo 3072 bits."))
            
            # AES ECB
            elif func_name in ("Crypto.Cipher.AES.new", "AES.new"):
                mode_node = None
                if len(node.args) > 1:
                    mode_node = node.args[1]
                for kw in node.keywords:
                    if kw.arg == "mode":
                        mode_node = kw.value
                
                is_ecb = False
                if isinstance(mode_node, ast.Attribute) and mode_node.attr == "MODE_ECB":
                    is_ecb = True
                elif isinstance(mode_node, ast.Name) and mode_node.id == "MODE_ECB":
                    is_ecb = True
                elif isinstance(mode_node, ast.Constant) and mode_node.value == 1:
                    is_ecb = True

                if is_ecb:
                    findings.append(_create_finding("aes-ecb", "AES en modo ECB", Severity.MEDIUM, file_path, node.lineno, snippet, "El modo ECB filtra patrones del texto plano."))
            
            # TLS Inseguro (verify=False)
            elif func_name in ("requests.get", "requests.post", "requests.request", "requests.put"):
                verify = _get_kwarg(node, "verify")
                if verify is False:
                    findings.append(_create_finding("tls-insecure", "Validación TLS deshabilitada", Severity.HIGH, file_path, node.lineno, snippet, "Peligro de Man-in-the-Middle."))

        # Random no criptográfico (solo si se asigna a variables de seguridad)
        elif isinstance(node, ast.Assign):
            is_secret_target = False
            for target in node.targets:
                if isinstance(target, ast.Name) and re.search(r"(?i)(token|key|secret|password)", target.id):
                    is_secret_target = True
            
            if is_secret_target:
                for subnode in ast.walk(node.value):
                    if isinstance(subnode, ast.Call):
                        func = _qualified_name(subnode.func, aliases)
                        if not func:
                            if isinstance(subnode.func, ast.Attribute) and isinstance(subnode.func.value, ast.Name):
                                func = f"{subnode.func.value.id}.{subnode.func.attr}"
                        if func in ("random.choice", "random.randint", "random.random", "random.choices"):
                            try:
                                snippet = pqc_snippet(node)
                            except RecursionError:
                                snippet = func
                            findings.append(_create_finding("insecure-random", "Uso de random no criptográfico para secretos", Severity.MEDIUM, file_path, node.lineno, snippet, "Usar el módulo secrets."))

    return findings

def _get_kwarg(node, name):
    for kw in node.keywords:
        if kw.arg == name and isinstance(kw.value, ast.Constant):
            return kw.value.value
    return None

def _scan_js(content: str, file_path: str) -> list[Finding]:
    findings = []
    for i, line in enumerate(content.splitlines(), start=1):
        # Enmascarar strings en JS con regex simple para el snippet
        snippet = re.sub(r"""(['"`])(?:\\.|(?!\1).)*?\1""", r"\1***\1", line).strip()[:200]
        
        if re.search(r"createHash\(['\"](md5|sha1)['\"]\)", line, re.I):
            findings.append(_create_finding("weak-hash", "Uso de hash roto (MD5/SHA-1)", Severity.HIGH, file_path, i, snippet, "Usar SHA-256."))
        
        elif re.search(r"createCipheriv\(['\"](des|rc4|bf)", line, re.I):
            findings.append(_create_finding("weak-cipher", "Uso de cifrado obsoleto", Severity.HIGH, file_path, i, snippet, "Migrar a AES-256-GCM."))
            
        elif re.search(r"createCipheriv\(['\"]aes-\d{3}-ecb", line, re.I):
            findings.append(_create_finding("aes-ecb", "AES en modo ECB", Severity.MEDIUM, file_path, i, snippet, "El modo ECB es inseguro."))
        
        # RSA < 2048 en JS
        elif match := re.search(r"modulusLength:\s*(\d+)", line):
            if int(match.group(1)) < 2048 and re.search(r"rsa", line, re.I):
                findings.append(_create_finding("rsa-weak-key", "Clave RSA menor a 2048 bits", Severity.HIGH, file_path, i, snippet, "Mínimo 3072 bits."))
            
        # Math.random para tokens
        elif "Math.random()" in line and re.search(r"(?i)(token|key|secret|password)", line):
            findings.append(_create_finding("insecure-random", "Math.random para tokens", Severity.MEDIUM, file_path, i, snippet, "Usar crypto.randomBytes."))
            
        # TLS Inseguro / TLSv1
        elif re.search(r"rejectUnauthorized:\s*false", line) or re.search(r"secureProtocol:\s*['\"]TLSv1['\"]", line):
            findings.append(_create_finding("tls-insecure", "Validación TLS deshabilitada o TLS 1.0 en Node", Severity.HIGH, file_path, i, snippet, "Peligro de Man-in-the-Middle."))
            
    return findings