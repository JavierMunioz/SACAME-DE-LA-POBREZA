"""prefactura de domicilio y estado pagado

Revision ID: f8b2d6e1a4c7
Revises: e4a7c3f9b6d1
Create Date: 2026-07-31 16:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f8b2d6e1a4c7'
down_revision: Union[str, None] = 'e4a7c3f9b6d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # La prefactura de un domicilio no tiene mesa (mismo motivo que
    # pedidos.mesa_id en e4a7c3f9b6d1): la mesa deja de ser la única
    # forma de ubicar el restaurante de una factura.
    op.alter_column('facturas', 'mesa_id', existing_type=sa.Integer(), nullable=True)
    op.add_column('facturas', sa.Column('restaurante_id', sa.Integer(), nullable=True))
    op.execute(
        """
        UPDATE facturas
        SET restaurante_id = mesas.restaurante_id
        FROM mesas
        WHERE facturas.mesa_id = mesas.id
        """
    )
    op.alter_column('facturas', 'restaurante_id', existing_type=sa.Integer(), nullable=False)
    op.create_foreign_key(
        'fk_facturas_restaurante_id', 'facturas', 'restaurantes', ['restaurante_id'], ['id']
    )

    op.add_column(
        'facturas', sa.Column('pagado', sa.Boolean(), nullable=False, server_default=sa.false())
    )
    op.alter_column('facturas', 'pagado', server_default=None)
    # Facturas existentes son todas de mesa, generadas al cerrar la mesa
    # (se asume cobrada en ese momento, como siempre funcionó) — se
    # backfillean como pagadas para no dejarlas "pendientes de cobro" por
    # error de una columna que no existía cuando se crearon.
    op.execute("UPDATE facturas SET pagado = true")
    op.add_column(
        'facturas', sa.Column('pagado_at', sa.DateTime(timezone=True), nullable=True)
    )
    op.execute("UPDATE facturas SET pagado_at = created_at")


def downgrade() -> None:
    op.drop_column('facturas', 'pagado_at')
    op.drop_column('facturas', 'pagado')
    op.drop_constraint('fk_facturas_restaurante_id', 'facturas', type_='foreignkey')
    op.drop_column('facturas', 'restaurante_id')
    op.alter_column('facturas', 'mesa_id', existing_type=sa.Integer(), nullable=False)
