"""sesión de mesa: estados de mesa, check-in de reserva, sesiones_mesa

Revision ID: 79e4cc88656e
Revises: 8d3a975d320e
Create Date: 2026-07-30 02:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '79e4cc88656e'
down_revision: Union[str, None] = '8d3a975d320e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    estado_mesa = sa.Enum("libre", "ocupada", name="estado_mesa")
    estado_mesa.create(op.get_bind())
    op.add_column(
        "mesas",
        sa.Column("estado", estado_mesa, nullable=False, server_default="libre"),
    )

    op.execute("ALTER TYPE estado_reserva ADD VALUE IF NOT EXISTS 'expirada'")

    op.add_column("reservas", sa.Column("check_in_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "sesiones_mesa",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("mesa_id", sa.Integer(), sa.ForeignKey("mesas.id"), nullable=False),
        sa.Column("cliente_id", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=True),
        sa.Column("nombre_invitado", sa.String(length=80), nullable=True),
        sa.Column("reserva_id", sa.Integer(), sa.ForeignKey("reservas.id"), nullable=True),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("codigo_acceso", sa.String(length=4), nullable=False),
        sa.Column(
            "abierta_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("cerrada_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_sesiones_mesa_token", "sesiones_mesa", ["token"], unique=True
    )
    op.create_index(
        "uq_sesion_mesa_activa",
        "sesiones_mesa",
        ["mesa_id"],
        unique=True,
        postgresql_where=sa.text("cerrada_at IS NULL"),
    )

    op.add_column(
        "pedidos", sa.Column("sesion_mesa_id", sa.Integer(), sa.ForeignKey("sesiones_mesa.id"), nullable=True)
    )
    op.add_column("pedidos", sa.Column("nombre_invitado", sa.String(length=80), nullable=True))


def downgrade() -> None:
    op.drop_column("pedidos", "nombre_invitado")
    op.drop_column("pedidos", "sesion_mesa_id")
    op.drop_index("uq_sesion_mesa_activa", table_name="sesiones_mesa")
    op.drop_index("ix_sesiones_mesa_token", table_name="sesiones_mesa")
    op.drop_table("sesiones_mesa")
    op.drop_column("reservas", "check_in_at")
    op.drop_column("mesas", "estado")
    sa.Enum(name="estado_mesa").drop(op.get_bind())
    # estado_reserva no se puede volver atrás (Postgres no soporta DROP
    # VALUE de un enum), igual que en la migración anterior.
