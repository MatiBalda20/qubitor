"""Autenticación con Clerk (Módulo A).

Cada request trae el JWT de la sesión de Clerk. Se valida con las claves
públicas de Clerk (JWKS) y se obtiene el usuario, su organización activa y su
rol en ella; si es la primera vez que se ven, se crean en la base. Un usuario
sin organización activa en Clerk trabaja en una organización personal, donde
es admin.

Los roles los administra Clerk (invitaciones, alta y baja de miembros); la API
solo los lee del token en cada request:
- admin: todo, incluido conectar repositorios.
- member: ver, lanzar escaneos y marcar hallazgos.
"""

import logging
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import cors_origins
from app.models.database import get_db
from app.models.models import Membership, MemberRole, Organization, User

logger = logging.getLogger(__name__)

# Margen para diferencias de reloj entre Clerk y el servidor.
LEEWAY_SECONDS = 5

_DEMO_USER = "demo-user"
_DEMO_ORG = "demo-org"
PERSONAL_PREFIX = "user:"

# La fecha de última actividad se actualiza como mucho cada tanto, para no
# escribir en la base en cada request.
LAST_SEEN_EVERY = timedelta(minutes=5)


@dataclass(frozen=True)
class CurrentUser:
    user_id: uuid.UUID
    organization_id: uuid.UUID
    role: MemberRole = MemberRole.ADMIN

    @property
    def is_admin(self) -> bool:
        return self.role == MemberRole.ADMIN


def clerk_issuer() -> str | None:
    return os.getenv("CLERK_ISSUER", "").rstrip("/") or None


def auth_disabled() -> bool:
    """Solo para desarrollo local con el frontend en modo demo (sin Clerk).

    En Render (que define RENDER) se ignora: con AUTH_DISABLED=true cualquier
    pedido sin token entraría como admin de la organización demo (QUB-13).
    """
    if os.getenv("AUTH_DISABLED", "").lower() != "true":
        return False
    if os.getenv("RENDER"):
        logger.error("AUTH_DISABLED=true se ignora en Render: la autenticación sigue activa")
        return False
    return True


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
    return org_id or f"{PERSONAL_PREFIX}{claims['sub']}"


def organization_role(claims: dict) -> MemberRole:
    """Rol en la organización activa: org_role (v1) u o.rol (v2).

    Clerk lo manda como "org:admin", "admin" u otros roles propios: solo admin
    da permisos de administración. Sin organización activa, el usuario está en
    la suya personal y es admin.
    """
    if not (claims.get("org_id") or (claims.get("o") or {}).get("id")):
        return MemberRole.ADMIN
    raw = claims.get("org_role") or (claims.get("o") or {}).get("rol") or ""
    return MemberRole.ADMIN if str(raw).removeprefix("org:") == "admin" else MemberRole.MEMBER


def organization_name(claims: dict) -> str | None:
    """Nombre corto (slug) de la organización de Clerk, si viene en el token."""
    return claims.get("org_slug") or (claims.get("o") or {}).get("slg") or None


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
    return ensure_user(
        db, claims["sub"], organization_key(claims), organization_role(claims), organization_name(claims)
    )


def require_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Para las acciones que solo puede hacer un admin de la organización."""
    if not user.is_admin:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Solo un administrador de la organización puede hacer esto"
        )
    return user


def ensure_user(
    db: Session,
    clerk_user_id: str,
    clerk_org_id: str,
    role: MemberRole = MemberRole.ADMIN,
    org_name: str | None = None,
) -> CurrentUser:
    """Devuelve el usuario, su organización y su rol, creándolos si es la primera vez.

    El rol se toma siempre del token: si un admin cambia el rol de alguien en
    Clerk, se aplica en el próximo pedido de esa persona.
    """
    for _ in range(2):
        try:
            organization = db.scalar(select(Organization).where(Organization.clerk_org_id == clerk_org_id))
            if organization is None:
                organization = Organization(name=org_name or _default_name(clerk_org_id), clerk_org_id=clerk_org_id)
                db.add(organization)
                db.flush()
            elif org_name and organization.name != org_name:
                organization.name = org_name
            user = db.scalar(select(User).where(User.clerk_user_id == clerk_user_id))
            if user is None:
                user = User(clerk_user_id=clerk_user_id, organization_id=organization.id)
                db.add(user)
                db.flush()
            elif user.organization_id != organization.id:
                # El usuario cambió de organización activa en Clerk.
                user.organization_id = organization.id
            _upsert_membership(db, user.id, organization.id, role)
            db.commit()
            return CurrentUser(user_id=user.id, organization_id=organization.id, role=role)
        except IntegrityError:
            # Otro request lo creó al mismo tiempo: se vuelve a leer.
            db.rollback()
    raise HTTPException(status.HTTP_409_CONFLICT, "No se pudo registrar el usuario, reintentá")


def _upsert_membership(db: Session, user_id: uuid.UUID, organization_id: uuid.UUID, role: MemberRole) -> None:
    membership = db.scalar(
        select(Membership).where(Membership.user_id == user_id, Membership.organization_id == organization_id)
    )
    now = datetime.now(timezone.utc)
    if membership is None:
        db.add(Membership(user_id=user_id, organization_id=organization_id, role=role, last_seen_at=now))
        return
    if membership.role != role:
        membership.role = role
    if membership.last_seen_at is None or now - membership.last_seen_at > LAST_SEEN_EVERY:
        membership.last_seen_at = now


def _default_name(clerk_org_id: str) -> str:
    return "Personal" if clerk_org_id.startswith(PERSONAL_PREFIX) else clerk_org_id


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, detail, headers={"WWW-Authenticate": "Bearer"})
