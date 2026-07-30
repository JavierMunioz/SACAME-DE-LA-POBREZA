from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.schemas.categoria import CategoriaOut
from app.schemas.menu import MenuItemCreate, MenuItemOut


class RestauranteCreate(BaseModel):
    nombre: str
    descripcion: str | None = None
    categoria: str | None = None
    latitud: float | None = None
    longitud: float | None = None
    menu_inicial: list[MenuItemCreate] = []


class RestauranteUpdate(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None
    categoria: str | None = None
    latitud: float | None = None
    longitud: float | None = None


class RestauranteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    descripcion: str | None
    categoria: str | None
    created_at: datetime
    # Al menos una mesa libre ahora mismo — computado en el listado
    # público, no una columna guardada (mismo criterio que el resto del
    # dominio: el estado de mesa siempre se calcula al vuelo).
    mesas_disponibles: bool = False


class RestauranteConMenu(RestauranteOut):
    latitud: float | None = None
    longitud: float | None = None
    # Categorías del menú (ej. "Entradas", "Postres") — no confundir con
    # `categoria` (el tipo de cocina del restaurante, ej. "Mariscos").
    categorias_menu: list[CategoriaOut] = []
    menu: list[MenuItemOut]


class PlatoVendidoOut(BaseModel):
    menu_item_id: int
    nombre: str
    cantidad_vendida: int
    precio: Decimal


class EstadisticasRestauranteOut(BaseModel):
    revenue_hoy: Decimal
    revenue_ayer: Decimal
    # None si ayer no facturó nada (no hay base para calcular variación).
    variacion_pct: float | None
    mesas_ocupadas: int
    mesas_total: int
    platos_mas_vendidos_hoy: list[PlatoVendidoOut]
