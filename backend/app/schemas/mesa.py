from datetime import datetime

from pydantic import BaseModel, ConfigDict


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
