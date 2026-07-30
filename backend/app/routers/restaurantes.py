import io
import secrets
from datetime import datetime, timedelta, timezone

import qrcode
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import require_roles
from app.core.security import hash_password
from app.models import (
    EstadoMesa,
    EstadoReserva,
    Factura,
    ItemPedido,
    MenuItem,
    Mesa,
    Pedido,
    Reserva,
    Restaurante,
    Rol,
    Usuario,
)
from app.schemas.mesa import MesaCreate, MesaOut
from app.schemas.menu import MenuItemCreate, MenuItemOut, MenuItemUpdate
from app.schemas.reserva import MesaDisponibilidad
from app.schemas.restaurante import (
    EstadisticasRestauranteOut,
    PlatoVendidoOut,
    RestauranteConMenu,
    RestauranteCreate,
    RestauranteOut,
)
from app.schemas.usuario import PersonalCreate, UsuarioOut

router = APIRouter(tags=["restaurantes"])


def _qr_url(restaurante_id: int, mesa_id: int, qr_token: str) -> str:
    return f"{settings.frontend_base_url}/mesa/{restaurante_id}/{mesa_id}?token={qr_token}"


def _mesa_a_out(mesa: Mesa, estado: str | None = None) -> MesaOut:
    return MesaOut(
        id=mesa.id,
        restaurante_id=mesa.restaurante_id,
        numero=mesa.numero,
        capacidad=mesa.capacidad,
        estado=estado if estado is not None else mesa.estado.value,
        qr_generado_at=mesa.qr_generado_at,
        qr_url=_qr_url(mesa.restaurante_id, mesa.id, mesa.qr_token),
    )


def _get_restaurante_o_404(db: Session, restaurante_id: int) -> Restaurante:
    restaurante = db.get(Restaurante, restaurante_id)
    if restaurante is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Restaurante no encontrado")
    return restaurante


def _get_mesa_o_404(db: Session, mesa_id: int) -> Mesa:
    mesa = db.get(Mesa, mesa_id)
    if mesa is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mesa no encontrada")
    return mesa


def _verificar_acceso_restaurante(usuario: Usuario, restaurante_id: int) -> None:
    """admin_general gestiona cualquier restaurante; el resto de roles
    scopeados (admin_restaurante, mesero, cocina) solo el suyo — ver
    Brain.md, bug donde admin_restaurante quedaba con cuenta creada pero
    sin ninguna página real que la usara."""
    if (
        usuario.rol in (Rol.ADMIN_RESTAURANTE, Rol.MESERO, Rol.COCINA)
        and usuario.restaurante_id != restaurante_id
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tiene permiso sobre este restaurante")


@router.post(
    "/restaurantes",
    response_model=RestauranteConMenu,
    status_code=status.HTTP_201_CREATED,
)
def crear_restaurante(
    datos: RestauranteCreate,
    db: Session = Depends(get_db),
    _admin=Depends(require_roles(Rol.ADMIN_GENERAL)),
):
    restaurante = Restaurante(
        nombre=datos.nombre, descripcion=datos.descripcion, categoria=datos.categoria
    )
    db.add(restaurante)
    db.flush()

    for item in datos.menu_inicial:
        db.add(MenuItem(restaurante_id=restaurante.id, **item.model_dump()))

    db.commit()
    db.refresh(restaurante)
    return RestauranteConMenu(
        id=restaurante.id,
        nombre=restaurante.nombre,
        descripcion=restaurante.descripcion,
        categoria=restaurante.categoria,
        created_at=restaurante.created_at,
        mesas_disponibles=False,
        menu=[MenuItemOut.model_validate(m) for m in restaurante.menu_items],
    )


@router.get("/restaurantes", response_model=list[RestauranteOut])
def listar_restaurantes(db: Session = Depends(get_db)):
    restaurantes = db.query(Restaurante).order_by(Restaurante.nombre).all()
    return [
        RestauranteOut(
            id=r.id,
            nombre=r.nombre,
            descripcion=r.descripcion,
            categoria=r.categoria,
            created_at=r.created_at,
            mesas_disponibles=any(m.estado == EstadoMesa.LIBRE for m in r.mesas),
        )
        for r in restaurantes
    ]


@router.get("/restaurantes/{restaurante_id}", response_model=RestauranteConMenu)
def obtener_restaurante(restaurante_id: int, db: Session = Depends(get_db)):
    restaurante = _get_restaurante_o_404(db, restaurante_id)
    return RestauranteConMenu(
        id=restaurante.id,
        nombre=restaurante.nombre,
        descripcion=restaurante.descripcion,
        categoria=restaurante.categoria,
        created_at=restaurante.created_at,
        mesas_disponibles=any(m.estado == EstadoMesa.LIBRE for m in restaurante.mesas),
        menu=[MenuItemOut.model_validate(m) for m in restaurante.menu_items],
    )


@router.get(
    "/restaurantes/{restaurante_id}/estadisticas", response_model=EstadisticasRestauranteOut
)
def obtener_estadisticas(
    restaurante_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_roles(Rol.ADMIN_GENERAL, Rol.ADMIN_RESTAURANTE)),
):
    """Métricas reales del dashboard admin — nada fabricado. `revenue_ayer`
    compara el total facturado del día completo de ayer contra lo que va
    de hoy (no "misma hora de ayer", eso pedía un cálculo que no vale la
    pena para lo que se usa acá). No hay inventario ni notificaciones:
    el dominio no tiene esos conceptos."""
    _get_restaurante_o_404(db, restaurante_id)
    _verificar_acceso_restaurante(admin, restaurante_id)
    ahora = datetime.now(timezone.utc)
    inicio_hoy = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
    inicio_ayer = inicio_hoy - timedelta(days=1)

    def _revenue_desde(inicio: datetime, fin: datetime | None) -> float:
        query = (
            db.query(func.coalesce(func.sum(Factura.total), 0))
            .join(Mesa)
            .filter(Mesa.restaurante_id == restaurante_id, Factura.created_at >= inicio)
        )
        if fin is not None:
            query = query.filter(Factura.created_at < fin)
        return query.scalar()

    revenue_hoy = _revenue_desde(inicio_hoy, None)
    revenue_ayer = _revenue_desde(inicio_ayer, inicio_hoy)
    variacion_pct = (
        float((revenue_hoy - revenue_ayer) / revenue_ayer * 100) if revenue_ayer else None
    )

    mesas_total = db.query(Mesa).filter(Mesa.restaurante_id == restaurante_id).count()
    mesas_ocupadas = (
        db.query(Mesa)
        .filter(Mesa.restaurante_id == restaurante_id, Mesa.estado == EstadoMesa.OCUPADA)
        .count()
    )

    top_platos = (
        db.query(
            MenuItem.id,
            MenuItem.nombre,
            MenuItem.precio,
            func.sum(ItemPedido.cantidad).label("vendidos"),
        )
        .join(ItemPedido, ItemPedido.menu_item_id == MenuItem.id)
        .join(Pedido, Pedido.id == ItemPedido.pedido_id)
        .join(Factura, Factura.id == Pedido.factura_id)
        .filter(MenuItem.restaurante_id == restaurante_id, Factura.created_at >= inicio_hoy)
        .group_by(MenuItem.id, MenuItem.nombre, MenuItem.precio)
        .order_by(func.sum(ItemPedido.cantidad).desc())
        .limit(3)
        .all()
    )

    return EstadisticasRestauranteOut(
        revenue_hoy=revenue_hoy,
        revenue_ayer=revenue_ayer,
        variacion_pct=variacion_pct,
        mesas_ocupadas=mesas_ocupadas,
        mesas_total=mesas_total,
        platos_mas_vendidos_hoy=[
            PlatoVendidoOut(
                menu_item_id=fila.id,
                nombre=fila.nombre,
                cantidad_vendida=int(fila.vendidos),
                precio=fila.precio,
            )
            for fila in top_platos
        ],
    )


@router.post(
    "/restaurantes/{restaurante_id}/menu",
    response_model=MenuItemOut,
    status_code=status.HTTP_201_CREATED,
)
def agregar_item_menu(
    restaurante_id: int,
    datos: MenuItemCreate,
    db: Session = Depends(get_db),
    admin=Depends(require_roles(Rol.ADMIN_GENERAL, Rol.ADMIN_RESTAURANTE)),
):
    _get_restaurante_o_404(db, restaurante_id)
    _verificar_acceso_restaurante(admin, restaurante_id)
    item = MenuItem(restaurante_id=restaurante_id, **datos.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def _get_item_menu_o_404(db: Session, restaurante_id: int, item_id: int) -> MenuItem:
    item = (
        db.query(MenuItem)
        .filter(MenuItem.id == item_id, MenuItem.restaurante_id == restaurante_id)
        .first()
    )
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ítem de menú no encontrado")
    return item


@router.put(
    "/restaurantes/{restaurante_id}/menu/{item_id}",
    response_model=MenuItemOut,
)
def editar_item_menu(
    restaurante_id: int,
    item_id: int,
    datos: MenuItemUpdate,
    db: Session = Depends(get_db),
    admin=Depends(require_roles(Rol.ADMIN_GENERAL, Rol.ADMIN_RESTAURANTE)),
):
    _get_restaurante_o_404(db, restaurante_id)
    _verificar_acceso_restaurante(admin, restaurante_id)
    item = _get_item_menu_o_404(db, restaurante_id, item_id)
    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(item, campo, valor)
    db.commit()
    db.refresh(item)
    return item


@router.post(
    "/restaurantes/{restaurante_id}/personal",
    response_model=UsuarioOut,
    status_code=status.HTTP_201_CREATED,
)
def crear_personal(
    restaurante_id: int,
    datos: PersonalCreate,
    db: Session = Depends(get_db),
    admin=Depends(require_roles(Rol.ADMIN_GENERAL, Rol.ADMIN_RESTAURANTE)),
):
    _get_restaurante_o_404(db, restaurante_id)
    _verificar_acceso_restaurante(admin, restaurante_id)
    usuario = Usuario(
        nombre=datos.nombre,
        email=datos.email,
        password_hash=hash_password(datos.password),
        rol=datos.rol,
        restaurante_id=restaurante_id,
    )
    db.add(usuario)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Email ya registrado")
    db.refresh(usuario)
    return usuario


@router.get("/restaurantes/{restaurante_id}/personal", response_model=list[UsuarioOut])
def listar_personal(
    restaurante_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_roles(Rol.ADMIN_GENERAL, Rol.ADMIN_RESTAURANTE)),
):
    _get_restaurante_o_404(db, restaurante_id)
    _verificar_acceso_restaurante(admin, restaurante_id)
    return (
        db.query(Usuario)
        .filter(Usuario.restaurante_id == restaurante_id)
        .order_by(Usuario.nombre)
        .all()
    )


@router.post(
    "/restaurantes/{restaurante_id}/mesas",
    response_model=MesaOut,
    status_code=status.HTTP_201_CREATED,
)
def crear_mesa(
    restaurante_id: int,
    datos: MesaCreate,
    db: Session = Depends(get_db),
    admin=Depends(require_roles(Rol.ADMIN_GENERAL, Rol.ADMIN_RESTAURANTE)),
):
    _get_restaurante_o_404(db, restaurante_id)
    _verificar_acceso_restaurante(admin, restaurante_id)
    mesa = Mesa(
        restaurante_id=restaurante_id,
        numero=datos.numero,
        capacidad=datos.capacidad,
        qr_token=secrets.token_urlsafe(24),
    )
    db.add(mesa)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Ya existe la mesa número {datos.numero} en este restaurante",
        )
    db.refresh(mesa)
    return _mesa_a_out(mesa)


@router.get("/restaurantes/{restaurante_id}/mesas", response_model=list[MesaOut])
def listar_mesas(
    restaurante_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_roles(Rol.ADMIN_GENERAL, Rol.ADMIN_RESTAURANTE, Rol.MESERO)),
):
    # Import acá adentro (no al tope del módulo) para evitar un ciclo de
    # imports entre routers/mesas.py y routers/restaurantes.py.
    from app.routers.mesas import _expirar_reservas_vencidas, _reserva_propia_y_libre

    _get_restaurante_o_404(db, restaurante_id)
    _verificar_acceso_restaurante(admin, restaurante_id)
    mesas = (
        db.query(Mesa).filter(Mesa.restaurante_id == restaurante_id).order_by(Mesa.numero).all()
    )
    salida = []
    for mesa in mesas:
        _expirar_reservas_vencidas(db, mesa.id)
        if mesa.estado == EstadoMesa.OCUPADA:
            estado = "ocupada"
        else:
            _, mesa_libre_ahora = _reserva_propia_y_libre(db, mesa, None)
            estado = "libre" if mesa_libre_ahora else "reservada"
        salida.append(_mesa_a_out(mesa, estado=estado))
    return salida


def _se_solapan(inicio_a: datetime, fin_a: datetime, inicio_b: datetime, fin_b: datetime) -> bool:
    return inicio_a < fin_b and inicio_b < fin_a


@router.get(
    "/restaurantes/{restaurante_id}/disponibilidad",
    response_model=list[MesaDisponibilidad],
)
def disponibilidad_mesas(
    restaurante_id: int,
    inicio: datetime,
    duracion_minutos: int = 90,
    db: Session = Depends(get_db),
):
    _get_restaurante_o_404(db, restaurante_id)
    if inicio.tzinfo is None:
        inicio = inicio.replace(tzinfo=timezone.utc)
    fin = inicio + timedelta(minutes=duracion_minutos)

    mesas = (
        db.query(Mesa).filter(Mesa.restaurante_id == restaurante_id).order_by(Mesa.numero).all()
    )
    reservas_activas = (
        db.query(Reserva)
        .join(Mesa)
        .filter(Mesa.restaurante_id == restaurante_id, Reserva.estado == EstadoReserva.ACTIVA)
        .all()
    )

    ocupadas = set()
    for r in reservas_activas:
        r_fin = r.inicio + timedelta(minutes=r.duracion_minutos)
        if _se_solapan(inicio, fin, r.inicio, r_fin):
            ocupadas.add(r.mesa_id)

    return [
        MesaDisponibilidad(
            mesa_id=m.id,
            numero=m.numero,
            capacidad=m.capacidad,
            disponible=m.id not in ocupadas,
        )
        for m in mesas
    ]


@router.get("/mesas/{mesa_id}/qr.png")
def obtener_qr_png(
    mesa_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_roles(Rol.ADMIN_GENERAL, Rol.ADMIN_RESTAURANTE)),
):
    mesa = _get_mesa_o_404(db, mesa_id)
    _verificar_acceso_restaurante(admin, mesa.restaurante_id)
    url = _qr_url(mesa.restaurante_id, mesa.id, mesa.qr_token)
    imagen = qrcode.make(url)
    buffer = io.BytesIO()
    imagen.save(buffer, format="PNG")
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="image/png")


@router.post("/mesas/{mesa_id}/regenerar-qr", response_model=MesaOut)
def regenerar_qr(
    mesa_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_roles(Rol.ADMIN_GENERAL, Rol.ADMIN_RESTAURANTE)),
):
    mesa = _get_mesa_o_404(db, mesa_id)
    _verificar_acceso_restaurante(admin, mesa.restaurante_id)
    # El token viejo queda invalidado al sobreescribirse: cualquier QR
    # impreso con el token anterior deja de resolver a esta mesa.
    mesa.qr_token = secrets.token_urlsafe(24)
    db.commit()
    db.refresh(mesa)
    return _mesa_a_out(mesa)
