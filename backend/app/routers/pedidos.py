from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.carrito_mesa import gestor_carritos
from app.core.database import get_db
from app.core.deps import get_current_user_opcional, require_roles
from app.models import EstadoPedido, ItemPedido, MenuItem, Mesa, Pedido, Rol, SesionMesa, Usuario
from app.schemas.pedido import ItemPedidoOut, PedidoCreate, PedidoOut

router = APIRouter(prefix="/pedidos", tags=["pedidos"])


def _pedido_a_out(pedido: Pedido) -> PedidoOut:
    return PedidoOut(
        id=pedido.id,
        mesa_id=pedido.mesa_id,
        mesa_numero=pedido.mesa.numero,
        cliente_id=pedido.cliente_id,
        nombre_invitado=pedido.nombre_invitado,
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
async def crear_pedido(
    datos: PedidoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario | None = Depends(get_current_user_opcional),
):
    # Sin cuenta también se puede pedir (ver Readme: mesa libre sin reserva
    # se puede usar sin fricción). Si hay sesión, tiene que ser un cliente:
    # mesero/cocina/admin no generan pedidos a través de este endpoint.
    if usuario is not None and usuario.rol != Rol.CLIENTE:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tiene permiso para esta acción")

    mesa = db.get(Mesa, datos.mesa_id)
    if mesa is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mesa no encontrada")
    if not datos.items:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "El pedido no tiene items")

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

    pedido = Pedido(
        mesa_id=mesa.id,
        cliente_id=usuario.id if usuario else None,
        sesion_mesa_id=sesion.id if sesion else None,
        nombre_invitado=nombre_invitado,
    )
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
    if sesion is not None:
        # El pedido ya quedó en la base — el carrito en vivo se vacía
        # para todos los que estaban viendo esta mesa.
        await gestor_carritos.limpiar(mesa.id)
    return _pedido_a_out(pedido)


# Rango de estados que le pertenece ver a cocina: desde que el mesero
# confirma hasta que el plato queda listo para servir.
ESTADOS_COCINA = (EstadoPedido.CONFIRMADO, EstadoPedido.PREPARANDO, EstadoPedido.LISTO)


@router.get("", response_model=list[PedidoOut])
def listar_pedidos(
    estado: EstadoPedido | None = None,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(require_roles(Rol.MESERO, Rol.COCINA, Rol.ADMIN_RESTAURANTE)),
):
    query = db.query(Pedido).join(Mesa).filter(Mesa.restaurante_id == usuario.restaurante_id)

    if estado is not None:
        query = query.filter(Pedido.estado == estado)
        orden = Pedido.confirmado_at if estado in ESTADOS_COCINA else Pedido.created_at
    elif usuario.rol == Rol.COCINA:
        # Cocina ve por defecto todo lo que sigue activo en su estación, no
        # un único estado puntual. Orden FIFO por hora de llegada a cocina
        # (confirmado_at), no por hora de creación del pedido.
        query = query.filter(Pedido.estado.in_(ESTADOS_COCINA))
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
