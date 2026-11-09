"""repos_privados_github

Módulo E: repos conectados desde la cuenta de GitHub del usuario. `is_private`
dice si hace falta un token para clonarlo y `connected_by_user_id`, de quién es
ese token (se pide a Clerk en el momento del clonado, nunca se guarda).

Revision ID: 9c2f1a7d3b10
Revises: 4e8bf93a60a1
Create Date: 2026-11-08 22:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '9c2f1a7d3b10'
down_revision: Union[str, Sequence[str], None] = '4e8bf93a60a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'repositories',
        sa.Column('is_private', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    )
    op.add_column('repositories', sa.Column('connected_by_user_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_repositories_connected_by_user_id',
        'repositories', 'users',
        ['connected_by_user_id'], ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('fk_repositories_connected_by_user_id', 'repositories', type_='foreignkey')
    op.drop_column('repositories', 'connected_by_user_id')
    op.drop_column('repositories', 'is_private')
