"""domicilio interno y canal de pedido

Revision ID: e4a7c3f9b6d1
Revises: d2b8f5a1c9e7
Create Date: 2026-07-31 10:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e4a7c3f9b6d1'
down_revision: Union[str, None] = 'd2b8f5a1c9e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE rol_usuario ADD VALUE IF NOT EXISTS 'repartidor'")
    op.execute("ALTER TYPE estado_pedido ADD VALUE IF NOT EXISTS 'en_camino'")

    canal_pedido = sa.Enum(
        'mesa', 'domicilio_interno', 'rappi', 'didi', name='canal_pedido'
    )
    canal_pedido.create(op.get_bind(), checkfirst=True)

    # Pedido por domicilio no tiene mesa: mesa_id pasa a opcional y el
    # restaurante queda explícito en su propia columna (antes se derivaba
    # siempre del join con mesas).
    op.alter_column('pedidos', 'mesa_id', existing_type=sa.Integer(), nullable=True)
    op.add_column('pedidos', sa.Column('restaurante_id', sa.Integer(), nullable=True))
    op.execute(
        """
        UPDATE pedidos
        SET restaurante_id = mesas.restaurante_id
        FROM mesas
        WHERE pedidos.mesa_id = mesas.id
        """
    )
    op.alter_column('pedidos', 'restaurante_id', existing_type=sa.Integer(), nullable=False)
    op.create_foreign_key(
        'fk_pedidos_restaurante_id', 'pedidos', 'restaurantes', ['restaurante_id'], ['id']
    )

    op.add_column(
        'pedidos',
        sa.Column('canal', canal_pedido, nullable=False, server_default='mesa'),
    )
    op.alter_column('pedidos', 'canal', server_default=None)
    op.add_column('pedidos', sa.Column('direccion_entrega', sa.String(255), nullable=True))
    op.add_column('pedidos', sa.Column('telefono_entrega', sa.String(30), nullable=True))
    op.add_column('pedidos', sa.Column('repartidor_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_pedidos_repartidor_id', 'pedidos', 'usuarios', ['repartidor_id'], ['id']
    )
    op.add_column('pedidos', sa.Column('repartidor_lat', sa.Float(), nullable=True))
    op.add_column('pedidos', sa.Column('repartidor_lng', sa.Float(), nullable=True))
    op.add_column(
        'pedidos',
        sa.Column('repartidor_actualizado_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    # ALTER TYPE ADD VALUE no se puede revertir en Postgres (ver
    # 8d3a975d320e) — mismo motivo, no se implementa downgrade completo.
    raise NotImplementedError("No se puede quitar un valor de un enum en Postgres")
