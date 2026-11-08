"""Autenticación con Clerk (Módulo A).

Cada request trae el JWT de la sesión de Clerk. Se valida con las claves
públicas de Clerk (JWKS) y se obtiene el usuario y su organización; si es la
primera vez que se ven, se crean en la base. Un usuario sin organización activa
en Clerk trabaja en una organización personal.
"""

import os
import uuid
from dataclasses import dataclass
from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import cors_origins
from app.models.database import get_db
from app.models.models import Organization, User

# Margen para diferencias de reloj entre Clerk y el servidor.
LEEWAY_SECONDS = 5

_DEMO_USER = "demo-user"
_DEMO_ORG = "demo-org"


@dataclass(frozen=True)
class CurrentUser:
    user_id: uuid.UUID
    organization_id: uuid.UUID


def clerk_issuer() -> str | None:
    return os.getenv("CLERK_ISSUER", "").rstrip("/") or None


def auth_disabled() -> bool:
    """Solo para desarrollo local con el frontend en modo demo (sin Clerk)."""
    return os.getenv("AUTH_DISABLED", "").lower() == "true"


@lru_cache
def _jwks_client(issuer: str) -> jwt.PyJWKClient:
    # Cachea las claves: no se consulta a Clerk en cada request.
    return jwt.PyJWKClient(f"{issuer}/.well-known/jwks.json", cache_keys=True, lifespan=3600)


def verify_token(token: str) -> dict:
    """Valida firma, vencimiento, emisor y origen del token. Lanza si no es válido."""
    issuer = clerk_issuer()
    key = _jwks_client(issuer).get_signing_key_from_jwt(token).key
    claims = jwt.decode(
        token,
        key,
        algorithms=["RS256"],
        issuer=issuer,
        leeway=LEEWAY_SECONDS,
        options={"require": ["exp", "iat", "iss", "sub"]},
    )
    # azp es el origen que pidió el token: evita aceptar tokens emitidos para otro sitio.
    if claims.get("azp") and claims["azp"] not in cors_origins():
        raise jwt.InvalidTokenError("Origen del token no permitido")
    return claims


def organization_key(claims: dict) -> str:
    """Organización activa en Clerk (formato v1 u o.id del v2) o una personal."""
    org_id = claims.get("org_id") or (claims.get("o") or {}).get("id")
    return org_id or f"user:{claims['sub']}"


def get_current_user(request: Request, db: Session = Depends(get_db)) -> CurrentUser:
    if auth_disabled():
        return ensure_user(db, _DEMO_USER, _DEMO_ORG)
    if clerk_issuer() is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "La autenticación no está configurada")

    scheme, _, token = request.headers.get("Authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise _unauthorized("Falta el token de sesión")
    try:
        claims = verify_token(token)
    except jwt.PyJWKClientConnectionError as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "No se pudo validar la sesión con Clerk") from error
    except jwt.PyJWTError as error:
        raise _unauthorized("La sesión no es válida o venció") from error
    return ensure_user(db, claims["sub"], organization_key(claims))


def ensure_user(db: Session, clerk_user_id: str, clerk_org_id: str) -> CurrentUser:
    """Devuelve el usuario y su organización, creándolos si es la primera vez."""
    for _ in range(2):
        try:
            organization = db.scalar(select(Organization).where(Organization.clerk_org_id == clerk_org_id))
            if organization is None:
                organization = Organization(name=clerk_org_id, clerk_org_id=clerk_org_id)
                db.add(organization)
                db.flush()
            user = db.scalar(select(User).where(User.clerk_user_id == clerk_user_id))
            if user is None:
                user = User(clerk_user_id=clerk_user_id, organization_id=organization.id)
                db.add(user)
            elif user.organization_id != organization.id:
                # El usuario cambió de organización activa en Clerk.
                user.organization_id = organization.id
            db.commit()
            return CurrentUser(user_id=user.id, organization_id=organization.id)
        except IntegrityError:
            # Otro request lo creó al mismo tiempo: se vuelve a leer.
            db.rollback()
    raise HTTPException(status.HTTP_409_CONFLICT, "No se pudo registrar el usuario, reintentá")


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, detail, headers={"WWW-Authenticate": "Bearer"})
