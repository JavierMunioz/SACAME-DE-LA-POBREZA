from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.models import EstadoPedido, Factura, Mesa, Pedido, Rol, Usuario
from app.schemas.factura import FacturaCreate, FacturaOut
from app.schemas.pedido import ItemPedidoOut

router = APIRouter(tags=["facturas"])


def _factura_a_out(factura: Factura, items: list[ItemPedidoOut]) -> FacturaOut:
    return FacturaOut(
        id=factura.id,
        mesa_id=factura.mesa_id,
        mesa_numero=factura.mesa.numero,
        subtotal=factura.subtotal,
        incluye_propina=factura.incluye_propina,
        propina=factura.propina,
        total=factura.total,
        created_at=factura.created_at,
        items=items,
    )


@router.post(
    "/mesas/{mesa_id}/factura",
    response_model=FacturaOut,
    status_code=status.HTTP_201_CREATED,
)
def generar_factura(
    mesa_id: int,
    datos: FacturaCreate,
    db: Session = Depends(get_db),
    mesero: Usuario = Depends(require_roles(Rol.MESERO, Rol.ADMIN_RESTAURANTE)),
):
    mesa = (
        db.query(Mesa)
        .filter(Mesa.id == mesa_id, Mesa.restaurante_id == mesero.restaurante_id)
        .first()
    )
    if mesa is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mesa no encontrada")

    # Solo se factura lo confirmado (ya en cocina) y que todavía no esté en
    # otra factura. Lo pendiente no cuenta: no se le puede cobrar al cliente
    # algo que la cocina ni recibió.
    pedidos = (
        db.query(Pedido)
        .filter(
            Pedido.mesa_id == mesa_id,
            Pedido.estado == EstadoPedido.CONFIRMADO,
            Pedido.factura_id.is_(None),
        )
        .all()
    )
    if not pedidos:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "No hay pedidos confirmados pendientes de facturar en esta mesa",
        )

    items = [item for pedido in pedidos for item in pedido.items]
    subtotal = sum((item.precio_unitario * item.cantidad for item in items), Decimal("0"))
    propina = (
        (subtotal * datos.porcentaje_propina).quantize(Decimal("0.01"))
        if datos.incluye_propina
        else Decimal("0")
    )
    total = subtotal + propina

    factura = Factura(
        mesa_id=mesa_id,
        subtotal=subtotal,
        incluye_propina=datos.incluye_propina,
        propina=propina,
        total=total,
    )
    db.add(factura)
    db.flush()

    for pedido in pedidos:
        pedido.factura_id = factura.id
        pedido.estado = EstadoPedido.ENTREGADO

    db.commit()
    db.refresh(factura)

    items_out = [
        ItemPedidoOut(
            id=i.id,
            menu_item_id=i.menu_item_id,
            menu_item_nombre=i.menu_item.nombre,
            cantidad=i.cantidad,
            precio_unitario=i.precio_unitario,
            observaciones=i.observaciones,
        )
        for i in items
    ]
    return _factura_a_out(factura, items_out)


@router.get("/facturas/{factura_id}", response_model=FacturaOut)
def obtener_factura(
    factura_id: int,
    db: Session = Depends(get_db),
    mesero: Usuario = Depends(require_roles(Rol.MESERO, Rol.ADMIN_RESTAURANTE)),
):
    factura = (
        db.query(Factura)
        .join(Mesa)
        .filter(Factura.id == factura_id, Mesa.restaurante_id == mesero.restaurante_id)
        .first()
    )
    if factura is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Factura no encontrada")

    items_out = [
        ItemPedidoOut(
            id=i.id,
            menu_item_id=i.menu_item_id,
            menu_item_nombre=i.menu_item.nombre,
            cantidad=i.cantidad,
            precio_unitario=i.precio_unitario,
            observaciones=i.observaciones,
        )
        for pedido in factura.pedidos
        for i in pedido.items
    ]
    return _factura_a_out(factura, items_out)
