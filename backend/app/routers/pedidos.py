from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.models import EstadoPedido, ItemPedido, MenuItem, Mesa, Pedido, Rol, Usuario
from app.schemas.pedido import ItemPedidoOut, PedidoCreate, PedidoOut

router = APIRouter(prefix="/pedidos", tags=["pedidos"])


def _pedido_a_out(pedido: Pedido) -> PedidoOut:
    return PedidoOut(
        id=pedido.id,
        mesa_id=pedido.mesa_id,
        mesa_numero=pedido.mesa.numero,
        cliente_id=pedido.cliente_id,
        estado=pedido.estado,
        created_at=pedido.created_at,
        confirmado_at=pedido.confirmado_at,
        items=[
            ItemPedidoOut(
                id=i.id,
                menu_item_id=i.menu_item_id,
                menu_item_nombre=i.menu_item.nombre,
                cantidad=i.cantidad,
                precio_unitario=i.precio_unitario,
                observaciones=i.observaciones,
            )
            for i in pedido.items
        ],
    )


def _get_pedido_del_restaurante_o_404(db: Session, pedido_id: int, restaurante_id: int) -> Pedido:
    pedido = (
        db.query(Pedido)
        .join(Mesa)
        .filter(Pedido.id == pedido_id, Mesa.restaurante_id == restaurante_id)
        .first()
    )
    if pedido is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido no encontrado")
    return pedido


@router.post("", response_model=PedidoOut, status_code=status.HTTP_201_CREATED)
def crear_pedido(
    datos: PedidoCreate,
    db: Session = Depends(get_db),
    cliente: Usuario = Depends(require_roles(Rol.CLIENTE)),
):
    mesa = db.get(Mesa, datos.mesa_id)
    if mesa is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mesa no encontrada")
    if not datos.items:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "El pedido no tiene items")

    menu_ids = [item.menu_item_id for item in datos.items]
    menu_items = (
        db.query(MenuItem)
        .filter(MenuItem.id.in_(menu_ids), MenuItem.restaurante_id == mesa.restaurante_id)
        .all()
    )
    menu_por_id = {m.id: m for m in menu_items}
    faltantes = set(menu_ids) - menu_por_id.keys()
    if faltantes:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Ítems de menú inválidos para este restaurante: {sorted(faltantes)}",
        )

    pedido = Pedido(mesa_id=mesa.id, cliente_id=cliente.id)
    db.add(pedido)
    db.flush()

    for item in datos.items:
        menu_item = menu_por_id[item.menu_item_id]
        db.add(
            ItemPedido(
                pedido_id=pedido.id,
                menu_item_id=menu_item.id,
                cantidad=item.cantidad,
                # Precio congelado al momento del pedido, no sigue al menú.
                precio_unitario=menu_item.precio,
                observaciones=item.observaciones,
            )
        )

    db.commit()
    db.refresh(pedido)
    return _pedido_a_out(pedido)


@router.get("", response_model=list[PedidoOut])
def listar_pedidos(
    estado: EstadoPedido | None = None,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(require_roles(Rol.MESERO, Rol.COCINA, Rol.ADMIN_RESTAURANTE)),
):
    query = db.query(Pedido).join(Mesa).filter(Mesa.restaurante_id == usuario.restaurante_id)
    if estado is not None:
        query = query.filter(Pedido.estado == estado)

    # Cocina necesita orden FIFO por hora de llegada a cocina (confirmado_at),
    # no por hora de creación del pedido (ver Readme.md).
    orden = Pedido.confirmado_at if estado == EstadoPedido.CONFIRMADO else Pedido.created_at
    pedidos = query.order_by(orden).all()
    return [_pedido_a_out(p) for p in pedidos]


@router.post("/{pedido_id}/confirmar", response_model=PedidoOut)
def confirmar_pedido(
    pedido_id: int,
    db: Session = Depends(get_db),
    mesero: Usuario = Depends(require_roles(Rol.MESERO, Rol.ADMIN_RESTAURANTE)),
):
    pedido = _get_pedido_del_restaurante_o_404(db, pedido_id, mesero.restaurante_id)
    if pedido.estado != EstadoPedido.PENDIENTE:
        raise HTTPException(status.HTTP_409_CONFLICT, "El pedido ya no está pendiente")
    pedido.estado = EstadoPedido.CONFIRMADO
    pedido.confirmado_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(pedido)
    return _pedido_a_out(pedido)


@router.post("/{pedido_id}/cancelar", response_model=PedidoOut)
def cancelar_pedido(
    pedido_id: int,
    db: Session = Depends(get_db),
    mesero: Usuario = Depends(require_roles(Rol.MESERO, Rol.ADMIN_RESTAURANTE)),
):
    pedido = _get_pedido_del_restaurante_o_404(db, pedido_id, mesero.restaurante_id)
    if pedido.estado != EstadoPedido.PENDIENTE:
        raise HTTPException(status.HTTP_409_CONFLICT, "El pedido ya no está pendiente")
    pedido.estado = EstadoPedido.CANCELADO
    db.commit()
    db.refresh(pedido)
    return _pedido_a_out(pedido)
