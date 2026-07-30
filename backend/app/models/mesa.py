from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Mesa(Base):
    __tablename__ = "mesas"
    __table_args__ = (
        UniqueConstraint("restaurante_id", "numero", name="uq_mesa_restaurante_numero"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    restaurante_id: Mapped[int] = mapped_column(ForeignKey("restaurantes.id"))
    numero: Mapped[int]
    capacidad: Mapped[int]
    # Token opaco que codifica la mesa en la URL del QR (ver Brain.md).
    # Se regenera al invalidar un QR perdido/dañado.
    qr_token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    qr_generado_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    restaurante: Mapped["Restaurante"] = relationship(back_populates="mesas")
    reservas: Mapped[list["Reserva"]] = relationship(back_populates="mesa")
    pedidos: Mapped[list["Pedido"]] = relationship(back_populates="mesa")
