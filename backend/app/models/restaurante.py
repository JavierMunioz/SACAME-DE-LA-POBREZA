from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Restaurante(Base):
    __tablename__ = "restaurantes"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(150))
    descripcion: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    categoria: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    mesas: Mapped[list["Mesa"]] = relationship(back_populates="restaurante")
    usuarios: Mapped[list["Usuario"]] = relationship(back_populates="restaurante")
    menu_items: Mapped[list["MenuItem"]] = relationship(back_populates="restaurante")
