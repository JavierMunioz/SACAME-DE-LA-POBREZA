import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Rol(str, enum.Enum):
    ADMIN_GENERAL = "admin_general"
    ADMIN_RESTAURANTE = "admin_restaurante"
    CLIENTE = "cliente"
    MESERO = "mesero"
    COCINA = "cocina"
    REPARTIDOR = "repartidor"


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    rol: Mapped[Rol] = mapped_column(
        Enum(Rol, name="rol_usuario", values_callable=lambda e: [m.value for m in e])
    )
    restaurante_id: Mapped[int | None] = mapped_column(
        ForeignKey("restaurantes.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    restaurante: Mapped["Restaurante | None"] = relationship(back_populates="usuarios")
