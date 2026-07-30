from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import EstadoReserva, Mesa, Reserva, Usuario
from app.schemas.mesa import MesaQrInfo
from app.schemas.menu import MenuItemOut

router = APIRouter(prefix="/mesas", tags=["mesas"])

# Ventana de gracia para la llegada: el cliente debe llegar 15 min antes
# de su reserva (ver Readme.md), y la reserva se considera vigente hasta
# que termina su duración.
MINUTOS_LLEGADA_ANTICIPADA = 15


@router.get("/qr/{token}", response_model=MesaQrInfo)
def canjear_qr(
    token: str,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    mesa = db.query(Mesa).filter(Mesa.qr_token == token).first()
    if mesa is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Código QR inválido")

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
            if r.cliente_id == usuario.id:
                reserva_propia = r

    return MesaQrInfo(
        mesa_id=mesa.id,
        restaurante_id=mesa.restaurante_id,
        restaurante_nombre=mesa.restaurante.nombre,
        numero=mesa.numero,
        capacidad=mesa.capacidad,
        reserva_propia=reserva_propia,
        mesa_libre_ahora=mesa_libre_ahora,
        menu=[MenuItemOut.model_validate(m) for m in mesa.restaurante.menu_items],
    )
