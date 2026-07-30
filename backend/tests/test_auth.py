from fastapi import HTTPException

from app.core.deps import require_roles
from app.models import Rol, Usuario


def test_registro_login_y_me(client):
    r = client.post(
        "/auth/registro",
        json={"nombre": "Test", "email": "a@sacame-tests.dev", "password": "clave12345"},
    )
    assert r.status_code == 201
    assert r.json()["rol"] == "cliente"

    r = client.post(
        "/auth/login", data={"username": "a@sacame-tests.dev", "password": "clave12345"}
    )
    assert r.status_code == 200
    token = r.json()["access_token"]

    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "a@sacame-tests.dev"


def test_registro_email_duplicado(client):
    payload = {"nombre": "Dup", "email": "dup@sacame-tests.dev", "password": "clave12345"}
    assert client.post("/auth/registro", json=payload).status_code == 201
    assert client.post("/auth/registro", json=payload).status_code == 409


def test_login_password_incorrecta(client):
    client.post(
        "/auth/registro",
        json={"nombre": "Test2", "email": "b@sacame-tests.dev", "password": "clave12345"},
    )
    r = client.post("/auth/login", data={"username": "b@sacame-tests.dev", "password": "mala"})
    assert r.status_code == 401


def test_me_sin_token(client):
    assert client.get("/auth/me").status_code == 401


def test_require_roles_bloquea_rol_incorrecto():
    dependency = require_roles(Rol.ADMIN_GENERAL)
    usuario_cliente = Usuario(nombre="x", email="x@x.com", password_hash="x", rol=Rol.CLIENTE)

    try:
        dependency(usuario=usuario_cliente)
        assert False, "debería haber lanzado 403"
    except HTTPException as e:
        assert e.status_code == 403


def test_require_roles_permite_rol_correcto():
    dependency = require_roles(Rol.ADMIN_GENERAL)
    usuario_admin = Usuario(
        nombre="x", email="x@x.com", password_hash="x", rol=Rol.ADMIN_GENERAL
    )

    assert dependency(usuario=usuario_admin) is usuario_admin
