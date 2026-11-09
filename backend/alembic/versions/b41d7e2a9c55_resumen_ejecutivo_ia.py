"""resumen_ejecutivo_ia

Módulo E: resumen ejecutivo de cada escaneo (estado general, tres riesgos
principales y prioridades), generado con Gemini o con el fallback heurístico.
Los campos del triage por hallazgo (`findings.ai_*`) ya existen desde la
migración inicial.

Revision ID: b41d7e2a9c55
Revises: 9c2f1a7d3b10
Create Date: 2026-11-08 23:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'b41d7e2a9c55'
down_revision: Union[str, Sequence[str], None] = '9c2f1a7d3b10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('scans', sa.Column('ai_summary', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('scans', 'ai_summary')
