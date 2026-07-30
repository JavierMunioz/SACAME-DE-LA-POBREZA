from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.pedido import EstadoPedido


class ItemPedidoCreate(BaseModel):
    menu_item_id: int
    cantidad: int = Field(default=1, ge=1)
    observaciones: str | None = None


class PedidoCreate(BaseModel):
    mesa_id: int
    items: list[ItemPedidoCreate]


class ItemPedidoOut(BaseModel):
    id: int
    menu_item_id: int
    menu_item_nombre: str
    cantidad: int
    precio_unitario: Decimal
    observaciones: str | None


class PedidoOut(BaseModel):
    id: int
    mesa_id: int
    mesa_numero: int
    cliente_id: int | None
    estado: EstadoPedido
    created_at: datetime
    confirmado_at: datetime | None
    items: list[ItemPedidoOut]
