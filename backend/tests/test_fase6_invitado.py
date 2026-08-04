def test_invitado_puede_canjear_qr_de_mesa_libre(client, restaurante_con_mesa):
    token = restaurante_con_mesa["mesa"].qr_token
    r = client.get(f"/mesas/qr/{token}")
    assert r.status_code == 200
    data = r.json()
    assert data["mesa_libre_ahora"] is True
    assert data["reserva_propia"] is None
    assert data["estado"] == "libre"
    assert data["requiere_codigo"] is False


def test_invitado_puede_crear_pedido_sin_login(client, restaurante_con_mesa):
    mesa_id = restaurante_con_mesa["mesa"].id
    ocupar = client.post(
        f"/mesas/{mesa_id}/ocupar",
        json={"qr_token": restaurante_con_mesa["mesa"].qr_token, "nombre_invitado": "Juan"},
    )
    assert ocupar.status_code == 201
    sesion_token = ocupar.json()["token_dueno"]

    r = client.post(
        "/pedidos",
        json={
            "mesa_id": mesa_id,
            "sesion_token": sesion_token,
            "items": [{"menu_item_id": restaurante_con_mesa["menu_item"].id, "cantidad": 1}],
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["cliente_id"] is None
    assert data["nombre_invitado"] == "Juan"
    assert data["estado"] == "pendiente"


def test_invitado_no_puede_pedir_sin_reclamar_mesa(client, restaurante_con_mesa):
    r = client.post(
        "/pedidos",
        json={
            "mesa_id": restaurante_con_mesa["mesa"].id,
            "items": [{"menu_item_id": restaurante_con_mesa["menu_item"].id, "cantidad": 1}],
        },
    )
    assert r.status_code == 401


def test_ocupar_mesa_sin_nombre_falla(client, restaurante_con_mesa):
    r = client.post(
        f"/mesas/{restaurante_con_mesa['mesa'].id}/ocupar",
        json={"qr_token": restaurante_con_mesa["mesa"].qr_token},
    )
    assert r.status_code == 422


def test_mesero_puede_pedir_por_su_mesa(
    client, restaurante_con_mesa, mesero_autenticado
):
    # El mesero puede tomar el pedido si el cliente no tiene forma de
    # pedir desde su celular (ver Brain.md) — pero queda marcado como
    # tomado por él, no como pedido directo de un cliente.
    r = client.post(
        "/pedidos",
        json={
            "mesa_id": restaurante_con_mesa["mesa"].id,
            "items": [{"menu_item_id": restaurante_con_mesa["menu_item"].id, "cantidad": 1}],
        },
        headers=mesero_autenticado["headers"],
    )
    assert r.status_code == 201
    assert r.json()["nombre_invitado"] == "Tomado por Mesero fixture"
    assert r.json()["cliente_id"] is None


def test_cocina_no_puede_pedir_via_endpoint_de_pedidos(
    client, restaurante_con_mesa, cocina_autenticado
):
    r = client.post(
        "/pedidos",
        json={
            "mesa_id": restaurante_con_mesa["mesa"].id,
            "items": [{"menu_item_id": restaurante_con_mesa["menu_item"].id, "cantidad": 1}],
        },
        headers=cocina_autenticado["headers"],
    )
    assert r.status_code == 403
