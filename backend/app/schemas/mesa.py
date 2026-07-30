from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.menu import MenuItemOut
from app.schemas.reserva import ReservaOut


class MesaCreate(BaseModel):
    numero: int
    capacidad: int


class MesaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    restaurante_id: int
    numero: int
    capacidad: int
    qr_generado_at: datetime
    qr_url: str


class MesaQrInfo(BaseModel):
    mesa_id: int
    restaurante_id: int
    restaurante_nombre: str
    numero: int
    capacidad: int
    reserva_propia: ReservaOut | None
    mesa_libre_ahora: bool
    menu: list[MenuItemOut]
