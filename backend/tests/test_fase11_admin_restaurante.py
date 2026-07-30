from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import Restaurante, Rol, Usuario


def _crear_admin_restaurante(client, restaurante_id: int, email: str):
    db = SessionLocal()
    db.add(
        Usuario(
            nombre="Admin del local",
            email=email,
            password_hash=hash_password("clave12345"),
            rol=Rol.ADMIN_RESTAURANTE,
            restaurante_id=restaurante_id,
        )
    )
    db.commit()
    db.close()
    login = client.post("/auth/login", data={"username": email, "password": "clave12345"})
    token = login.json()["access_token"]
    return {"token": token, "headers": {"Authorization": f"Bearer {token}"}}


def test_auth_me_incluye_restaurante_id(client, restaurante_con_mesa):
    admin = _crear_admin_restaurante(
        client, restaurante_con_mesa["restaurante"].id, "admin-local1@sacame-tests.dev"
    )
    r = client.get("/auth/me", headers=admin["headers"])
    assert r.status_code == 200
    assert r.json()["restaurante_id"] == restaurante_con_mesa["restaurante"].id


def test_admin_restaurante_gestiona_su_propio_restaurante(client, restaurante_con_mesa):
    restaurante_id = restaurante_con_mesa["restaurante"].id
    admin = _crear_admin_restaurante(client, restaurante_id, "admin-local2@sacame-tests.dev")

    # Puede ver estadísticas, listar mesas/personal y crear una mesa en
    # SU restaurante — antes de este fix, admin_restaurante no tenía
    # ninguna página real ni permiso backend, quedaba con una cuenta
    # inutilizable (ver Brain.md).
    assert client.get(
        f"/restaurantes/{restaurante_id}/estadisticas", headers=admin["headers"]
    ).status_code == 200
    assert client.get(
        f"/restaurantes/{restaurante_id}/mesas", headers=admin["headers"]
    ).status_code == 200
    assert client.get(
        f"/restaurantes/{restaurante_id}/personal", headers=admin["headers"]
    ).status_code == 200
    r = client.post(
        f"/restaurantes/{restaurante_id}/mesas",
        json={"numero": 99, "capacidad": 2},
        headers=admin["headers"],
    )
    assert r.status_code == 201


def test_admin_restaurante_no_accede_a_otro_restaurante(client, restaurante_con_mesa):
    restaurante_id = restaurante_con_mesa["restaurante"].id
    admin = _crear_admin_restaurante(client, restaurante_id, "admin-local3@sacame-tests.dev")

    db = SessionLocal()
    otro = Restaurante(nombre="Otro restaurante (test)")
    db.add(otro)
    db.commit()
    otro_id = otro.id
    db.close()

    try:
        r = client.get(f"/restaurantes/{otro_id}/estadisticas", headers=admin["headers"])
        assert r.status_code == 403
        r = client.get(f"/restaurantes/{otro_id}/mesas", headers=admin["headers"])
        assert r.status_code == 403
        r = client.post(
            f"/restaurantes/{otro_id}/mesas",
            json={"numero": 1, "capacidad": 2},
            headers=admin["headers"],
        )
        assert r.status_code == 403
    finally:
        db = SessionLocal()
        db.query(Restaurante).filter(Restaurante.id == otro_id).delete()
        db.commit()
        db.close()


def test_admin_restaurante_no_puede_crear_restaurantes(client, restaurante_con_mesa):
    admin = _crear_admin_restaurante(
        client, restaurante_con_mesa["restaurante"].id, "admin-local4@sacame-tests.dev"
    )
    r = client.post(
        "/restaurantes",
        json={"nombre": "Uno nuevo", "menu_inicial": []},
        headers=admin["headers"],
    )
    assert r.status_code == 403
