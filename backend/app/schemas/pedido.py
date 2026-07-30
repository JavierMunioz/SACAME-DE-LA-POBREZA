from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.pedido import EstadoPedido


class ItemPedidoCreate(BaseModel):
    menu_item_id: int
    cantidad: int = Field(default=1, ge=1)
    observaciones: str | None = None


class PedidoCreate(BaseModel):
    mesa_id: int
    items: list[ItemPedidoCreate]


class ItemPedidoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    menu_item_id: int
    cantidad: int
    precio_unitario: Decimal
    observaciones: str | None


class PedidoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    mesa_id: int
    cliente_id: int | None
    estado: EstadoPedido
    created_at: datetime
    items: list[ItemPedidoOut]
