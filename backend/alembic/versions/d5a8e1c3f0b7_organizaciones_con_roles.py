"""organizaciones_con_roles

Módulo A: organizaciones con varios miembros y roles. Cada usuario puede
pertenecer a varias organizaciones de Clerk, con el rol que Clerk le da en cada
una (admin o member). `users.organization_id` sigue siendo la organización
activa en la sesión.

Revision ID: d5a8e1c3f0b7
Revises: b41d7e2a9c55
Create Date: 2026-11-17 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'd5a8e1c3f0b7'
down_revision: Union[str, Sequence[str], None] = 'b41d7e2a9c55'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'memberships',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('role', sa.Enum('admin', 'member', name='memberrole'), server_default='member', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'organization_id', name='uq_membership_user_org'),
    )
    op.create_index('ix_memberships_organization_id', 'memberships', ['organization_id'], unique=False)

    # Los usuarios que ya existen pasan a ser miembros de su organización actual.
    # En una organización personal son admin; en una de Clerk, member hasta su
    # próximo pedido, que trae el rol real en el token.
    op.execute("""
        INSERT INTO memberships (id, user_id, organization_id, role)
        SELECT gen_random_uuid(), u.id, u.organization_id,
               CASE WHEN o.clerk_org_id LIKE 'user:%%' THEN 'admin'::memberrole ELSE 'member'::memberrole END
        FROM users u JOIN organizations o ON o.id = u.organization_id
    """)

    # Igual que las demás tablas: sin políticas, solo la API (dueña de las tablas) accede.
    op.execute("ALTER TABLE memberships ENABLE ROW LEVEL SECURITY;")


def downgrade() -> None:
    op.drop_index('ix_memberships_organization_id', table_name='memberships')
    op.drop_table('memberships')
    sa.Enum(name='memberrole').drop(op.get_bind(), checkfirst=True)
