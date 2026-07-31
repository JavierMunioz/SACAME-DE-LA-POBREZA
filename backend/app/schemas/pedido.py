from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.models.pedido import CanalPedido, EstadoPedido


class ItemPedidoCreate(BaseModel):
    menu_item_id: int
    cantidad: int = Field(default=1, ge=1)
    observaciones: str | None = None


class PedidoCreate(BaseModel):
    # Uno de los dos, según el canal: pedido de mesa manda mesa_id;
    # pedido de domicilio manda restaurante_id + dirección directamente
    # (no hay mesa física que lo ubique).
    mesa_id: int | None = None
    restaurante_id: int | None = None
    canal: CanalPedido = CanalPedido.MESA
    direccion_entrega: str | None = None
    telefono_entrega: str | None = None
    items: list[ItemPedidoCreate]
    # Requerido si quien pide no tiene sesión (invitado sin cuenta): la
    # sesión sabe el nombre y valida que la mesa siga reclamada por vos.
    # Opcional para clientes logueados que piden directo sin haber
    # reclamado la mesa vía /mesas/{id}/ocupar (compatibilidad).
    sesion_token: str | None = None

    @model_validator(mode="after")
    def _validar_canal(self) -> "PedidoCreate":
        if self.canal == CanalPedido.MESA:
            if self.mesa_id is None:
                raise ValueError("mesa_id es obligatorio para pedidos de mesa")
        else:
            if self.restaurante_id is None:
                raise ValueError("restaurante_id es obligatorio para pedidos de domicilio")
            if self.canal == CanalPedido.DOMICILIO_INTERNO and not self.direccion_entrega:
                raise ValueError("direccion_entrega es obligatoria para domicilio interno")
        return self


class ItemPedidoOut(BaseModel):
    id: int
    menu_item_id: int
    menu_item_nombre: str
    cantidad: int
    precio_unitario: Decimal
    observaciones: str | None


class PedidoOut(BaseModel):
    id: int
    mesa_id: int | None
    mesa_numero: int | None
    restaurante_id: int
    canal: CanalPedido
    direccion_entrega: str | None
    telefono_entrega: str | None
    repartidor_id: int | None
    repartidor_nombre: str | None
    repartidor_lat: float | None
    repartidor_lng: float | None
    repartidor_actualizado_at: datetime | None
    cliente_id: int | None
    nombre_invitado: str | None
    estado: EstadoPedido
    created_at: datetime
    confirmado_at: datetime | None
    factura_id: int | None
    # Denormalizado desde la Factura para que el repartidor sepa cuánto
    # cobrar sin tener que pegarle a /facturas/{id} aparte.
    factura_total: Decimal | None
    factura_pagado: bool | None
    items: list[ItemPedidoOut]


class UbicacionUpdate(BaseModel):
    lat: float
    lng: float


class AsignarRepartidor(BaseModel):
    repartidor_id: int


class MarcarEntregadoInput(BaseModel):
    # Domicilio interno cobra contra entrega: al marcar entregado, el
    # repartidor también confirma si cobró (default sí — es lo esperado
    # en el camino feliz). Mesa/rappi/didi lo ignoran, no tienen
    # prefactura en este punto del flujo.
    pagado: bool = True
