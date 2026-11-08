import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app.api import auth

ISSUER = "https://test.clerk.example"


class _Clave:
    def __init__(self, key):
        self.key = key


class _JwksFalso:
    def __init__(self, public_key):
        self.public_key = public_key

    def get_signing_key_from_jwt(self, token):
        return _Clave(self.public_key)


@pytest.fixture
def clave():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(autouse=True)
def entorno(monkeypatch, clave):
    monkeypatch.setenv("CLERK_ISSUER", ISSUER)
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173")
    monkeypatch.setattr(auth, "_jwks_client", lambda issuer: _JwksFalso(clave.public_key()))


def token(clave, **cambios):
    ahora = int(time.time())
    claims = {"iss": ISSUER, "sub": "user_1", "iat": ahora, "exp": ahora + 60, "azp": "http://localhost:5173"}
    claims.update(cambios)
    claims = {k: v for k, v in claims.items() if v is not None}
    return jwt.encode(claims, clave, algorithm="RS256")


def test_token_valido(clave):
    assert auth.verify_token(token(clave))["sub"] == "user_1"


def test_token_vencido(clave):
    with pytest.raises(jwt.ExpiredSignatureError):
        auth.verify_token(token(clave, exp=int(time.time()) - 60))


def test_token_de_otro_emisor(clave):
    with pytest.raises(jwt.InvalidIssuerError):
        auth.verify_token(token(clave, iss="https://otro.clerk.example"))


def test_token_firmado_con_otra_clave():
    otra = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with pytest.raises(jwt.InvalidSignatureError):
        auth.verify_token(token(otra))


def test_token_sin_firma_rsa_se_rechaza():
    falso = jwt.encode({"iss": ISSUER, "sub": "x", "iat": 1, "exp": 9999999999}, "secreto", algorithm="HS256")
    with pytest.raises(jwt.InvalidAlgorithmError):
        auth.verify_token(falso)


def test_token_emitido_para_otro_sitio(clave):
    with pytest.raises(jwt.InvalidTokenError, match="Origen"):
        auth.verify_token(token(clave, azp="https://malicioso.example"))


def test_token_sin_sub(clave):
    with pytest.raises(jwt.MissingRequiredClaimError):
        auth.verify_token(token(clave, sub=None))


@pytest.mark.parametrize(
    ("claims", "esperada"),
    [
        ({"sub": "user_1", "org_id": "org_1"}, "org_1"),  # formato v1
        ({"sub": "user_1", "o": {"id": "org_2"}}, "org_2"),  # formato v2
        ({"sub": "user_1"}, "user:user_1"),  # sin organización activa
    ],
)
def test_organizacion_del_token(claims, esperada):
    assert auth.organization_key(claims) == esperada
