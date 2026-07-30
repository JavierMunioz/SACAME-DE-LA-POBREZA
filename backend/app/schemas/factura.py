from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.pedido import ItemPedidoOut


class FacturaCreate(BaseModel):
    incluye_propina: bool = False
    porcentaje_propina: Decimal = Field(default=Decimal("0.10"), ge=0, le=1)


class FacturaOut(BaseModel):
    id: int
    mesa_id: int
    mesa_numero: int
    subtotal: Decimal
    incluye_propina: bool
    propina: Decimal
    total: Decimal
    created_at: datetime
    items: list[ItemPedidoOut]
