"""ubicacion de restaurante

Revision ID: a1c4e9f2b7d3
Revises: 795714b90bc2
Create Date: 2026-07-30 19:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a1c4e9f2b7d3'
down_revision: Union[str, None] = '795714b90bc2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("restaurantes", sa.Column("latitud", sa.Float(), nullable=True))
    op.add_column("restaurantes", sa.Column("longitud", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("restaurantes", "longitud")
    op.drop_column("restaurantes", "latitud")
