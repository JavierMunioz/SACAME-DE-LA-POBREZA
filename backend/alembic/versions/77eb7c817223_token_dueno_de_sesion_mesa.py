"""token_dueno separado del token compartido en sesiones_mesa

Revision ID: 77eb7c817223
Revises: 79e4cc88656e
Create Date: 2026-07-30 15:00:00.000000

"""
import secrets
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '77eb7c817223'
down_revision: Union[str, None] = '79e4cc88656e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "sesiones_mesa", sa.Column("token_dueno", sa.String(length=64), nullable=True)
    )
    # Backfill de filas existentes (si las hay) con un secreto propio, no
    # pueden quedar en NULL antes de aplicar el unique+not null.
    conn = op.get_bind()
    filas = conn.execute(sa.text("SELECT id FROM sesiones_mesa")).fetchall()
    for (id_,) in filas:
        conn.execute(
            sa.text("UPDATE sesiones_mesa SET token_dueno = :t WHERE id = :id"),
            {"t": secrets.token_urlsafe(32), "id": id_},
        )
    op.alter_column("sesiones_mesa", "token_dueno", nullable=False)
    op.create_index(
        "ix_sesiones_mesa_token_dueno", "sesiones_mesa", ["token_dueno"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_sesiones_mesa_token_dueno", table_name="sesiones_mesa")
    op.drop_column("sesiones_mesa", "token_dueno")
