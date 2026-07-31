from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.carrito_mesa import gestor_carritos
from app.core.database import get_db
from app.core.deps import require_roles
from app.models import EstadoMesa, EstadoPedido, Factura, Mesa, Pedido, Rol, SesionMesa, Usuario
from app.schemas.factura import FacturaCreate, FacturaOut
from app.schemas.pedido import ItemPedidoOut

router = APIRouter(tags=["facturas"])


def _factura_a_out(factura: Factura, items: list[ItemPedidoOut]) -> FacturaOut:
    return FacturaOut(
        id=factura.id,
        mesa_id=factura.mesa_id,
        mesa_numero=factura.mesa.numero if factura.mesa else None,
        restaurante_id=factura.restaurante_id,
        subtotal=factura.subtotal,
        incluye_propina=factura.incluye_propina,
        propina=factura.propina,
        total=factura.total,
        pagado=factura.pagado,
        pagado_at=factura.pagado_at,
        created_at=factura.created_at,
        items=items,
    )


@router.post(
    "/mesas/{mesa_id}/factura",
    response_model=FacturaOut,
    status_code=status.HTTP_201_CREATED,
)
async def generar_factura(
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

    # Solo se factura lo que el mesero ya confirmó como entregado en la
    # mesa (ver Brain.md) — no alcanza con que cocina lo haya marcado
    # "listo": eso es que está listo para servir, no que ya se sirvió. No
    # se le cobra al cliente algo que todavía no llegó a la mesa.
    pedidos = (
        db.query(Pedido)
        .filter(
            Pedido.mesa_id == mesa_id,
            Pedido.estado == EstadoPedido.ENTREGADO,
            Pedido.factura_id.is_(None),
        )
        .all()
    )
    if not pedidos:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "No hay pedidos entregados pendientes de facturar en esta mesa",
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
        restaurante_id=mesa.restaurante_id,
        subtotal=subtotal,
        incluye_propina=datos.incluye_propina,
        propina=propina,
        total=total,
        # Se asume cobrada al cerrar la mesa, como siempre funcionó este
        # flujo — a diferencia de la prefactura de domicilio, que nace
        # sin pagar (ver POST /pedidos/{id}/prefactura).
        pagado=True,
        pagado_at=datetime.now(timezone.utc),
    )
    db.add(factura)
    db.flush()

    for pedido in pedidos:
        pedido.factura_id = factura.id

    # Facturar cierra la mesa: se acabó la sesión de quien la reclamó, y
    # la mesa vuelve a estar libre para el próximo comensal.
    sesion = (
        db.query(SesionMesa)
        .filter(SesionMesa.mesa_id == mesa_id, SesionMesa.cerrada_at.is_(None))
        .first()
    )
    if sesion is not None:
        sesion.cerrada_at = datetime.now(timezone.utc)
    mesa.estado = EstadoMesa.LIBRE

    db.commit()
    await gestor_carritos.limpiar(mesa_id)
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
        .filter(Factura.id == factura_id, Factura.restaurante_id == mesero.restaurante_id)
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
