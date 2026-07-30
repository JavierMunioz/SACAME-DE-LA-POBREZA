from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.reserva import EstadoReserva


class ReservaCreate(BaseModel):
    mesa_id: int
    inicio: datetime
    duracion_minutos: int = 90


class ReservaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    mesa_id: int
    cliente_id: int
    inicio: datetime
    duracion_minutos: int
    estado: EstadoReserva
    created_at: datetime
    check_in_at: datetime | None


class MesaDisponibilidad(BaseModel):
    mesa_id: int
    numero: int
    capacidad: int
    disponible: bool
