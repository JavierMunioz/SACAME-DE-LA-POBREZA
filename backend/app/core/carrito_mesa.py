"""Carrito compartido en vivo por mesa, sincronizado por WebSocket.

Vive en memoria del proceso — es estado transitorio previo al pedido
real (que sí se persiste vía POST /pedidos). No hay multi-worker en este
proyecto, así que un dict en memoria alcanza; si se escala a varios
workers esto necesitaría moverse a Redis pub/sub."""

from dataclasses import dataclass, field

from fastapi import WebSocket


@dataclass
class ItemCarrito:
    cantidad: int
    observaciones: str | None = None


class GestorCarritosMesa:
    def __init__(self) -> None:
        self._conexiones: dict[int, list[WebSocket]] = {}
        self._carritos: dict[int, dict[int, ItemCarrito]] = {}

    async def conectar(self, mesa_id: int, ws: WebSocket) -> None:
        await ws.accept()
        self._conexiones.setdefault(mesa_id, []).append(ws)
        await ws.send_json(self._snapshot(mesa_id))

    def desconectar(self, mesa_id: int, ws: WebSocket) -> None:
        conexiones = self._conexiones.get(mesa_id)
        if conexiones and ws in conexiones:
            conexiones.remove(ws)

    async def actualizar_item(
        self, mesa_id: int, menu_item_id: int, cantidad: int, observaciones: str | None
    ) -> None:
        carrito = self._carritos.setdefault(mesa_id, {})
        if cantidad <= 0:
            carrito.pop(menu_item_id, None)
        else:
            carrito[menu_item_id] = ItemCarrito(cantidad=cantidad, observaciones=observaciones)
        await self._broadcast(mesa_id)

    async def limpiar(self, mesa_id: int) -> None:
        self._carritos.pop(mesa_id, None)
        await self._broadcast(mesa_id)

    def _snapshot(self, mesa_id: int) -> dict:
        items = self._carritos.get(mesa_id, {})
        return {
            "tipo": "carrito",
            "items": [
                {"menu_item_id": k, "cantidad": v.cantidad, "observaciones": v.observaciones}
                for k, v in items.items()
            ],
        }

    async def _broadcast(self, mesa_id: int) -> None:
        snapshot = self._snapshot(mesa_id)
        vivas: list[WebSocket] = []
        for ws in self._conexiones.get(mesa_id, []):
            try:
                await ws.send_json(snapshot)
                vivas.append(ws)
            except Exception:
                pass
        self._conexiones[mesa_id] = vivas


gestor_carritos = GestorCarritosMesa()
