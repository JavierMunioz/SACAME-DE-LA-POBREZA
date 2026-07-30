from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.schemas.categoria import CategoriaOut


class MenuItemCreate(BaseModel):
    nombre: str
    descripcion: str | None = None
    precio: Decimal
    disponible: bool = True
    categoria_ids: list[int] = []


class MenuItemUpdate(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None
    precio: Decimal | None = None
    disponible: bool | None = None
    # None = no tocar las categorías asignadas; [] = sacarlo de todas.
    categoria_ids: list[int] | None = None


class MenuItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    descripcion: str | None
    precio: Decimal
    disponible: bool
    categorias: list[CategoriaOut] = []
