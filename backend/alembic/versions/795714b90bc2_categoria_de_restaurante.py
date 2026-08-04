"""categoria de restaurante

Revision ID: 795714b90bc2
Revises: 77eb7c817223
Create Date: 2026-07-30 18:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '795714b90bc2'
down_revision: Union[str, None] = '77eb7c817223'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("restaurantes", sa.Column("categoria", sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column("restaurantes", "categoria")
