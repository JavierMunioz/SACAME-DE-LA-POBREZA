import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user_opcional
from app.models import EstadoMesa, EstadoReserva, Mesa, Reserva, Rol, SesionMesa, Usuario
from app.schemas.mesa import MesaQrInfo, OcuparMesaRequest, SesionMesaOut, UnirseMesaRequest
from app.schemas.menu import MenuItemOut

router = APIRouter(prefix="/mesas", tags=["mesas"])

# Ventana de gracia para la llegada: el cliente debe hacer check-in hasta
# 15 min antes de su reserva (ver Readme.md) o la reserva se libera sola.
MINUTOS_LLEGADA_ANTICIPADA = 15


def _expirar_reservas_vencidas(db: Session, mesa_id: int) -> None:
    """Libera reservas activas sin check-in cuyo plazo (inicio - 15 min)
    ya pasó. Se corre al vuelo en cada lectura relevante en vez de con un
    job en background, que no existe en este proyecto."""
    ahora = datetime.now(timezone.utc)
    reservas = (
        db.query(Reserva)
        .filter(
            Reserva.mesa_id == mesa_id,
            Reserva.estado == EstadoReserva.ACTIVA,
            Reserva.check_in_at.is_(None),
        )
        .all()
    )
    hubo_cambios = False
    for r in reservas:
        deadline = r.inicio - timedelta(minutes=MINUTOS_LLEGADA_ANTICIPADA)
        # Reserva de último momento (hecha después de su propio plazo de
        # check-in, ej. "reservo para ahora mismo"): no tuvo ventana real
        # para hacer check-in con anticipación, así que no se le aplica.
        if r.created_at >= deadline:
            continue
        if ahora >= deadline:
            r.estado = EstadoReserva.EXPIRADA
            hubo_cambios = True
    if hubo_cambios:
        db.commit()


def _reserva_propia_y_libre(
    db: Session, mesa: Mesa, usuario: Usuario | None
) -> tuple[Reserva | None, bool]:
    ahora = datetime.now(timezone.utc)
    reservas_activas = (
        db.query(Reserva)
        .filter(Reserva.mesa_id == mesa.id, Reserva.estado == EstadoReserva.ACTIVA)
        .all()
    )
    reserva_propia = None
    mesa_libre_ahora = True
    for r in reservas_activas:
        ventana_inicio = r.inicio - timedelta(minutes=MINUTOS_LLEGADA_ANTICIPADA)
        ventana_fin = r.inicio + timedelta(minutes=r.duracion_minutos)
        if ventana_inicio <= ahora <= ventana_fin:
            mesa_libre_ahora = False
            if usuario is not None and r.cliente_id == usuario.id:
                reserva_propia = r
    return reserva_propia, mesa_libre_ahora


def _sesion_activa(db: Session, mesa_id: int) -> SesionMesa | None:
    return (
        db.query(SesionMesa)
        .filter(SesionMesa.mesa_id == mesa_id, SesionMesa.cerrada_at.is_(None))
        .first()
    )


def _sesion_a_out(sesion: SesionMesa, nombre: str) -> SesionMesaOut:
    return SesionMesaOut(
        token=sesion.token,
        codigo_acceso=sesion.codigo_acceso,
        mesa_id=sesion.mesa_id,
        nombre=nombre,
    )


@router.get("/qr/{token}", response_model=MesaQrInfo)
def canjear_qr(
    token: str,
    db: Session = Depends(get_db),
    usuario: Usuario | None = Depends(get_current_user_opcional),
):
    mesa = db.query(Mesa).filter(Mesa.qr_token == token).first()
    if mesa is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Código QR inválido")

    _expirar_reservas_vencidas(db, mesa.id)
    reserva_propia, mesa_libre_ahora = _reserva_propia_y_libre(db, mesa, usuario)
    sesion = _sesion_activa(db, mesa.id)

    if sesion is not None:
        estado = "ocupada"
    elif not mesa_libre_ahora:
        estado = "reservada"
    else:
        estado = "libre"

    return MesaQrInfo(
        mesa_id=mesa.id,
        restaurante_id=mesa.restaurante_id,
        restaurante_nombre=mesa.restaurante.nombre,
        numero=mesa.numero,
        capacidad=mesa.capacidad,
        reserva_propia=reserva_propia,
        mesa_libre_ahora=mesa_libre_ahora,
        estado=estado,
        requiere_codigo=sesion is not None,
        menu=[MenuItemOut.model_validate(m) for m in mesa.restaurante.menu_items],
    )


@router.post(
    "/{mesa_id}/ocupar", response_model=SesionMesaOut, status_code=status.HTTP_201_CREATED
)
def ocupar_mesa(
    mesa_id: int,
    datos: OcuparMesaRequest,
    db: Session = Depends(get_db),
    usuario: Usuario | None = Depends(get_current_user_opcional),
):
    mesa = db.get(Mesa, mesa_id)
    if mesa is None or mesa.qr_token != datos.qr_token:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Código QR inválido")

    _expirar_reservas_vencidas(db, mesa.id)

    if _sesion_activa(db, mesa.id) is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Esta mesa ya está ocupada. Pedile el código de 4 dígitos a quien la abrió.",
        )

    reserva: Reserva | None = None
    nombre_invitado: str | None = None

    if datos.reserva_id is not None:
        if usuario is None or usuario.rol != Rol.CLIENTE:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No tiene permiso para esta acción")
        reserva = db.get(Reserva, datos.reserva_id)
        if (
            reserva is None
            or reserva.mesa_id != mesa.id
            or reserva.cliente_id != usuario.id
            or reserva.estado != EstadoReserva.ACTIVA
        ):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Reserva no encontrada o vencida")
        reserva.check_in_at = datetime.now(timezone.utc)
    else:
        _, mesa_libre_ahora = _reserva_propia_y_libre(db, mesa, usuario)
        if not mesa_libre_ahora:
            raise HTTPException(
                status.HTTP_409_CONFLICT, "Esta mesa está reservada en este horario"
            )
        if usuario is not None and usuario.rol != Rol.CLIENTE:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No tiene permiso para esta acción")
        if usuario is None:
            if not datos.nombre_invitado or not datos.nombre_invitado.strip():
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "Necesitamos tu nombre para abrir la mesa",
                )
            nombre_invitado = datos.nombre_invitado.strip()

    sesion = SesionMesa(
        mesa_id=mesa.id,
        cliente_id=usuario.id if usuario is not None else None,
        nombre_invitado=nombre_invitado,
        reserva_id=reserva.id if reserva is not None else None,
        token=secrets.token_urlsafe(32),
        codigo_acceso=f"{secrets.randbelow(10000):04d}",
    )
    db.add(sesion)
    mesa.estado = EstadoMesa.OCUPADA
    db.commit()
    db.refresh(sesion)

    nombre = usuario.nombre if usuario is not None else nombre_invitado or ""
    return _sesion_a_out(sesion, nombre)


@router.post("/{mesa_id}/unirse", response_model=SesionMesaOut)
def unirse_a_mesa(
    mesa_id: int,
    datos: UnirseMesaRequest,
    db: Session = Depends(get_db),
):
    mesa = db.get(Mesa, mesa_id)
    if mesa is None or mesa.qr_token != datos.qr_token:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Código QR inválido")

    sesion = _sesion_activa(db, mesa.id)
    if sesion is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Esta mesa no tiene una sesión activa")
    if sesion.codigo_acceso != datos.codigo_acceso.strip():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Código incorrecto")

    nombre = (
        sesion.cliente.nombre if sesion.cliente_id is not None else (sesion.nombre_invitado or "")
    )
    return _sesion_a_out(sesion, nombre)
