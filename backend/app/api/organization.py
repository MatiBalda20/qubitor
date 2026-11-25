"""La organización del usuario: quién es, qué rol tiene y quiénes son los miembros (Módulo A).

Las invitaciones y los cambios de rol se hacen desde Clerk (componente
OrganizationSwitcher del frontend); acá solo se leen.
"""

import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import PERSONAL_PREFIX, CurrentUser, get_current_user
from app.api.clerk_users import fetch_profiles
from app.models.database import get_db
from app.models.models import Membership, MemberRole, Organization, User

router = APIRouter()


class Permissions(BaseModel):
    connect_repositories: bool
    start_scans: bool
    update_findings: bool


class OrganizationOut(BaseModel):
    id: str
    name: str
    personal: bool


class MeOut(BaseModel):
    user_id: str
    role: Literal["admin", "member"]
    organization: OrganizationOut
    permissions: Permissions


class MemberOut(BaseModel):
    user_id: str
    name: str | None
    image_url: str | None
    role: Literal["admin", "member"]
    joined_at: datetime | None
    last_seen_at: datetime | None
    is_you: bool


def permissions_for(role: MemberRole) -> Permissions:
    """Qué puede hacer cada rol. La API lo aplica; el frontend lo usa para no ofrecer lo que no se puede."""
    return Permissions(connect_repositories=role == MemberRole.ADMIN, start_scans=True, update_findings=True)


@router.get("/me", response_model=MeOut)
def get_me(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    organization = db.get(Organization, user.organization_id)
    return MeOut(
        user_id=str(user.user_id),
        role=user.role.value,
        organization=_organization_out(organization),
        permissions=permissions_for(user.role),
    )


@router.get("/organization/members", response_model=list[MemberOut])
def list_members(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """Miembros de la organización activa que ya usaron Qubitor: primero los admin, después por actividad."""
    rows = db.execute(
        select(Membership, User.clerk_user_id)
        .join(User, User.id == Membership.user_id)
        .where(Membership.organization_id == user.organization_id)
    ).all()
    profiles = fetch_profiles([clerk_id for _, clerk_id in rows])
    members = [_member_out(membership, profiles.get(clerk_id), user.user_id) for membership, clerk_id in rows]
    return sorted(members, key=lambda m: (m.role != "admin", -(m.last_seen_at.timestamp() if m.last_seen_at else 0)))


def _organization_out(organization: Organization) -> OrganizationOut:
    return OrganizationOut(
        id=str(organization.id),
        name=organization.name,
        personal=organization.clerk_org_id.startswith(PERSONAL_PREFIX),
    )


def _member_out(membership: Membership, profile, current_user_id: uuid.UUID) -> MemberOut:
    return MemberOut(
        user_id=str(membership.user_id),
        name=profile.name if profile else None,
        image_url=profile.image_url if profile else None,
        role=membership.role.value,
        joined_at=membership.created_at,
        last_seen_at=membership.last_seen_at,
        is_you=membership.user_id == current_user_id,
    )
