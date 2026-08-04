"""categorias de menu

Revision ID: c7f3a0e1d8b4
Revises: a1c4e9f2b7d3
Create Date: 2026-07-30 20:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c7f3a0e1d8b4'
down_revision: Union[str, None] = 'a1c4e9f2b7d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "categorias_menu",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("restaurante_id", sa.Integer(), sa.ForeignKey("restaurantes.id"), nullable=False),
        sa.Column("nombre", sa.String(length=60), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("restaurante_id", "nombre", name="uq_categoria_restaurante_nombre"),
    )
    op.create_table(
        "menu_item_categoria",
        sa.Column("menu_item_id", sa.Integer(), sa.ForeignKey("menu.id"), primary_key=True),
        sa.Column(
            "categoria_id", sa.Integer(), sa.ForeignKey("categorias_menu.id"), primary_key=True
        ),
    )


def downgrade() -> None:
    op.drop_table("menu_item_categoria")
    op.drop_table("categorias_menu")
