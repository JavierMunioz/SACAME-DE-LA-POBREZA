import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class EstadoMesa(str, enum.Enum):
    """Estado transaccional de la mesa (evento: se ocupa/se libera).

    No incluye 'reservada': ese estado es temporal (depende de la hora
    actual contra la ventana de una reserva) y se calcula al vuelo en el
    router en vez de guardarse, para no arrastrar un valor viejo si nadie
    corre un job que lo actualice."""

    LIBRE = "libre"
    OCUPADA = "ocupada"


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
    estado: Mapped[EstadoMesa] = mapped_column(
        Enum(EstadoMesa, name="estado_mesa", values_callable=lambda e: [m.value for m in e]),
        default=EstadoMesa.LIBRE,
    )

    restaurante: Mapped["Restaurante"] = relationship(back_populates="mesas")
    reservas: Mapped[list["Reserva"]] = relationship(back_populates="mesa")
    pedidos: Mapped[list["Pedido"]] = relationship(back_populates="mesa")
    sesiones: Mapped[list["SesionMesa"]] = relationship(back_populates="mesa")
