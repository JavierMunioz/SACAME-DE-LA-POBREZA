from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.models import Mesa, Reserva, Rol, Usuario
from app.routers.mesas import _expirar_reservas_vencidas
from app.schemas.reserva import ReservaCreate, ReservaOut

router = APIRouter(prefix="/reservas", tags=["reservas"])


@router.post("", response_model=ReservaOut, status_code=status.HTTP_201_CREATED)
def crear_reserva(
    datos: ReservaCreate,
    db: Session = Depends(get_db),
    cliente: Usuario = Depends(require_roles(Rol.CLIENTE)),
):
    if db.get(Mesa, datos.mesa_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mesa no encontrada")

    # Libera primero cualquier reserva vencida sin check-in: si no, una
    # reserva "zombi" (activa mas sin nadie) bloquearía este horario para
    # todos aunque ya debería haberse liberado sola.
    _expirar_reservas_vencidas(db, datos.mesa_id)

    reserva = Reserva(
        mesa_id=datos.mesa_id,
        cliente_id=cliente.id,
        inicio=datos.inicio,
        duracion_minutos=datos.duracion_minutos,
    )
    db.add(reserva)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Esa mesa ya tiene una reserva activa en ese horario",
        )
    db.refresh(reserva)
    return reserva


@router.get("/me", response_model=list[ReservaOut])
def mis_reservas(
    db: Session = Depends(get_db),
    cliente: Usuario = Depends(require_roles(Rol.CLIENTE)),
):
    return (
        db.query(Reserva)
        .filter(Reserva.cliente_id == cliente.id)
        .order_by(Reserva.inicio.desc())
        .all()
    )
