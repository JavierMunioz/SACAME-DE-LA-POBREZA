from pydantic import BaseModel, ConfigDict


class CategoriaCreate(BaseModel):
    nombre: str


class CategoriaUpdate(BaseModel):
    nombre: str | None = None
    orden: int | None = None


class CategoriaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    orden: int
