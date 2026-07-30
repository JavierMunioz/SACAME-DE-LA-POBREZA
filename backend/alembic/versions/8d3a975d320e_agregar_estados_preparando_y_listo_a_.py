"""agregar estados preparando y listo a pedidos

Revision ID: 8d3a975d320e
Revises: 072d96094a7e
Create Date: 2026-07-30 00:48:45.877808

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8d3a975d320e'
down_revision: Union[str, None] = '072d96094a7e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE estado_pedido ADD VALUE IF NOT EXISTS 'preparando'")
    op.execute("ALTER TYPE estado_pedido ADD VALUE IF NOT EXISTS 'listo'")


def downgrade() -> None:
    # Postgres no soporta DROP VALUE de un enum. Revertir esto requiere
    # recrear el tipo desde cero (migrar filas existentes primero), no se
    # implementa porque no hay necesidad práctica de bajar esta migración.
    raise NotImplementedError("No se puede quitar un valor de un enum en Postgres")
