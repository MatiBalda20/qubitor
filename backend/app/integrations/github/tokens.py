"""Token de GitHub para clonar un repo privado desde el scan-worker (Módulo E).

El trabajo de la cola solo lleva `scan_id` y la URL: el token no viaja por
Redis ni se guarda en la base. El worker lo pide a Clerk en el momento del
clonado, con el usuario que conectó el repo, y lo descarta al terminar.
"""

import logging
import uuid
from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.github.clerk import get_github_token
from app.integrations.github.errors import GitHubNotLinked, GitHubUnavailable
from app.integrations.github.settings import private_repos_enabled
from app.worker.clone import CloneError, CloneRejected

logger = logging.getLogger(__name__)


def clone_token_for_scan(scan_id: str, session_factory: Callable[[], Session] | None = None) -> str | None:
    """Token para clonar el repo del escaneo, o None si el repo es público.

    Lanza CloneRejected si el repo es privado y no hay forma de obtener acceso
    (no tiene sentido reintentar), y CloneError si Clerk no respondió.
    """
    if not private_repos_enabled():
        return None
    try:
        key = uuid.UUID(scan_id)
    except ValueError:
        return None

    if session_factory is None:
        from app.models.database import SessionLocal

        session_factory = SessionLocal

    from app.models.models import Repository, Scan, User

    with session_factory() as session:
        row = session.execute(
            select(Repository.is_private, User.clerk_user_id)
            .select_from(Scan)
            .join(Repository, Scan.repository_id == Repository.id)
            .outerjoin(User, Repository.connected_by_user_id == User.id)
            .where(Scan.id == key)
        ).first()

    if row is None or not row.is_private:
        return None
    if not row.clerk_user_id:
        raise CloneRejected("El repositorio privado no tiene un usuario con acceso: volvé a conectarlo")
    try:
        return get_github_token(row.clerk_user_id)
    except GitHubNotLinked:
        raise CloneRejected("Quien conectó el repositorio privado ya no tiene GitHub vinculado: volvé a conectarlo") from None
    except GitHubUnavailable as error:
        logger.warning("Escaneo %s: no se pudo obtener el token de GitHub: %s", scan_id, error)
        raise CloneError("No se pudo obtener el acceso al repositorio privado") from None
