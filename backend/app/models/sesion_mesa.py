from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SesionMesa(Base):
    """Sesión de uso de una mesa: se abre cuando alguien escanea el QR y
    reclama la mesa (invitado con nombre, o cliente con o sin reserva), y
    se cierra cuando el mesero factura. Mientras está abierta, la mesa
    queda bloqueada para que otro dispositivo la reclame — solo puede
    sumarse con el código de 4 dígitos de esta sesión."""

    __tablename__ = "sesiones_mesa"
    __table_args__ = (
        # Solo una sesión abierta por mesa a la vez.
        Index(
            "uq_sesion_mesa_activa",
            "mesa_id",
            unique=True,
            postgresql_where=text("cerrada_at IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    mesa_id: Mapped[int] = mapped_column(ForeignKey("mesas.id"))
    cliente_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    nombre_invitado: Mapped[str | None] = mapped_column(String(80), nullable=True)
    reserva_id: Mapped[int | None] = mapped_column(ForeignKey("reservas.id"), nullable=True)
    # Token compartido: lo tienen dueño y quienes se suman con el código.
    # Autoriza ver/editar el carrito en vivo (WebSocket), NO enviar el
    # pedido — eso requiere token_dueno, que solo recibe quien abrió la
    # mesa (nunca se devuelve en /unirse).
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    token_dueno: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    codigo_acceso: Mapped[str] = mapped_column(String(4))
    abierta_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    cerrada_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Se llenó cuando el cliente tocó "Llamar al mesero"; se limpia cuando
    # el mesero marca que ya fue. No es un chat, es una bandera simple.
    llamada_mesero_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    mesa: Mapped["Mesa"] = relationship(back_populates="sesiones")
    cliente: Mapped["Usuario"] = relationship()
