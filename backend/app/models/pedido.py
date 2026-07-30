import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class EstadoPedido(str, enum.Enum):
    PENDIENTE = "pendiente"
    CONFIRMADO = "confirmado"
    PREPARANDO = "preparando"
    LISTO = "listo"
    CANCELADO = "cancelado"
    ENTREGADO = "entregado"


class Pedido(Base):
    __tablename__ = "pedidos"

    id: Mapped[int] = mapped_column(primary_key=True)
    mesa_id: Mapped[int] = mapped_column(ForeignKey("mesas.id"))
    cliente_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    mesero_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    factura_id: Mapped[int | None] = mapped_column(ForeignKey("facturas.id"), nullable=True)
    estado: Mapped[EstadoPedido] = mapped_column(
        Enum(EstadoPedido, name="estado_pedido", values_callable=lambda e: [m.value for m in e]),
        default=EstadoPedido.PENDIENTE,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    confirmado_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    mesa: Mapped["Mesa"] = relationship(back_populates="pedidos")
    items: Mapped[list["ItemPedido"]] = relationship(back_populates="pedido")
