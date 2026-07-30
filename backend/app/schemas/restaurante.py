from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.menu import MenuItemCreate, MenuItemOut


class RestauranteCreate(BaseModel):
    nombre: str
    descripcion: str | None = None
    menu_inicial: list[MenuItemCreate] = []


class RestauranteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    descripcion: str | None
    created_at: datetime


class RestauranteConMenu(RestauranteOut):
    menu: list[MenuItemOut]
