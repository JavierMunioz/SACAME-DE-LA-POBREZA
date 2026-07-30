from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.menu import MenuItemOut
from app.schemas.reserva import ReservaOut


class MesaCreate(BaseModel):
    numero: int
    capacidad: int


class MesaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    restaurante_id: int
    numero: int
    capacidad: int
    # Tri-estado de presentación (libre/reservada/ocupada), igual que en
    # MesaQrInfo — reservada se computa al vuelo, no se guarda.
    estado: Literal["libre", "reservada", "ocupada"]
    qr_generado_at: datetime
    qr_url: str


class SesionMesaOut(BaseModel):
    """Lo que recibe el dispositivo que abre o se une a una sesión de mesa.
    `token` autoriza ver/editar el carrito en vivo (WebSocket) y lo tienen
    todos los que se sumaron con el código. `token_dueno` autoriza enviar
    el pedido y solo lo recibe quien abrió la mesa (null para quien se
    suma vía /unirse)."""

    token: str
    token_dueno: str | None
    codigo_acceso: str
    mesa_id: int
    nombre: str


class OcuparMesaRequest(BaseModel):
    qr_token: str
    nombre_invitado: str | None = None
    reserva_id: int | None = None


class OcuparMesaStaffRequest(BaseModel):
    """Apertura manual por mesero/admin: sin QR, para sentar a alguien
    que no puede o no quiere usar el celular (ver Brain.md)."""

    nombre_invitado: str | None = None


class UnirseMesaRequest(BaseModel):
    qr_token: str
    codigo_acceso: str


class MesaQrInfo(BaseModel):
    mesa_id: int
    restaurante_id: int
    restaurante_nombre: str
    numero: int
    capacidad: int
    reserva_propia: ReservaOut | None
    mesa_libre_ahora: bool
    # Estado de presentación (tri-estado): a diferencia de Mesa.estado
    # (solo libre/ocupada, transaccional), acá "reservada" se calcula al
    # vuelo contra la hora actual.
    estado: Literal["libre", "reservada", "ocupada"]
    # True si hay una sesión activa que no es la de quien está pidiendo
    # este QR — el frontend debe pedir el código de 4 dígitos en vez de
    # mostrar el menú directamente.
    requiere_codigo: bool
    menu: list[MenuItemOut]
