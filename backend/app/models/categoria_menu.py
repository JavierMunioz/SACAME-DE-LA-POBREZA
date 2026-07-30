from sqlalchemy import Column, ForeignKey, Integer, String, Table, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

# Muchos-a-muchos: un plato puede estar en varias categorías (ej. "Para
# compartir" y "Vegetariano" a la vez), una categoría tiene varios platos.
menu_item_categoria = Table(
    "menu_item_categoria",
    Base.metadata,
    Column("menu_item_id", ForeignKey("menu.id"), primary_key=True),
    Column("categoria_id", ForeignKey("categorias_menu.id"), primary_key=True),
)


class CategoriaMenu(Base):
    __tablename__ = "categorias_menu"
    __table_args__ = (
        UniqueConstraint("restaurante_id", "nombre", name="uq_categoria_restaurante_nombre"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    restaurante_id: Mapped[int] = mapped_column(ForeignKey("restaurantes.id"))
    nombre: Mapped[str] = mapped_column(String(60))
    # Orden de presentación en el menú (no alfabético): lo define el
    # admin al crearlas, en el orden en que las va agregando.
    orden: Mapped[int] = mapped_column(Integer, default=0)

    restaurante: Mapped["Restaurante"] = relationship()
    items: Mapped[list["MenuItem"]] = relationship(
        secondary=menu_item_categoria, back_populates="categorias"
    )
