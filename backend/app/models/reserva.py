import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class EstadoReserva(str, enum.Enum):
    ACTIVA = "activa"
    CANCELADA = "cancelada"
    COMPLETADA = "completada"
    # Nadie hizo check-in 15 min antes de la hora reservada: la mesa se
    # libera sola para que otro pueda usarla o reservarla (ver Brain.md).
    EXPIRADA = "expirada"


class Reserva(Base):
    __tablename__ = "reservas"
    __table_args__ = (
        # Impide dos reservas activas para la misma mesa en el mismo horario exacto.
        # Índice único parcial (solo sobre estado='activa') para permitir que
        # reservas canceladas no bloqueen ese horario.
        Index(
            "uq_reserva_mesa_horario_activa",
            "mesa_id",
            "inicio",
            unique=True,
            postgresql_where=text("estado = 'activa'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    mesa_id: Mapped[int] = mapped_column(ForeignKey("mesas.id"))
    cliente_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    duracion_minutos: Mapped[int] = mapped_column(default=90)
    estado: Mapped[EstadoReserva] = mapped_column(
        Enum(EstadoReserva, name="estado_reserva", values_callable=lambda e: [m.value for m in e]),
        default=EstadoReserva.ACTIVA,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # Se llena cuando el cliente confirma su llegada (ver /mesas/{id}/ocupar
    # con reserva_id). Si no se llena 15 min antes de `inicio`, la reserva
    # expira sola (ver MINUTOS_LLEGADA_ANTICIPADA en routers/mesas.py).
    check_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    mesa: Mapped["Mesa"] = relationship(back_populates="reservas")
    cliente: Mapped["Usuario"] = relationship()
