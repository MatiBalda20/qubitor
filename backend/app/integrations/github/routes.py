"""Endpoints del Módulo E para listar y conectar los repos de GitHub del usuario.

El token OAuth de GitHub se pide a Clerk en cada request y se usa solo del
lado del servidor: ninguna respuesta lo incluye. Conectar un repo crea la fila
en `repositories` de la organización del usuario; el primer escaneo se lanza
con el endpoint existente `POST /repositories/{id}/scans` (Módulo A).
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.auth import CurrentUser, get_current_user
from app.api.schemas import RepositoryOut, repository_out
from app.integrations.github.clerk import get_github_token
from app.integrations.github.client import GitHubClient, GitHubRepo, is_valid_full_name
from app.integrations.github.errors import GitHubError
from app.integrations.github.settings import private_repos_enabled
from app.models.database import get_db
from app.models.models import Repository, User
from app.worker.clone import MAX_REPO_BYTES

router = APIRouter(prefix="/github", tags=["github"])


class GitHubRepoOut(BaseModel):
    full_name: str
    url: str
    private: bool
    description: str | None
    default_branch: str
    size_bytes: int
    updated_at: str | None
    archived: bool
    connected: bool
    # Si se puede conectar y, si no, por qué (para mostrarlo en la pantalla).
    connectable: bool
    reason: str | None


class GitHubRepoPageOut(BaseModel):
    items: list[GitHubRepoOut]
    page: int
    has_next: bool


class ConnectGitHubRepoIn(BaseModel):
    full_name: str = Field(max_length=201)


def get_github_client(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)) -> GitHubClient:
    clerk_user_id = db.scalar(select(User.clerk_user_id).where(User.id == user.user_id))
    try:
        return GitHubClient(get_github_token(clerk_user_id or ""))
    except GitHubError as error:
        raise _http_error(error) from None


@router.get("/repositories", response_model=GitHubRepoPageOut)
def list_github_repositories(
    page: int = Query(1, ge=1, le=1000),
    per_page: int = Query(30, ge=1, le=100),
    user: CurrentUser = Depends(get_current_user),
    github: GitHubClient = Depends(get_github_client),
    db: Session = Depends(get_db),
):
    """Repos de GitHub del usuario, marcando cuáles ya conectó su organización."""
    try:
        result = github.list_repositories(page=page, per_page=per_page)
    except GitHubError as error:
        raise _http_error(error) from None

    connected = set(
        db.scalars(select(func.lower(Repository.url)).where(Repository.organization_id == user.organization_id))
    )
    return GitHubRepoPageOut(
        items=[_repo_out(repo, repo.url.lower() in connected) for repo in result.items],
        page=result.page,
        has_next=result.has_next,
    )


@router.post("/repositories", response_model=RepositoryOut, status_code=status.HTTP_201_CREATED)
def connect_github_repository(
    body: ConnectGitHubRepoIn,
    response: Response,
    user: CurrentUser = Depends(get_current_user),
    github: GitHubClient = Depends(get_github_client),
    db: Session = Depends(get_db),
):
    """Conecta un repo de la cuenta de GitHub del usuario, validándolo contra GitHub."""
    if not is_valid_full_name(body.full_name):
        raise HTTPException(422, "El nombre del repositorio no es válido")
    try:
        repo = github.get_repository(body.full_name)
    except GitHubError as error:
        raise _http_error(error) from None
    reason = _not_connectable_reason(repo)
    if reason:
        raise HTTPException(422, reason)

    existing = db.scalar(
        select(Repository).where(
            Repository.organization_id == user.organization_id, func.lower(Repository.url) == repo.url.lower()
        )
    )
    if existing is not None:
        # Se actualiza quién lo conectó: su token es el que va a usar el worker si es privado.
        existing.is_private = repo.private
        existing.connected_by_user_id = user.user_id
        existing.default_branch = repo.default_branch
        db.commit()
        response.status_code = status.HTTP_200_OK
        return repository_out(existing)

    created = Repository(
        organization_id=user.organization_id,
        full_name=repo.full_name,
        url=repo.url,
        default_branch=repo.default_branch,
        is_private=repo.private,
        connected_by_user_id=user.user_id,
    )
    db.add(created)
    db.commit()
    return repository_out(created)


def _repo_out(repo: GitHubRepo, connected: bool) -> GitHubRepoOut:
    reason = _not_connectable_reason(repo)
    return GitHubRepoOut(
        full_name=repo.full_name,
        url=repo.url,
        private=repo.private,
        description=repo.description,
        default_branch=repo.default_branch,
        size_bytes=repo.size_bytes,
        updated_at=repo.updated_at,
        archived=repo.archived,
        connected=connected,
        connectable=reason is None,
        reason=reason,
    )


def _not_connectable_reason(repo: GitHubRepo) -> str | None:
    if not repo.can_read:
        return "Tu cuenta no tiene permiso de lectura sobre este repositorio"
    if repo.private and not private_repos_enabled():
        return "Los repositorios privados todavía no están habilitados en Qubitor"
    if repo.size_bytes > MAX_REPO_BYTES:
        return "El repositorio supera el límite de 50 MB"
    return None


def _http_error(error: GitHubError) -> HTTPException:
    headers = {"Retry-After": str(error.retry_after)} if error.retry_after is not None else None
    return HTTPException(error.status_code, error.message, headers=headers)
