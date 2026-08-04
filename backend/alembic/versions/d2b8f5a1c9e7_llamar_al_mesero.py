"""llamar al mesero

Revision ID: d2b8f5a1c9e7
Revises: c7f3a0e1d8b4
Create Date: 2026-07-30 21:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd2b8f5a1c9e7'
down_revision: Union[str, None] = 'c7f3a0e1d8b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "sesiones_mesa", sa.Column("llamada_mesero_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("sesiones_mesa", "llamada_mesero_at")
