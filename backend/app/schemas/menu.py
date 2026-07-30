from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class MenuItemCreate(BaseModel):
    nombre: str
    descripcion: str | None = None
    precio: Decimal
    disponible: bool = True


class MenuItemUpdate(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None
    precio: Decimal | None = None
    disponible: bool | None = None


class MenuItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    descripcion: str | None
    precio: Decimal
    disponible: bool
