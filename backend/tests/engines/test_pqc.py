from app.engines.base import Severity
from app.engines.crypto.pqc import _iter_files, scan_pqc


def _escanear(tmp_path, codigo):
    (tmp_path / "app.py").write_text(codigo)
    return scan_pqc(str(tmp_path))


def test_repo_vacio_devuelve_lista_vacia(tmp_path):
    assert scan_pqc(str(tmp_path)) == []


def test_archivo_con_error_de_sintaxis_no_rompe(tmp_path):
    (tmp_path / "roto.py").write_text("def f(:\n")
    assert scan_pqc(str(tmp_path)) == []


def test_archivo_que_no_es_utf8_no_rompe(tmp_path):
    (tmp_path / "latin1.py").write_bytes("x = 'año'".encode("latin-1"))
    assert scan_pqc(str(tmp_path)) == []


def test_ignora_carpetas_de_dependencias(tmp_path):
    (tmp_path / "app.py").write_text("")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "lib.py").write_text("")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "site.py").write_text("")

    encontrados = [p.name for p in _iter_files(tmp_path, (".py",))]

    assert encontrados == ["app.py"]


# --- RSA ---

def test_detecta_generacion_de_clave_rsa(tmp_path):
    hallazgos = _escanear(tmp_path, (
        "from cryptography.hazmat.primitives.asymmetric import rsa\n"
        "\n"
        "clave = rsa.generate_private_key(public_exponent=65537, key_size=2048)\n"
    ))

    assert len(hallazgos) == 1
    h = hallazgos[0]
    assert h.rule_id == "crypto.pqc.rsa-keygen"
    assert h.severity == Severity.MEDIUM
    assert h.file_path == "app.py"
    assert h.line == 3
    assert "generate_private_key" in h.snippet


def test_detecta_rsa_importando_la_funcion_directamente(tmp_path):
    hallazgos = _escanear(tmp_path, (
        "from cryptography.hazmat.primitives.asymmetric.rsa import generate_private_key\n"
        "clave = generate_private_key(65537, 3072)\n"
    ))
    assert [h.rule_id for h in hallazgos] == ["crypto.pqc.rsa-keygen"]


def test_detecta_rsa_con_alias(tmp_path):
    hallazgos = _escanear(tmp_path, (
        "import cryptography.hazmat.primitives.asymmetric.rsa as r\n"
        "clave = r.generate_private_key(65537, 2048)\n"
    ))
    assert [h.rule_id for h in hallazgos] == ["crypto.pqc.rsa-keygen"]


def test_no_detecta_rsa_en_comentarios_ni_textos(tmp_path):
    hallazgos = _escanear(tmp_path, (
        "# rsa.generate_private_key(65537, 2048)\n"
        "ayuda = 'usar rsa.generate_private_key para crear claves'\n"
    ))
    assert hallazgos == []


def test_no_detecta_objeto_propio_llamado_rsa(tmp_path):
    hallazgos = _escanear(tmp_path, (
        "from mi_app import servicio as rsa\n"
        "rsa.generate_private_key()\n"
    ))
    assert hallazgos == []


# --- Curvas elípticas (ECDSA / ECDH) ---

def test_detecta_generacion_de_clave_de_curva_eliptica(tmp_path):
    hallazgos = _escanear(tmp_path, (
        "from cryptography.hazmat.primitives.asymmetric import ec\n"
        "clave = ec.generate_private_key(ec.SECP256R1())\n"
    ))

    assert len(hallazgos) == 1
    assert hallazgos[0].rule_id == "crypto.pqc.ec-keygen"
    assert hallazgos[0].severity == Severity.MEDIUM
    assert hallazgos[0].metadata["algorithm"] == "ECC"


def test_detecta_firma_ecdsa(tmp_path):
    hallazgos = _escanear(tmp_path, (
        "from cryptography.hazmat.primitives import hashes\n"
        "from cryptography.hazmat.primitives.asymmetric import ec\n"
        "def firmar(clave, datos):\n"
        "    return clave.sign(datos, ec.ECDSA(hashes.SHA256()))\n"
    ))

    # El SHA-256 de la firma también aparece, como inventario.
    assert [h.rule_id for h in hallazgos] == ["crypto.pqc.ecdsa", "crypto.pqc.inventory.hash"]
    assert hallazgos[0].line == 4


def test_detecta_intercambio_ecdh(tmp_path):
    hallazgos = _escanear(tmp_path, (
        "from cryptography.hazmat.primitives.asymmetric import ec\n"
        "def acordar(clave, clave_del_otro):\n"
        "    return clave.exchange(ec.ECDH(), clave_del_otro)\n"
    ))

    assert [h.rule_id for h in hallazgos] == ["crypto.pqc.ecdh"]


def test_detecta_firmas_ed25519_y_ed448(tmp_path):
    hallazgos = _escanear(tmp_path, (
        "from cryptography.hazmat.primitives.asymmetric import ed25519\n"
        "from cryptography.hazmat.primitives.asymmetric.ed448 import Ed448PrivateKey\n"
        "a = ed25519.Ed25519PrivateKey.generate()\n"
        "b = Ed448PrivateKey.generate()\n"
    ))

    assert [(h.rule_id, h.line) for h in hallazgos] == [("crypto.pqc.eddsa", 3), ("crypto.pqc.eddsa", 4)]
    assert all(h.severity == Severity.MEDIUM for h in hallazgos)


def test_x25519_y_x448_son_intercambio_ecdh(tmp_path):
    hallazgos = _escanear(tmp_path, (
        "from cryptography.hazmat.primitives.asymmetric import x25519, x448\n"
        "a = x25519.X25519PrivateKey.generate()\n"
        "b = x448.X448PrivateKey.generate()\n"
    ))

    assert [h.rule_id for h in hallazgos] == ["crypto.pqc.ecdh", "crypto.pqc.ecdh"]


def test_cargar_una_clave_ed25519_sin_generarla_no_es_hallazgo(tmp_path):
    hallazgos = _escanear(tmp_path, (
        "from cryptography.hazmat.primitives.asymmetric import ed25519\n"
        "clave = ed25519.Ed25519PublicKey.from_public_bytes(datos)\n"
    ))

    assert hallazgos == []


def test_nombrar_una_curva_sin_usarla_no_es_hallazgo(tmp_path):
    hallazgos = _escanear(tmp_path, (
        "from cryptography.hazmat.primitives.asymmetric import ec\n"
        "CURVA = ec.SECP256R1()\n"
    ))
    assert hallazgos == []


# --- Diffie-Hellman ---

def test_detecta_diffie_hellman_una_sola_vez(tmp_path):
    hallazgos = _escanear(tmp_path, (
        "from cryptography.hazmat.primitives.asymmetric import dh\n"
        "parametros = dh.generate_parameters(generator=2, key_size=2048)\n"
        "clave = parametros.generate_private_key()\n"
    ))

    assert [h.rule_id for h in hallazgos] == ["crypto.pqc.dh"]
    assert hallazgos[0].line == 2
    assert hallazgos[0].metadata["algorithm"] == "DH"


def test_detecta_diffie_hellman_con_parametros_manuales(tmp_path):
    hallazgos = _escanear(tmp_path, (
        "from cryptography.hazmat.primitives.asymmetric import dh\n"
        "numeros = dh.DHParameterNumbers(p=23, g=5)\n"
    ))
    assert [h.rule_id for h in hallazgos] == ["crypto.pqc.dh"]


# --- AES (Grover) e inventario ---

AESGCM_IMPORT = "from cryptography.hazmat.primitives.ciphers.aead import AESGCM\n"
ALGORITHMS_IMPORT = "from cryptography.hazmat.primitives.ciphers import algorithms\n"


def test_aes_128_es_severidad_baja(tmp_path):
    hallazgos = _escanear(tmp_path, AESGCM_IMPORT + "clave = AESGCM.generate_key(bit_length=128)\n")

    assert [h.rule_id for h in hallazgos] == ["crypto.pqc.aes-128"]
    assert hallazgos[0].severity == Severity.LOW


def test_aes_128_con_el_tamano_por_posicion(tmp_path):
    hallazgos = _escanear(tmp_path, AESGCM_IMPORT + "clave = AESGCM.generate_key(128)\n")
    assert [h.rule_id for h in hallazgos] == ["crypto.pqc.aes-128"]


def test_aes_256_va_al_inventario(tmp_path):
    hallazgos = _escanear(tmp_path, AESGCM_IMPORT + "clave = AESGCM.generate_key(bit_length=256)\n")

    assert [h.rule_id for h in hallazgos] == ["crypto.pqc.inventory.aes"]
    assert hallazgos[0].severity == Severity.INFO
    assert hallazgos[0].metadata["algorithm"] == "AES-256"


def test_aes_con_tamano_en_variable_va_al_inventario_sin_tamano(tmp_path):
    hallazgos = _escanear(tmp_path, AESGCM_IMPORT + "clave = AESGCM.generate_key(bit_length=TAMANO)\n")

    assert hallazgos[0].severity == Severity.INFO
    assert hallazgos[0].metadata["algorithm"] == "AES"


def test_clases_aes128_y_aes256_de_algorithms(tmp_path):
    hallazgos = _escanear(tmp_path, ALGORITHMS_IMPORT + (
        "a = algorithms.AES128(clave)\n"
        "b = algorithms.AES256(clave)\n"
    ))

    assert [(h.rule_id, h.severity) for h in hallazgos] == [
        ("crypto.pqc.aes-128", Severity.LOW),
        ("crypto.pqc.inventory.aes", Severity.INFO),
    ]


def test_aes_generico_va_al_inventario(tmp_path):
    hallazgos = _escanear(tmp_path, ALGORITHMS_IMPORT + "cifrado = algorithms.AES(clave)\n")

    assert [h.rule_id for h in hallazgos] == ["crypto.pqc.inventory.aes"]
    assert hallazgos[0].metadata["algorithm"] == "AES"


# --- Inventario: hashes, Argon2 y ChaCha20 ---

def test_hashlib_sha256_va_al_inventario(tmp_path):
    hallazgos = _escanear(tmp_path, (
        "import hashlib\n"
        "huella = hashlib.sha256(b'datos').hexdigest()\n"
    ))

    assert [h.rule_id for h in hallazgos] == ["crypto.pqc.inventory.hash"]
    assert hallazgos[0].severity == Severity.INFO
    assert hallazgos[0].metadata["algorithm"] == "SHA-256"


def test_sha3_importado_directamente(tmp_path):
    hallazgos = _escanear(tmp_path, (
        "from hashlib import sha3_256\n"
        "huella = sha3_256(b'datos')\n"
    ))
    assert hallazgos[0].metadata["algorithm"] == "SHA3-256"


def test_sha512_de_cryptography(tmp_path):
    hallazgos = _escanear(tmp_path, (
        "from cryptography.hazmat.primitives import hashes\n"
        "algoritmo = hashes.SHA512()\n"
    ))
    assert hallazgos[0].metadata["algorithm"] == "SHA-512"


def test_argon2_va_al_inventario(tmp_path):
    hallazgos = _escanear(tmp_path, (
        "from argon2 import PasswordHasher\n"
        "hasher = PasswordHasher()\n"
    ))

    assert [h.rule_id for h in hallazgos] == ["crypto.pqc.inventory.password-hash"]
    assert hallazgos[0].metadata["algorithm"] == "Argon2"


def test_chacha20_va_al_inventario(tmp_path):
    hallazgos = _escanear(tmp_path, (
        "from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305\n"
        "cifrador = ChaCha20Poly1305(clave)\n"
    ))
    assert [h.rule_id for h in hallazgos] == ["crypto.pqc.inventory.chacha20"]


def test_md5_y_sha1_no_son_de_este_modulo(tmp_path):
    hallazgos = _escanear(tmp_path, (
        "import hashlib\n"
        "a = hashlib.md5(b'x')\n"
        "b = hashlib.sha1(b'x')\n"
    ))
    assert hallazgos == []


# --- Otras librerías: pycryptodome, rsa y ecdsa (y DSA) ---

def test_detecta_dsa_de_cryptography(tmp_path):
    hallazgos = _escanear(tmp_path, (
        "from cryptography.hazmat.primitives.asymmetric import dsa\n"
        "clave = dsa.generate_private_key(key_size=2048)\n"
    ))

    assert [h.rule_id for h in hallazgos] == ["crypto.pqc.dsa-keygen"]
    assert hallazgos[0].severity == Severity.MEDIUM


def test_pycryptodome_rsa_ecc_y_dsa(tmp_path):
    hallazgos = _escanear(tmp_path, (
        "from Crypto.PublicKey import RSA, ECC, DSA\n"
        "a = RSA.generate(2048)\n"
        "b = ECC.generate(curve='P-256')\n"
        "c = DSA.generate(2048)\n"
    ))

    assert [h.rule_id for h in hallazgos] == [
        "crypto.pqc.rsa-keygen",
        "crypto.pqc.ec-keygen",
        "crypto.pqc.dsa-keygen",
    ]


def test_pycryptodome_aes_va_al_inventario(tmp_path):
    hallazgos = _escanear(tmp_path, (
        "from Crypto.Cipher import AES\n"
        "cifrador = AES.new(clave, AES.MODE_GCM)\n"
    ))

    assert [h.rule_id for h in hallazgos] == ["crypto.pqc.inventory.aes"]


def test_libreria_rsa(tmp_path):
    hallazgos = _escanear(tmp_path, (
        "import rsa\n"
        "publica, privada = rsa.newkeys(2048)\n"
    ))

    assert [h.rule_id for h in hallazgos] == ["crypto.pqc.rsa-keygen"]


def test_libreria_ecdsa(tmp_path):
    hallazgos = _escanear(tmp_path, (
        "from ecdsa import SigningKey, NIST256p\n"
        "clave = SigningKey.generate(curve=NIST256p)\n"
    ))

    assert [h.rule_id for h in hallazgos] == ["crypto.pqc.ecdsa"]


def test_rsa_de_cryptography_no_se_confunde_con_la_libreria_rsa(tmp_path):
    hallazgos = _escanear(tmp_path, (
        "from cryptography.hazmat.primitives.asymmetric import rsa\n"
        "rsa.newkeys(2048)\n"
    ))
    assert hallazgos == []


# --- Seguridad: el repo escaneado no es de confianza ---

def test_no_sigue_enlaces_a_archivos_de_afuera_del_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    afuera = tmp_path / "privado.py"
    afuera.write_text("import rsa\nrsa.newkeys(2048)\n")
    (repo / "enlace.py").symlink_to(afuera)

    assert scan_pqc(str(repo)) == []


def test_no_sigue_carpetas_enlazadas_a_afuera_del_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    afuera = tmp_path / "afuera"
    afuera.mkdir()
    (afuera / "privado.py").write_text("import rsa\nrsa.newkeys(2048)\n")
    (repo / "carpeta").symlink_to(afuera, target_is_directory=True)

    assert scan_pqc(str(repo)) == []


def test_el_snippet_no_muestra_claves_escritas_en_el_codigo(tmp_path):
    hallazgos = _escanear(tmp_path, (
        "from Crypto.Cipher import AES\n"
        "cifrador = AES.new(b'clave-super-secreta', AES.MODE_GCM, nonce='otro-secreto')\n"
    ))

    snippet = hallazgos[0].snippet
    assert "clave-super-secreta" not in snippet
    assert "otro-secreto" not in snippet
    assert snippet == "AES.new('***', AES.MODE_GCM, nonce='***')"


def test_el_snippet_largo_se_recorta(tmp_path):
    hallazgos = _escanear(tmp_path, (
        "import rsa\n"
        "rsa.newkeys(" + " + ".join(["tamano"] * 100) + ")\n"
    ))

    assert len(hallazgos[0].snippet) <= 201
    assert hallazgos[0].snippet.endswith("…")


# --- JavaScript ---

def _escanear_js(tmp_path, codigo, nombre="app.js"):
    (tmp_path / nombre).write_text(codigo)
    return scan_pqc(str(tmp_path))


def test_js_detecta_claves_rsa(tmp_path):
    hallazgos = _escanear_js(tmp_path, (
        "const crypto = require('crypto');\n"
        "const par = crypto.generateKeyPairSync('rsa', { modulusLength: 2048 });\n"
    ))

    assert [h.rule_id for h in hallazgos] == ["crypto.pqc.rsa-keygen"]
    assert hallazgos[0].line == 2
    assert hallazgos[0].file_path == "app.js"


def test_js_detecta_claves_de_curva_eliptica_en_varias_lineas(tmp_path):
    hallazgos = _escanear_js(tmp_path, (
        "const { privateKey } = crypto.generateKeyPairSync(\n"
        "  \"ec\",\n"
        "  { namedCurve: 'P-256' },\n"
        ");\n"
    ))
    assert [h.rule_id for h in hallazgos] == ["crypto.pqc.ec-keygen"]


def test_js_detecta_ecdh_y_diffie_hellman(tmp_path):
    hallazgos = _escanear_js(tmp_path, (
        "const a = crypto.createECDH('prime256v1');\n"
        "const b = crypto.createDiffieHellman(2048);\n"
    ))
    assert [h.rule_id for h in hallazgos] == ["crypto.pqc.ecdh", "crypto.pqc.dh"]


def test_js_tipo_de_clave_sin_riesgo_cuantico_conocido_no_es_hallazgo(tmp_path):
    hallazgos = _escanear_js(tmp_path, "crypto.generateKeyPairSync('ml-dsa-65');\n")
    assert hallazgos == []


def test_js_clave_ec_que_firma_es_ecdsa(tmp_path):
    hallazgos = _escanear_js(tmp_path, (
        "const { privateKey } = crypto.generateKeyPairSync('ec', { namedCurve: 'P-256' });\n"
        "const firma = crypto.sign('sha256', datos, privateKey);\n"
    ))
    assert [(h.rule_id, h.line) for h in hallazgos] == [("crypto.pqc.ecdsa", 1)]


def test_js_clave_ec_con_create_sign_es_ecdsa(tmp_path):
    hallazgos = _escanear_js(tmp_path, (
        "const { privateKey } = crypto.generateKeyPairSync('ec', { namedCurve: 'P-256' });\n"
        "const firmador = crypto.createSign('SHA256');\n"
    ))
    assert [h.rule_id for h in hallazgos] == ["crypto.pqc.ecdsa"]


def test_js_clave_ec_sin_firmar_sigue_siendo_de_uso_indefinido(tmp_path):
    hallazgos = _escanear_js(tmp_path, "crypto.generateKeyPairSync('ec', { namedCurve: 'P-256' });\n")
    assert [h.rule_id for h in hallazgos] == ["crypto.pqc.ec-keygen"]


def test_js_firmar_en_un_comentario_no_cambia_el_uso(tmp_path):
    hallazgos = _escanear_js(tmp_path, (
        "crypto.generateKeyPairSync('ec', { namedCurve: 'P-256' });\n"
        "// después: crypto.sign('sha256', datos, clave)\n"
    ))
    assert [h.rule_id for h in hallazgos] == ["crypto.pqc.ec-keygen"]


def test_js_firmar_no_convierte_en_ecdsa_una_clave_rsa(tmp_path):
    hallazgos = _escanear_js(tmp_path, (
        "crypto.generateKeyPairSync('rsa', { modulusLength: 3072 });\n"
        "crypto.sign('sha256', datos, clave);\n"
    ))
    assert [h.rule_id for h in hallazgos] == ["crypto.pqc.rsa-keygen"]


def test_js_detecta_ed25519_y_x25519(tmp_path):
    hallazgos = _escanear_js(tmp_path, (
        "const firma = crypto.generateKeyPairSync('ed25519');\n"
        "const acuerdo = crypto.generateKeyPairSync('x25519');\n"
    ))
    assert [h.rule_id for h in hallazgos] == ["crypto.pqc.eddsa", "crypto.pqc.ecdh"]


def test_js_aes_128_y_aes_256(tmp_path):
    hallazgos = _escanear_js(tmp_path, (
        "const a = crypto.createCipheriv('aes-128-gcm', clave, iv);\n"
        "const b = crypto.createCipheriv('AES-256-GCM', clave, iv);\n"
    ))

    assert [(h.rule_id, h.severity) for h in hallazgos] == [
        ("crypto.pqc.aes-128", Severity.LOW),
        ("crypto.pqc.inventory.aes", Severity.INFO),
    ]


def test_js_hashes_seguros_van_al_inventario_y_md5_no(tmp_path):
    hallazgos = _escanear_js(tmp_path, (
        "const a = crypto.createHash('sha256');\n"
        "const b = crypto.createHash('md5');\n"
    ))

    assert [h.rule_id for h in hallazgos] == ["crypto.pqc.inventory.hash"]
    assert hallazgos[0].metadata["algorithm"] == "SHA-256"


def test_js_ignora_comentarios_y_conserva_los_numeros_de_linea(tmp_path):
    hallazgos = _escanear_js(tmp_path, (
        "// crypto.generateKeyPairSync('rsa')\n"
        "/* crypto.createECDH('prime256v1');\n"
        "   crypto.createDiffieHellman(2048); */\n"
        "const url = 'https://ejemplo.com'; crypto.createECDH('prime256v1');\n"
    ))

    assert [h.rule_id for h in hallazgos] == ["crypto.pqc.ecdh"]
    assert hallazgos[0].line == 4


def test_js_el_snippet_no_incluye_la_clave(tmp_path):
    hallazgos = _escanear_js(tmp_path, (
        "crypto.createCipheriv('aes-128-gcm', 'clave-super-secreta', iv);\n"
    ))
    assert "clave-super-secreta" not in hallazgos[0].snippet


def test_js_tambien_escanea_typescript(tmp_path):
    hallazgos = _escanear_js(tmp_path, "crypto.createECDH('prime256v1');\n", nombre="app.ts")
    assert [h.file_path for h in hallazgos] == ["app.ts"]
