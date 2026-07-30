import io
import secrets

import qrcode
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import require_roles
from app.models import MenuItem, Mesa, Restaurante, Rol
from app.schemas.mesa import MesaCreate, MesaOut
from app.schemas.menu import MenuItemCreate, MenuItemOut
from app.schemas.restaurante import RestauranteConMenu, RestauranteCreate, RestauranteOut

router = APIRouter(tags=["restaurantes"])


def _qr_url(restaurante_id: int, mesa_id: int, qr_token: str) -> str:
    return f"{settings.frontend_base_url}/mesa/{restaurante_id}/{mesa_id}?token={qr_token}"


def _mesa_a_out(mesa: Mesa) -> MesaOut:
    return MesaOut(
        id=mesa.id,
        restaurante_id=mesa.restaurante_id,
        numero=mesa.numero,
        capacidad=mesa.capacidad,
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
    restaurante = Restaurante(nombre=datos.nombre, descripcion=datos.descripcion)
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
        created_at=restaurante.created_at,
        menu=[MenuItemOut.model_validate(m) for m in restaurante.menu_items],
    )


@router.get("/restaurantes", response_model=list[RestauranteOut])
def listar_restaurantes(db: Session = Depends(get_db)):
    return db.query(Restaurante).order_by(Restaurante.nombre).all()


@router.get("/restaurantes/{restaurante_id}", response_model=RestauranteConMenu)
def obtener_restaurante(restaurante_id: int, db: Session = Depends(get_db)):
    restaurante = _get_restaurante_o_404(db, restaurante_id)
    return RestauranteConMenu(
        id=restaurante.id,
        nombre=restaurante.nombre,
        descripcion=restaurante.descripcion,
        created_at=restaurante.created_at,
        menu=[MenuItemOut.model_validate(m) for m in restaurante.menu_items],
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
    _admin=Depends(require_roles(Rol.ADMIN_GENERAL)),
):
    _get_restaurante_o_404(db, restaurante_id)
    item = MenuItem(restaurante_id=restaurante_id, **datos.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.post(
    "/restaurantes/{restaurante_id}/mesas",
    response_model=MesaOut,
    status_code=status.HTTP_201_CREATED,
)
def crear_mesa(
    restaurante_id: int,
    datos: MesaCreate,
    db: Session = Depends(get_db),
    _admin=Depends(require_roles(Rol.ADMIN_GENERAL)),
):
    _get_restaurante_o_404(db, restaurante_id)
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
    _admin=Depends(require_roles(Rol.ADMIN_GENERAL)),
):
    _get_restaurante_o_404(db, restaurante_id)
    mesas = (
        db.query(Mesa).filter(Mesa.restaurante_id == restaurante_id).order_by(Mesa.numero).all()
    )
    return [_mesa_a_out(m) for m in mesas]


@router.get("/mesas/{mesa_id}/qr.png")
def obtener_qr_png(
    mesa_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(require_roles(Rol.ADMIN_GENERAL)),
):
    mesa = _get_mesa_o_404(db, mesa_id)
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
    _admin=Depends(require_roles(Rol.ADMIN_GENERAL)),
):
    mesa = _get_mesa_o_404(db, mesa_id)
    # El token viejo queda invalidado al sobreescribirse: cualquier QR
    # impreso con el token anterior deja de resolver a esta mesa.
    mesa.qr_token = secrets.token_urlsafe(24)
    db.commit()
    db.refresh(mesa)
    return _mesa_a_out(mesa)
