from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.usuario import Rol


class UsuarioRegistro(BaseModel):
    nombre: str
    email: EmailStr
    password: str


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    email: EmailStr
    rol: Rol


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
