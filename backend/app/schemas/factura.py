from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.pedido import ItemPedidoOut


class FacturaCreate(BaseModel):
    incluye_propina: bool = False
    porcentaje_propina: Decimal = Field(default=Decimal("0.10"), ge=0, le=1)


class FacturaOut(BaseModel):
    id: int
    mesa_id: int | None
    mesa_numero: int | None
    restaurante_id: int
    subtotal: Decimal
    incluye_propina: bool
    propina: Decimal
    total: Decimal
    pagado: bool
    pagado_at: datetime | None
    created_at: datetime
    items: list[ItemPedidoOut]
