from typing import Literal

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
    restaurante_id: int | None = None


class PersonalCreate(BaseModel):
    nombre: str
    email: EmailStr
    password: str
    rol: Literal[Rol.MESERO, Rol.COCINA, Rol.ADMIN_RESTAURANTE]


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
