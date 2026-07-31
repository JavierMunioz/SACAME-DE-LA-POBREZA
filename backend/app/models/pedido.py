import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class EstadoPedido(str, enum.Enum):
    PENDIENTE = "pendiente"
    CONFIRMADO = "confirmado"
    PREPARANDO = "preparando"
    LISTO = "listo"
    EN_CAMINO = "en_camino"
    CANCELADO = "cancelado"
    ENTREGADO = "entregado"


class CanalPedido(str, enum.Enum):
    MESA = "mesa"
    DOMICILIO_INTERNO = "domicilio_interno"
    RAPPI = "rappi"
    DIDI = "didi"


class Pedido(Base):
    __tablename__ = "pedidos"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Null en pedidos por domicilio (no hay mesa física asociada).
    mesa_id: Mapped[int | None] = mapped_column(ForeignKey("mesas.id"), nullable=True)
    # Antes se derivaba siempre de mesa.restaurante_id (join obligatorio
    # para todo scoping por restaurante). Un pedido por domicilio no tiene
    # mesa, así que el restaurante queda explícito acá — evita reintroducir
    # el join opcional en cada query de mesero/cocina/admin.
    restaurante_id: Mapped[int] = mapped_column(ForeignKey("restaurantes.id"))
    cliente_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    mesero_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    factura_id: Mapped[int | None] = mapped_column(ForeignKey("facturas.id"), nullable=True)
    sesion_mesa_id: Mapped[int | None] = mapped_column(
        ForeignKey("sesiones_mesa.id"), nullable=True
    )
    # Nombre tipeado por el invitado al reclamar la mesa (ver SesionMesa).
    # Snapshot al momento del pedido — no sigue cambios posteriores de la
    # sesión. Null si quien pidió es un cliente logueado (ya tiene nombre
    # vía cliente_id).
    nombre_invitado: Mapped[str | None] = mapped_column(String(80), nullable=True)
    estado: Mapped[EstadoPedido] = mapped_column(
        Enum(EstadoPedido, name="estado_pedido", values_callable=lambda e: [m.value for m in e]),
        default=EstadoPedido.PENDIENTE,
    )
    canal: Mapped[CanalPedido] = mapped_column(
        Enum(CanalPedido, name="canal_pedido", values_callable=lambda e: [m.value for m in e]),
        default=CanalPedido.MESA,
    )
    # Solo domicilio_interno usa lo de abajo. rappi/didi no se integran de
    # verdad (requiere cuenta de comercio con esas plataformas) — el
    # mesero solo registra el canal para que quede en el reporte.
    direccion_entrega: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telefono_entrega: Mapped[str | None] = mapped_column(String(30), nullable=True)
    repartidor_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    repartidor_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    repartidor_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    repartidor_actualizado_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    confirmado_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    mesa: Mapped["Mesa | None"] = relationship(back_populates="pedidos")
    items: Mapped[list["ItemPedido"]] = relationship(back_populates="pedido")
    # foreign_keys explícito: usuarios.id ya lo referencian cliente_id y
    # mesero_id, SQLAlchemy no puede inferir solo con repartidor_id.
    repartidor: Mapped["Usuario | None"] = relationship(foreign_keys=[repartidor_id])
