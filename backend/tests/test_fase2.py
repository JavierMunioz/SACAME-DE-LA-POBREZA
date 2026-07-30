from datetime import datetime, timedelta, timezone


def test_reserva_y_conflicto_doble_reserva(client, restaurante_con_mesa, cliente_autenticado):
    mesa_id = restaurante_con_mesa["mesa"].id
    inicio = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()

    r = client.post(
        "/reservas",
        json={"mesa_id": mesa_id, "inicio": inicio, "duracion_minutos": 90},
        headers=cliente_autenticado["headers"],
    )
    assert r.status_code == 201
    assert r.json()["estado"] == "activa"

    r2 = client.post(
        "/reservas",
        json={"mesa_id": mesa_id, "inicio": inicio, "duracion_minutos": 90},
        headers=cliente_autenticado["headers"],
    )
    assert r2.status_code == 409


def test_disponibilidad_refleja_reserva_activa(client, restaurante_con_mesa, cliente_autenticado):
    restaurante_id = restaurante_con_mesa["restaurante"].id
    mesa_id = restaurante_con_mesa["mesa"].id
    inicio = datetime.now(timezone.utc) + timedelta(days=2)

    r = client.get(
        f"/restaurantes/{restaurante_id}/disponibilidad",
        params={"inicio": inicio.isoformat(), "duracion_minutos": 90},
    )
    assert r.status_code == 200
    assert next(m for m in r.json() if m["mesa_id"] == mesa_id)["disponible"] is True

    client.post(
        "/reservas",
        json={"mesa_id": mesa_id, "inicio": inicio.isoformat(), "duracion_minutos": 90},
        headers=cliente_autenticado["headers"],
    )

    r = client.get(
        f"/restaurantes/{restaurante_id}/disponibilidad",
        params={"inicio": inicio.isoformat(), "duracion_minutos": 90},
    )
    assert next(m for m in r.json() if m["mesa_id"] == mesa_id)["disponible"] is False


def test_canje_qr_mesa_libre(client, restaurante_con_mesa, cliente_autenticado):
    token = restaurante_con_mesa["mesa"].qr_token
    r = client.get(f"/mesas/qr/{token}", headers=cliente_autenticado["headers"])
    assert r.status_code == 200
    data = r.json()
    assert data["mesa_libre_ahora"] is True
    assert data["reserva_propia"] is None


def test_canje_qr_con_reserva_propia(client, restaurante_con_mesa, cliente_autenticado):
    mesa_id = restaurante_con_mesa["mesa"].id
    token = restaurante_con_mesa["mesa"].qr_token
    ahora = datetime.now(timezone.utc)

    client.post(
        "/reservas",
        json={"mesa_id": mesa_id, "inicio": ahora.isoformat(), "duracion_minutos": 90},
        headers=cliente_autenticado["headers"],
    )

    r = client.get(f"/mesas/qr/{token}", headers=cliente_autenticado["headers"])
    data = r.json()
    assert data["mesa_libre_ahora"] is False
    assert data["reserva_propia"] is not None
    assert data["reserva_propia"]["cliente_id"] == cliente_autenticado["usuario_id"]


def test_canje_qr_token_invalido(client, cliente_autenticado):
    r = client.get("/mesas/qr/token-que-no-existe", headers=cliente_autenticado["headers"])
    assert r.status_code == 404


def test_crear_pedido(client, restaurante_con_mesa, cliente_autenticado):
    mesa_id = restaurante_con_mesa["mesa"].id
    menu_item_id = restaurante_con_mesa["menu_item"].id

    r = client.post(
        "/pedidos",
        json={
            "mesa_id": mesa_id,
            "items": [{"menu_item_id": menu_item_id, "cantidad": 2, "observaciones": "sin sal"}],
        },
        headers=cliente_autenticado["headers"],
    )
    assert r.status_code == 201
    data = r.json()
    assert data["estado"] == "pendiente"
    assert len(data["items"]) == 1
    assert data["items"][0]["cantidad"] == 2
    assert data["items"][0]["precio_unitario"] == "10000.00"


def test_crear_pedido_item_de_menu_invalido(client, restaurante_con_mesa, cliente_autenticado):
    mesa_id = restaurante_con_mesa["mesa"].id
    r = client.post(
        "/pedidos",
        json={"mesa_id": mesa_id, "items": [{"menu_item_id": 999999, "cantidad": 1}]},
        headers=cliente_autenticado["headers"],
    )
    assert r.status_code == 422


def test_crear_pedido_requiere_rol_cliente(client, restaurante_con_mesa, admin_autenticado):
    mesa_id = restaurante_con_mesa["mesa"].id
    menu_item_id = restaurante_con_mesa["menu_item"].id
    r = client.post(
        "/pedidos",
        json={"mesa_id": mesa_id, "items": [{"menu_item_id": menu_item_id, "cantidad": 1}]},
        headers=admin_autenticado["headers"],
    )
    assert r.status_code == 403
