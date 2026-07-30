def _pedido_confirmado(client, restaurante_con_mesa, cliente_autenticado, mesero_autenticado):
    r = client.post(
        "/pedidos",
        json={
            "mesa_id": restaurante_con_mesa["mesa"].id,
            "items": [{"menu_item_id": restaurante_con_mesa["menu_item"].id, "cantidad": 1}],
        },
        headers=cliente_autenticado["headers"],
    )
    pedido_id = r.json()["id"]
    client.post(f"/pedidos/{pedido_id}/confirmar", headers=mesero_autenticado["headers"])
    return pedido_id


def test_cocina_marca_preparando_y_listo(
    client, restaurante_con_mesa, cliente_autenticado, mesero_autenticado, cocina_autenticado
):
    pedido_id = _pedido_confirmado(
        client, restaurante_con_mesa, cliente_autenticado, mesero_autenticado
    )

    r = client.post(f"/pedidos/{pedido_id}/marcar-preparando", headers=cocina_autenticado["headers"])
    assert r.status_code == 200
    assert r.json()["estado"] == "preparando"

    r2 = client.post(f"/pedidos/{pedido_id}/marcar-listo", headers=cocina_autenticado["headers"])
    assert r2.status_code == 200
    assert r2.json()["estado"] == "listo"


def test_no_se_puede_saltar_de_confirmado_a_listo(
    client, restaurante_con_mesa, cliente_autenticado, mesero_autenticado, cocina_autenticado
):
    pedido_id = _pedido_confirmado(
        client, restaurante_con_mesa, cliente_autenticado, mesero_autenticado
    )
    r = client.post(f"/pedidos/{pedido_id}/marcar-listo", headers=cocina_autenticado["headers"])
    assert r.status_code == 409


def test_cocina_ve_confirmado_preparando_y_listo_sin_filtro(
    client, restaurante_con_mesa, cliente_autenticado, mesero_autenticado, cocina_autenticado
):
    pedido_id = _pedido_confirmado(
        client, restaurante_con_mesa, cliente_autenticado, mesero_autenticado
    )
    client.post(f"/pedidos/{pedido_id}/marcar-preparando", headers=cocina_autenticado["headers"])

    r = client.get("/pedidos", headers=cocina_autenticado["headers"])
    assert r.status_code == 200
    ids = [p["id"] for p in r.json()]
    assert pedido_id in ids


def test_mesero_no_puede_marcar_preparando(
    client, restaurante_con_mesa, cliente_autenticado, mesero_autenticado
):
    pedido_id = _pedido_confirmado(
        client, restaurante_con_mesa, cliente_autenticado, mesero_autenticado
    )
    r = client.post(f"/pedidos/{pedido_id}/marcar-preparando", headers=mesero_autenticado["headers"])
    assert r.status_code == 403


def test_facturar_incluye_pedidos_en_preparando_y_listo(
    client, restaurante_con_mesa, cliente_autenticado, mesero_autenticado, cocina_autenticado
):
    mesa_id = restaurante_con_mesa["mesa"].id
    pedido_id = _pedido_confirmado(
        client, restaurante_con_mesa, cliente_autenticado, mesero_autenticado
    )
    client.post(f"/pedidos/{pedido_id}/marcar-preparando", headers=cocina_autenticado["headers"])
    client.post(f"/pedidos/{pedido_id}/marcar-listo", headers=cocina_autenticado["headers"])

    r = client.post(
        f"/mesas/{mesa_id}/factura",
        json={"incluye_propina": False},
        headers=mesero_autenticado["headers"],
    )
    assert r.status_code == 201
    assert len(r.json()["items"]) == 1
