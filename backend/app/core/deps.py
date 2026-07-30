import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models import Rol, Usuario

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
# auto_error=False: no revienta si no hay header Authorization, para las
# rutas que aceptan tanto invitado (sin cuenta) como cliente logueado.
oauth2_scheme_opcional = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

_credentials_error = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="No se pudo validar la credencial",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> Usuario:
    try:
        payload = decode_access_token(token)
        email = payload.get("sub")
        if email is None:
            raise _credentials_error
    except jwt.PyJWTError:
        raise _credentials_error

    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if usuario is None:
        raise _credentials_error
    return usuario


def get_current_user_opcional(
    token: str | None = Depends(oauth2_scheme_opcional), db: Session = Depends(get_db)
) -> Usuario | None:
    """Como get_current_user, pero devuelve None en vez de 401 si no hay
    token o es inválido — para el flujo de invitado sin cuenta (escanear
    QR, ver menú y pedir sin loguearse)."""
    if token is None:
        return None
    try:
        payload = decode_access_token(token)
        email = payload.get("sub")
    except jwt.PyJWTError:
        return None
    if email is None:
        return None
    return db.query(Usuario).filter(Usuario.email == email).first()


def require_roles(*roles: Rol):
    def dependency(usuario: Usuario = Depends(get_current_user)) -> Usuario:
        if usuario.rol not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permiso para esta acción",
            )
        return usuario

    return dependency
