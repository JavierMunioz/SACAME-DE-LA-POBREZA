from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.models import ItemPedido, MenuItem, Mesa, Pedido, Rol, Usuario
from app.schemas.pedido import PedidoCreate, PedidoOut

router = APIRouter(prefix="/pedidos", tags=["pedidos"])


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
    return pedido
