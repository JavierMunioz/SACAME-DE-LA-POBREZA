from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Factura(Base):
    __tablename__ = "facturas"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Null en la prefactura de un domicilio (no hay mesa que cerrar).
    mesa_id: Mapped[int | None] = mapped_column(ForeignKey("mesas.id"), nullable=True)
    restaurante_id: Mapped[int] = mapped_column(ForeignKey("restaurantes.id"))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    incluye_propina: Mapped[bool] = mapped_column(Boolean, default=False)
    propina: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    # Mesa: se marca pagada al generarla (se asume cobrada al cerrar la
    # mesa, como siempre). Domicilio interno: nace sin pagar — es la
    # prefactura que el repartidor lleva y cobra contra entrega, recién
    # ahí se marca pagada (ver Brain.md).
    pagado: Mapped[bool] = mapped_column(Boolean, default=False)
    pagado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    mesa: Mapped["Mesa | None"] = relationship()
    pedidos: Mapped[list["Pedido"]] = relationship(back_populates="factura")
