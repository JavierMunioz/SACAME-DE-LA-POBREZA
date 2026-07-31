from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.carrito_mesa import gestor_carritos
from app.core.database import get_db
from app.core.deps import get_current_user, get_current_user_opcional, require_roles
from app.models import (
    CanalPedido,
    EstadoPedido,
    Factura,
    ItemPedido,
    MenuItem,
    Mesa,
    Pedido,
    Restaurante,
    Rol,
    SesionMesa,
    Usuario,
)
from app.schemas.factura import FacturaCreate, FacturaOut
from app.schemas.pedido import (
    AsignarRepartidor,
    ItemPedidoOut,
    MarcarEntregadoInput,
    PedidoCreate,
    PedidoOut,
    UbicacionUpdate,
)

router = APIRouter(prefix="/pedidos", tags=["pedidos"])

# Solo domicilio_interno se opera de verdad (asignar repartidor, rastrear
# ubicación). Rappi/Didi no tienen integración real con esas plataformas
# (piden cuenta de comercio) — el staff solo los registra manualmente
# para que queden en el reporte, ver Brain.md.
ROLES_STAFF_RESTAURANTE = (Rol.MESERO, Rol.COCINA, Rol.ADMIN_RESTAURANTE, Rol.REPARTIDOR)


def _pedido_a_out(pedido: Pedido) -> PedidoOut:
    return PedidoOut(
        id=pedido.id,
        mesa_id=pedido.mesa_id,
        mesa_numero=pedido.mesa.numero if pedido.mesa else None,
        restaurante_id=pedido.restaurante_id,
        canal=pedido.canal,
        direccion_entrega=pedido.direccion_entrega,
        telefono_entrega=pedido.telefono_entrega,
        repartidor_id=pedido.repartidor_id,
        repartidor_nombre=pedido.repartidor.nombre if pedido.repartidor else None,
        repartidor_lat=pedido.repartidor_lat,
        repartidor_lng=pedido.repartidor_lng,
        repartidor_actualizado_at=pedido.repartidor_actualizado_at,
        cliente_id=pedido.cliente_id,
        nombre_invitado=pedido.nombre_invitado,
        estado=pedido.estado,
        created_at=pedido.created_at,
        confirmado_at=pedido.confirmado_at,
        factura_id=pedido.factura_id,
        factura_total=pedido.factura.total if pedido.factura else None,
        factura_pagado=pedido.factura.pagado if pedido.factura else None,
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
        .filter(Pedido.id == pedido_id, Pedido.restaurante_id == restaurante_id)
        .first()
    )
    if pedido is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido no encontrado")
    return pedido


def _validar_items_o_422(db: Session, restaurante_id: int, items: list) -> dict[int, MenuItem]:
    menu_ids = [item.menu_item_id for item in items]
    menu_items = (
        db.query(MenuItem)
        .filter(MenuItem.id.in_(menu_ids), MenuItem.restaurante_id == restaurante_id)
        .all()
    )
    menu_por_id = {m.id: m for m in menu_items}
    faltantes = set(menu_ids) - menu_por_id.keys()
    if faltantes:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Ítems de menú inválidos para este restaurante: {sorted(faltantes)}",
        )
    return menu_por_id


def _agregar_items(db: Session, pedido: Pedido, items: list, menu_por_id: dict[int, MenuItem]) -> None:
    for item in items:
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


@router.post("", response_model=PedidoOut, status_code=status.HTTP_201_CREATED)
async def crear_pedido(
    datos: PedidoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario | None = Depends(get_current_user_opcional),
):
    if not datos.items:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "El pedido no tiene items")

    if datos.canal != CanalPedido.MESA:
        return await _crear_pedido_domicilio(datos, db, usuario)

    # Sin cuenta también se puede pedir (ver Readme: mesa libre sin reserva
    # se puede usar sin fricción). Mesero/admin_restaurante también pueden
    # pedir directo por la mesa (ver Brain.md: cliente sentado sin forma
    # de pedir desde su celular). Cocina/admin_general no generan pedidos.
    ROLES_STAFF_PEDIDO = (Rol.MESERO, Rol.ADMIN_RESTAURANTE)
    if usuario is not None and usuario.rol not in (Rol.CLIENTE, *ROLES_STAFF_PEDIDO):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tiene permiso para esta acción")

    mesa = db.get(Mesa, datos.mesa_id) if datos.mesa_id is not None else None
    if mesa is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mesa no encontrada")

    if usuario is not None and usuario.rol in ROLES_STAFF_PEDIDO:
        if mesa.restaurante_id != usuario.restaurante_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No tiene permiso sobre esta mesa")
        pedido = Pedido(
            mesa_id=mesa.id,
            restaurante_id=mesa.restaurante_id,
            nombre_invitado=f"Tomado por {usuario.nombre}",
        )
        db.add(pedido)
        db.flush()
        menu_por_id = _validar_items_o_422(db, mesa.restaurante_id, datos.items)
        _agregar_items(db, pedido, datos.items, menu_por_id)
        db.commit()
        db.refresh(pedido)
        return _pedido_a_out(pedido)

    # Solo quien abrió la mesa puede enviar el pedido — a los que se
    # sumaron con el código les llega el mismo carrito en vivo por
    # WebSocket, pero no tienen `token_dueno` para confirmar el envío.
    # Un invitado sin cuenta necesita haber reclamado la mesa antes de
    # pedir (POST /mesas/{id}/ocupar) — así sabemos su nombre y
    # confirmamos que la mesa sigue siendo suya. Un cliente logueado puede
    # pedir con o sin sesión (compatibilidad con el flujo directo previo).
    sesion: SesionMesa | None = None
    nombre_invitado: str | None = None
    if datos.sesion_token is not None:
        sesion = (
            db.query(SesionMesa)
            .filter(
                SesionMesa.token_dueno == datos.sesion_token,
                SesionMesa.mesa_id == mesa.id,
                SesionMesa.cerrada_at.is_(None),
            )
            .first()
        )
        if sesion is None:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                "Solo quien abrió la mesa puede enviar el pedido, o la sesión venció",
            )
        nombre_invitado = sesion.nombre_invitado
    elif usuario is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Necesitás abrir o unirte a la mesa antes de pedir (escaneá el QR)",
        )

    menu_por_id = _validar_items_o_422(db, mesa.restaurante_id, datos.items)

    pedido = Pedido(
        mesa_id=mesa.id,
        restaurante_id=mesa.restaurante_id,
        cliente_id=usuario.id if usuario else None,
        sesion_mesa_id=sesion.id if sesion else None,
        nombre_invitado=nombre_invitado,
    )
    db.add(pedido)
    db.flush()

    _agregar_items(db, pedido, datos.items, menu_por_id)

    db.commit()
    db.refresh(pedido)
    if sesion is not None:
        # El pedido ya quedó en la base — el carrito en vivo se vacía
        # para todos los que estaban viendo esta mesa.
        await gestor_carritos.limpiar(mesa.id)
    return _pedido_a_out(pedido)


async def _crear_pedido_domicilio(
    datos: PedidoCreate, db: Session, usuario: Usuario | None
) -> PedidoOut:
    restaurante = db.get(Restaurante, datos.restaurante_id)
    if restaurante is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Restaurante no encontrado")

    if datos.canal == CanalPedido.DOMICILIO_INTERNO:
        # El cliente pide desde su cuenta, o el mesero/admin lo carga a
        # mano (pedido tomado por teléfono).
        if usuario is None:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED, "Necesitás iniciar sesión para pedir domicilio"
            )
        if usuario.rol not in (Rol.CLIENTE, Rol.MESERO, Rol.ADMIN_RESTAURANTE):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No tiene permiso para esta acción")
    else:
        # Rappi/Didi: no hay integración real con esas plataformas (ver
        # Brain.md) — solo el staff registra que el pedido salió por ahí.
        if usuario is None or usuario.rol not in (Rol.MESERO, Rol.ADMIN_RESTAURANTE):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, "Solo el staff puede registrar este canal"
            )

    if usuario.rol in (Rol.MESERO, Rol.ADMIN_RESTAURANTE) and usuario.restaurante_id != restaurante.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tiene permiso sobre este restaurante")

    menu_por_id = _validar_items_o_422(db, restaurante.id, datos.items)

    es_cliente = usuario.rol == Rol.CLIENTE
    pedido = Pedido(
        mesa_id=None,
        restaurante_id=restaurante.id,
        canal=datos.canal,
        direccion_entrega=datos.direccion_entrega,
        telefono_entrega=datos.telefono_entrega,
        cliente_id=usuario.id if es_cliente else None,
        nombre_invitado=None if es_cliente else f"Tomado por {usuario.nombre}",
    )
    db.add(pedido)
    db.flush()

    _agregar_items(db, pedido, datos.items, menu_por_id)

    db.commit()
    db.refresh(pedido)
    return _pedido_a_out(pedido)


@router.get("/{pedido_id}", response_model=PedidoOut)
def obtener_pedido(
    pedido_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """Para el cliente hacer seguimiento (polling) de su propio pedido de
    domicilio, además de lo que ya cubre `listar_pedidos` para el staff."""
    pedido = db.get(Pedido, pedido_id)
    if pedido is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido no encontrado")
    es_dueno = pedido.cliente_id == usuario.id
    es_staff_restaurante = (
        usuario.rol in ROLES_STAFF_RESTAURANTE and usuario.restaurante_id == pedido.restaurante_id
    )
    if not (es_dueno or es_staff_restaurante):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tiene permiso para ver este pedido")
    return _pedido_a_out(pedido)


# Rango de estados que le pertenece ver a cocina: desde que el mesero
# confirma hasta que el plato queda listo para servir.
ESTADOS_COCINA = (EstadoPedido.CONFIRMADO, EstadoPedido.PREPARANDO, EstadoPedido.LISTO)
# Cola activa de un repartidor: ya salió de cocina, listo para salir o ya
# en camino. Entregado/cancelado no le sirven de default.
ESTADOS_REPARTIDOR = (EstadoPedido.LISTO, EstadoPedido.EN_CAMINO)


@router.get("", response_model=list[PedidoOut])
def listar_pedidos(
    estado: EstadoPedido | None = None,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(
        require_roles(Rol.MESERO, Rol.COCINA, Rol.ADMIN_RESTAURANTE, Rol.REPARTIDOR, Rol.CLIENTE)
    ),
):
    if usuario.rol == Rol.CLIENTE:
        # "Mis pedidos": historial propio del cliente, cruza restaurantes
        # (a diferencia del staff, que solo ve lo de su restaurante). Sin
        # esto no había forma de recuperar el pedido si cerraba la
        # pestaña — el link de seguimiento solo llegaba por el redirect
        # justo después de pedir.
        query = db.query(Pedido).filter(Pedido.cliente_id == usuario.id)
        if estado is not None:
            query = query.filter(Pedido.estado == estado)
        pedidos = query.order_by(Pedido.created_at.desc()).all()
        return [_pedido_a_out(p) for p in pedidos]

    query = db.query(Pedido).filter(Pedido.restaurante_id == usuario.restaurante_id)

    if usuario.rol == Rol.REPARTIDOR:
        # Un repartidor solo ve sus propias entregas asignadas, nunca las
        # de otro compañero.
        query = query.filter(Pedido.repartidor_id == usuario.id)

    if estado is not None:
        query = query.filter(Pedido.estado == estado)
        orden = Pedido.confirmado_at if estado in ESTADOS_COCINA else Pedido.created_at
    elif usuario.rol == Rol.COCINA:
        # Cocina ve por defecto todo lo que sigue activo en su estación, no
        # un único estado puntual. Orden FIFO por hora de llegada a cocina
        # (confirmado_at), no por hora de creación del pedido.
        query = query.filter(Pedido.estado.in_(ESTADOS_COCINA))
        orden = Pedido.confirmado_at
    elif usuario.rol == Rol.REPARTIDOR:
        query = query.filter(Pedido.estado.in_(ESTADOS_REPARTIDOR))
        orden = Pedido.confirmado_at
    else:
        orden = Pedido.created_at

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


@router.post("/{pedido_id}/marcar-preparando", response_model=PedidoOut)
def marcar_preparando(
    pedido_id: int,
    db: Session = Depends(get_db),
    cocina: Usuario = Depends(require_roles(Rol.COCINA, Rol.ADMIN_RESTAURANTE)),
):
    pedido = _get_pedido_del_restaurante_o_404(db, pedido_id, cocina.restaurante_id)
    if pedido.estado != EstadoPedido.CONFIRMADO:
        raise HTTPException(status.HTTP_409_CONFLICT, "El pedido no está confirmado")
    pedido.estado = EstadoPedido.PREPARANDO
    db.commit()
    db.refresh(pedido)
    return _pedido_a_out(pedido)


@router.post("/{pedido_id}/marcar-listo", response_model=PedidoOut)
def marcar_listo(
    pedido_id: int,
    db: Session = Depends(get_db),
    cocina: Usuario = Depends(require_roles(Rol.COCINA, Rol.ADMIN_RESTAURANTE)),
):
    pedido = _get_pedido_del_restaurante_o_404(db, pedido_id, cocina.restaurante_id)
    if pedido.estado != EstadoPedido.PREPARANDO:
        raise HTTPException(status.HTTP_409_CONFLICT, "El pedido no está en preparación")
    pedido.estado = EstadoPedido.LISTO
    db.commit()
    db.refresh(pedido)
    return _pedido_a_out(pedido)


@router.post(
    "/{pedido_id}/prefactura", response_model=FacturaOut, status_code=status.HTTP_201_CREATED
)
def generar_prefactura(
    pedido_id: int,
    datos: FacturaCreate,
    db: Session = Depends(get_db),
    staff: Usuario = Depends(require_roles(Rol.MESERO, Rol.ADMIN_RESTAURANTE)),
):
    """Comprobante para el domicilio interno: el mesero la genera antes de
    asignar repartidor, se la entrega impresa junto con el pedido, el
    repartidor se la lleva y la cobra contra entrega — recién ahí queda
    marcada `pagado` (ver `marcar_entregado`). Nace sin pagar, a
    diferencia de la factura de mesa (esa se asume cobrada al cerrar la
    mesa). No cierra nada del pedido — el estado sigue su curso normal
    por cocina/repartidor."""
    pedido = _get_pedido_del_restaurante_o_404(db, pedido_id, staff.restaurante_id)
    if pedido.canal != CanalPedido.DOMICILIO_INTERNO:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Solo domicilio interno usa prefactura"
        )
    if pedido.estado in (EstadoPedido.CANCELADO, EstadoPedido.ENTREGADO):
        raise HTTPException(status.HTTP_409_CONFLICT, "El pedido ya no está activo")
    if pedido.factura_id is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Este pedido ya tiene prefactura")

    subtotal = sum((i.precio_unitario * i.cantidad for i in pedido.items), Decimal("0"))
    propina = (
        (subtotal * datos.porcentaje_propina).quantize(Decimal("0.01"))
        if datos.incluye_propina
        else Decimal("0")
    )
    total = subtotal + propina

    factura = Factura(
        mesa_id=None,
        restaurante_id=pedido.restaurante_id,
        subtotal=subtotal,
        incluye_propina=datos.incluye_propina,
        propina=propina,
        total=total,
        pagado=False,
    )
    db.add(factura)
    db.flush()
    pedido.factura_id = factura.id
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
        for i in pedido.items
    ]
    return FacturaOut(
        id=factura.id,
        mesa_id=None,
        mesa_numero=None,
        restaurante_id=factura.restaurante_id,
        subtotal=factura.subtotal,
        incluye_propina=factura.incluye_propina,
        propina=factura.propina,
        total=factura.total,
        pagado=factura.pagado,
        pagado_at=factura.pagado_at,
        created_at=factura.created_at,
        items=items_out,
    )


@router.post("/{pedido_id}/asignar-repartidor", response_model=PedidoOut)
def asignar_repartidor(
    pedido_id: int,
    datos: AsignarRepartidor,
    db: Session = Depends(get_db),
    staff: Usuario = Depends(require_roles(Rol.MESERO, Rol.ADMIN_RESTAURANTE)),
):
    pedido = _get_pedido_del_restaurante_o_404(db, pedido_id, staff.restaurante_id)
    if pedido.canal != CanalPedido.DOMICILIO_INTERNO:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Solo pedidos de domicilio interno tienen repartidor"
        )
    if pedido.factura_id is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Generá la prefactura antes de asignar un repartidor",
        )
    repartidor = db.get(Usuario, datos.repartidor_id)
    if (
        repartidor is None
        or repartidor.rol != Rol.REPARTIDOR
        or repartidor.restaurante_id != staff.restaurante_id
    ):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Repartidor no encontrado")
    pedido.repartidor_id = repartidor.id
    db.commit()
    db.refresh(pedido)
    return _pedido_a_out(pedido)


@router.post("/{pedido_id}/marcar-en-camino", response_model=PedidoOut)
def marcar_en_camino(
    pedido_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(
        require_roles(Rol.REPARTIDOR, Rol.MESERO, Rol.ADMIN_RESTAURANTE)
    ),
):
    pedido = _get_pedido_del_restaurante_o_404(db, pedido_id, usuario.restaurante_id)
    if usuario.rol == Rol.REPARTIDOR and pedido.repartidor_id != usuario.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Este pedido no está asignado a vos")
    if pedido.repartidor_id is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "El pedido todavía no tiene repartidor asignado")
    if pedido.estado != EstadoPedido.LISTO:
        raise HTTPException(status.HTTP_409_CONFLICT, "El pedido todavía no está listo")
    pedido.estado = EstadoPedido.EN_CAMINO
    db.commit()
    db.refresh(pedido)
    return _pedido_a_out(pedido)


@router.patch("/{pedido_id}/ubicacion", response_model=PedidoOut)
def actualizar_ubicacion(
    pedido_id: int,
    datos: UbicacionUpdate,
    db: Session = Depends(get_db),
    repartidor: Usuario = Depends(require_roles(Rol.REPARTIDOR)),
):
    pedido = _get_pedido_del_restaurante_o_404(db, pedido_id, repartidor.restaurante_id)
    if pedido.repartidor_id != repartidor.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Este pedido no está asignado a vos")
    if pedido.estado != EstadoPedido.EN_CAMINO:
        raise HTTPException(status.HTTP_409_CONFLICT, "El pedido no está en camino")
    pedido.repartidor_lat = datos.lat
    pedido.repartidor_lng = datos.lng
    pedido.repartidor_actualizado_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(pedido)
    return _pedido_a_out(pedido)


@router.post("/{pedido_id}/marcar-entregado", response_model=PedidoOut)
def marcar_entregado(
    pedido_id: int,
    datos: MarcarEntregadoInput = MarcarEntregadoInput(),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(
        require_roles(Rol.MESERO, Rol.ADMIN_RESTAURANTE, Rol.REPARTIDOR)
    ),
):
    """El mesero confirma que ya llevó el plato a la mesa, o el repartidor
    confirma que ya entregó el domicilio. Separado de `marcar-listo` (que
    es cocina avisando que ya está para servir): solo a partir de acá el
    pedido se puede facturar — no se cobra algo que todavía no llegó a
    destino (ver Brain.md). Si el pedido ya tiene prefactura (domicilio
    interno), entregar también cobra: `pagado` marca la Factura — el
    repartidor cobra contra entrega, no hay paso de pago aparte."""
    pedido = _get_pedido_del_restaurante_o_404(db, pedido_id, usuario.restaurante_id)
    if usuario.rol == Rol.REPARTIDOR and pedido.repartidor_id != usuario.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Este pedido no está asignado a vos")
    if pedido.estado not in (EstadoPedido.LISTO, EstadoPedido.EN_CAMINO):
        raise HTTPException(status.HTTP_409_CONFLICT, "El pedido todavía no está listo")
    pedido.estado = EstadoPedido.ENTREGADO
    if pedido.factura is not None:
        pedido.factura.pagado = datos.pagado
        pedido.factura.pagado_at = datetime.now(timezone.utc) if datos.pagado else None
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
