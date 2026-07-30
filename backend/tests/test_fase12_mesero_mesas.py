from datetime import datetime, timedelta, timezone


def test_mesero_puede_editar_item_menu(client, restaurante_con_mesa, mesero_autenticado):
    item_id = restaurante_con_mesa["menu_item"].id
    restaurante_id = restaurante_con_mesa["restaurante"].id
    r = client.put(
        f"/restaurantes/{restaurante_id}/menu/{item_id}",
        json={"precio": "15000", "disponible": False},
        headers=mesero_autenticado["headers"],
    )
    # mesero no gestiona menú, solo admin_restaurante/admin_general.
    assert r.status_code == 403


def test_admin_restaurante_edita_item_menu(client, restaurante_con_mesa):
    from app.core.database import SessionLocal
    from app.core.security import hash_password
    from app.models import Rol, Usuario

    restaurante_id = restaurante_con_mesa["restaurante"].id
    item_id = restaurante_con_mesa["menu_item"].id

    db = SessionLocal()
    db.add(
        Usuario(
            nombre="Admin local",
            email="admin-menu@sacame-tests.dev",
            password_hash=hash_password("clave12345"),
            rol=Rol.ADMIN_RESTAURANTE,
            restaurante_id=restaurante_id,
        )
    )
    db.commit()
    db.close()
    login = client.post(
        "/auth/login", data={"username": "admin-menu@sacame-tests.dev", "password": "clave12345"}
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    r = client.put(
        f"/restaurantes/{restaurante_id}/menu/{item_id}",
        json={"precio": "15000", "disponible": False},
        headers=headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert float(data["precio"]) == 15000
    assert data["disponible"] is False
    # nombre no se tocó (update parcial).
    assert data["nombre"] == restaurante_con_mesa["menu_item"].nombre


def test_mesero_ve_mesas_de_su_restaurante(client, restaurante_con_mesa, mesero_autenticado):
    restaurante_id = restaurante_con_mesa["restaurante"].id
    r = client.get(f"/restaurantes/{restaurante_id}/mesas", headers=mesero_autenticado["headers"])
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_mesero_ocupa_libera_y_vuelve_a_ocupar_mesa(client, restaurante_con_mesa, mesero_autenticado):
    mesa_id = restaurante_con_mesa["mesa"].id

    r = client.post(
        f"/mesas/{mesa_id}/ocupar-staff",
        json={"nombre_invitado": "Cliente sin celular"},
        headers=mesero_autenticado["headers"],
    )
    assert r.status_code == 201
    assert r.json()["nombre"] == "Cliente sin celular"

    # ya ocupada: no se puede volver a ocupar.
    r2 = client.post(
        f"/mesas/{mesa_id}/ocupar-staff", json={}, headers=mesero_autenticado["headers"]
    )
    assert r2.status_code == 409

    # liberar sin pedidos pendientes: se puede.
    r3 = client.post(f"/mesas/{mesa_id}/liberar", headers=mesero_autenticado["headers"])
    assert r3.status_code == 200
    assert r3.json()["estado"] == "libre"

    qr = client.get(f"/mesas/qr/{restaurante_con_mesa['mesa'].qr_token}").json()
    assert qr["estado"] == "libre"

    # se puede volver a ocupar tras liberar.
    r4 = client.post(
        f"/mesas/{mesa_id}/ocupar-staff", json={}, headers=mesero_autenticado["headers"]
    )
    assert r4.status_code == 201


def test_listar_mesas_expone_codigo_acceso_mientras_este_ocupada(
    client, restaurante_con_mesa, mesero_autenticado
):
    mesa_id = restaurante_con_mesa["mesa"].id
    restaurante_id = restaurante_con_mesa["restaurante"].id

    def _mesa_del_listado():
        r = client.get(
            f"/restaurantes/{restaurante_id}/mesas", headers=mesero_autenticado["headers"]
        )
        return next(m for m in r.json() if m["id"] == mesa_id)

    assert _mesa_del_listado()["codigo_acceso"] is None

    ocupar = client.post(
        f"/mesas/{mesa_id}/ocupar-staff", json={}, headers=mesero_autenticado["headers"]
    )
    codigo = ocupar.json()["codigo_acceso"]
    assert codigo is not None
    assert _mesa_del_listado()["codigo_acceso"] == codigo

    client.post(f"/mesas/{mesa_id}/liberar", headers=mesero_autenticado["headers"])
    assert _mesa_del_listado()["codigo_acceso"] is None

    # se ocupa de nuevo: el código es otro (se regenera por sesión).
    ocupar2 = client.post(
        f"/mesas/{mesa_id}/ocupar-staff", json={}, headers=mesero_autenticado["headers"]
    )
    assert _mesa_del_listado()["codigo_acceso"] == ocupar2.json()["codigo_acceso"]


def test_liberar_mesa_con_pedidos_sin_facturar_se_bloquea(
    client, restaurante_con_mesa, mesero_autenticado
):
    mesa_id = restaurante_con_mesa["mesa"].id
    client.post(
        f"/mesas/{mesa_id}/ocupar-staff",
        json={"nombre_invitado": "Cliente"},
        headers=mesero_autenticado["headers"],
    )
    pedido = client.post(
        "/pedidos",
        json={
            "mesa_id": mesa_id,
            "items": [{"menu_item_id": restaurante_con_mesa["menu_item"].id, "cantidad": 1}],
        },
        headers=mesero_autenticado["headers"],
    )
    assert pedido.status_code == 201

    r = client.post(f"/mesas/{mesa_id}/liberar", headers=mesero_autenticado["headers"])
    assert r.status_code == 409


def test_reserva_rechaza_menos_de_2_horas_de_anticipacion(
    client, restaurante_con_mesa, cliente_autenticado
):
    inicio = datetime.now(timezone.utc) + timedelta(minutes=30)
    r = client.post(
        "/reservas",
        json={"mesa_id": restaurante_con_mesa["mesa"].id, "inicio": inicio.isoformat()},
        headers=cliente_autenticado["headers"],
    )
    assert r.status_code == 422


def test_reserva_con_2_horas_de_anticipacion_se_acepta(
    client, restaurante_con_mesa, cliente_autenticado
):
    inicio = datetime.now(timezone.utc) + timedelta(hours=3)
    r = client.post(
        "/reservas",
        json={"mesa_id": restaurante_con_mesa["mesa"].id, "inicio": inicio.isoformat()},
        headers=cliente_autenticado["headers"],
    )
    assert r.status_code == 201
