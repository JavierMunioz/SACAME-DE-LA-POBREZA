from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ItemPedido(Base):
    __tablename__ = "items_pedido"

    id: Mapped[int] = mapped_column(primary_key=True)
    pedido_id: Mapped[int] = mapped_column(ForeignKey("pedidos.id"))
    menu_item_id: Mapped[int] = mapped_column(ForeignKey("menu.id"))
    cantidad: Mapped[int] = mapped_column(default=1)
    # Precio congelado al momento del pedido (no sigue cambios futuros del menú).
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    observaciones: Mapped[str | None] = mapped_column(String(500), nullable=True)

    pedido: Mapped["Pedido"] = relationship(back_populates="items")
    menu_item: Mapped["MenuItem"] = relationship()
