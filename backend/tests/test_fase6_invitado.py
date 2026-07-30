def test_invitado_puede_canjear_qr_de_mesa_libre(client, restaurante_con_mesa):
    token = restaurante_con_mesa["mesa"].qr_token
    r = client.get(f"/mesas/qr/{token}")
    assert r.status_code == 200
    data = r.json()
    assert data["mesa_libre_ahora"] is True
    assert data["reserva_propia"] is None


def test_invitado_puede_crear_pedido_sin_login(client, restaurante_con_mesa):
    r = client.post(
        "/pedidos",
        json={
            "mesa_id": restaurante_con_mesa["mesa"].id,
            "items": [{"menu_item_id": restaurante_con_mesa["menu_item"].id, "cantidad": 1}],
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["cliente_id"] is None
    assert data["estado"] == "pendiente"


def test_mesero_no_puede_pedir_via_endpoint_de_pedidos(
    client, restaurante_con_mesa, mesero_autenticado
):
    r = client.post(
        "/pedidos",
        json={
            "mesa_id": restaurante_con_mesa["mesa"].id,
            "items": [{"menu_item_id": restaurante_con_mesa["menu_item"].id, "cantidad": 1}],
        },
        headers=mesero_autenticado["headers"],
    )
    assert r.status_code == 403
