def _crear_pedido_domicilio(client, headers, restaurante_id, menu_item_id, direccion="Calle 1 # 2-3"):
    return client.post(
        "/pedidos",
        json={
            "canal": "domicilio_interno",
            "restaurante_id": restaurante_id,
            "direccion_entrega": direccion,
            "telefono_entrega": "3001234567",
            "items": [{"menu_item_id": menu_item_id, "cantidad": 1}],
        },
        headers=headers,
    )


def test_cliente_pide_domicilio_interno(client, cliente_autenticado, restaurante_con_mesa):
    r = _crear_pedido_domicilio(
        client,
        cliente_autenticado["headers"],
        restaurante_con_mesa["restaurante"].id,
        restaurante_con_mesa["menu_item"].id,
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["canal"] == "domicilio_interno"
    assert data["mesa_id"] is None
    assert data["mesa_numero"] is None
    assert data["direccion_entrega"] == "Calle 1 # 2-3"
    assert data["estado"] == "pendiente"


def test_domicilio_sin_direccion_falla(client, cliente_autenticado, restaurante_con_mesa):
    r = client.post(
        "/pedidos",
        json={
            "canal": "domicilio_interno",
            "restaurante_id": restaurante_con_mesa["restaurante"].id,
            "items": [{"menu_item_id": restaurante_con_mesa["menu_item"].id, "cantidad": 1}],
        },
        headers=cliente_autenticado["headers"],
    )
    assert r.status_code == 422


def test_guest_no_puede_pedir_domicilio(client, restaurante_con_mesa):
    r = _crear_pedido_domicilio(
        client, {}, restaurante_con_mesa["restaurante"].id, restaurante_con_mesa["menu_item"].id
    )
    assert r.status_code == 401


def test_cliente_no_puede_registrar_rappi(client, cliente_autenticado, restaurante_con_mesa):
    r = client.post(
        "/pedidos",
        json={
            "canal": "rappi",
            "restaurante_id": restaurante_con_mesa["restaurante"].id,
            "items": [{"menu_item_id": restaurante_con_mesa["menu_item"].id, "cantidad": 1}],
        },
        headers=cliente_autenticado["headers"],
    )
    assert r.status_code == 403


def test_mesero_puede_registrar_rappi(client, mesero_autenticado, restaurante_con_mesa):
    r = client.post(
        "/pedidos",
        json={
            "canal": "rappi",
            "restaurante_id": restaurante_con_mesa["restaurante"].id,
            "items": [{"menu_item_id": restaurante_con_mesa["menu_item"].id, "cantidad": 1}],
        },
        headers=mesero_autenticado["headers"],
    )
    assert r.status_code == 201, r.text
    assert r.json()["canal"] == "rappi"


def test_flujo_completo_domicilio_interno_con_repartidor(
    client, cliente_autenticado, mesero_autenticado, cocina_autenticado, repartidor_autenticado, restaurante_con_mesa
):
    pedido = _crear_pedido_domicilio(
        client,
        cliente_autenticado["headers"],
        restaurante_con_mesa["restaurante"].id,
        restaurante_con_mesa["menu_item"].id,
    ).json()
    pedido_id = pedido["id"]

    # Cliente puede ver el estado de su propio pedido (seguimiento).
    r = client.get(f"/pedidos/{pedido_id}", headers=cliente_autenticado["headers"])
    assert r.status_code == 200

    # Otro cliente cualquiera no puede verlo.
    r = client.get(f"/pedidos/{pedido_id}")
    assert r.status_code == 401

    client.post(f"/pedidos/{pedido_id}/confirmar", headers=mesero_autenticado["headers"])
    client.post(f"/pedidos/{pedido_id}/marcar-preparando", headers=cocina_autenticado["headers"])
    client.post(f"/pedidos/{pedido_id}/marcar-listo", headers=cocina_autenticado["headers"])

    r = client.post(
        f"/pedidos/{pedido_id}/asignar-repartidor",
        json={"repartidor_id": repartidor_autenticado["usuario_id"]},
        headers=mesero_autenticado["headers"],
    )
    assert r.status_code == 200, r.text
    assert r.json()["repartidor_nombre"] == "Repartidor fixture"

    r = client.post(
        f"/pedidos/{pedido_id}/marcar-en-camino", headers=repartidor_autenticado["headers"]
    )
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "en_camino"

    r = client.patch(
        f"/pedidos/{pedido_id}/ubicacion",
        json={"lat": 4.65, "lng": -74.05},
        headers=repartidor_autenticado["headers"],
    )
    assert r.status_code == 200, r.text
    assert r.json()["repartidor_lat"] == 4.65

    # El cliente ve la ubicación actualizada al pollear su pedido.
    r = client.get(f"/pedidos/{pedido_id}", headers=cliente_autenticado["headers"])
    assert r.json()["repartidor_lng"] == -74.05

    r = client.post(
        f"/pedidos/{pedido_id}/marcar-entregado", headers=repartidor_autenticado["headers"]
    )
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "entregado"


def test_repartidor_no_puede_marcar_en_camino_pedido_ajeno(
    client, cliente_autenticado, mesero_autenticado, cocina_autenticado, repartidor_autenticado, restaurante_con_mesa
):
    pedido = _crear_pedido_domicilio(
        client,
        cliente_autenticado["headers"],
        restaurante_con_mesa["restaurante"].id,
        restaurante_con_mesa["menu_item"].id,
    ).json()
    pedido_id = pedido["id"]
    client.post(f"/pedidos/{pedido_id}/confirmar", headers=mesero_autenticado["headers"])
    client.post(f"/pedidos/{pedido_id}/marcar-preparando", headers=cocina_autenticado["headers"])
    client.post(f"/pedidos/{pedido_id}/marcar-listo", headers=cocina_autenticado["headers"])

    # Nunca se le asignó este pedido: no puede tomarlo.
    r = client.post(
        f"/pedidos/{pedido_id}/marcar-en-camino", headers=repartidor_autenticado["headers"]
    )
    assert r.status_code == 403


def test_cliente_ve_su_historial_de_pedidos(client, cliente_autenticado, restaurante_con_mesa):
    _crear_pedido_domicilio(
        client,
        cliente_autenticado["headers"],
        restaurante_con_mesa["restaurante"].id,
        restaurante_con_mesa["menu_item"].id,
    )
    r = client.get("/pedidos", headers=cliente_autenticado["headers"])
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 1
    assert all(p["cliente_id"] == cliente_autenticado["usuario_id"] for p in data)


def test_repartidor_solo_ve_sus_pedidos_asignados(
    client, cliente_autenticado, mesero_autenticado, cocina_autenticado, repartidor_autenticado, restaurante_con_mesa
):
    pedido = _crear_pedido_domicilio(
        client,
        cliente_autenticado["headers"],
        restaurante_con_mesa["restaurante"].id,
        restaurante_con_mesa["menu_item"].id,
    ).json()
    pedido_id = pedido["id"]
    client.post(f"/pedidos/{pedido_id}/confirmar", headers=mesero_autenticado["headers"])
    client.post(f"/pedidos/{pedido_id}/marcar-preparando", headers=cocina_autenticado["headers"])
    client.post(f"/pedidos/{pedido_id}/marcar-listo", headers=cocina_autenticado["headers"])

    # Todavía sin asignar: no aparece en la cola del repartidor.
    r = client.get("/pedidos", headers=repartidor_autenticado["headers"])
    assert pedido_id not in [p["id"] for p in r.json()]

    client.post(
        f"/pedidos/{pedido_id}/asignar-repartidor",
        json={"repartidor_id": repartidor_autenticado["usuario_id"]},
        headers=mesero_autenticado["headers"],
    )
    r = client.get("/pedidos", headers=repartidor_autenticado["headers"])
    assert pedido_id in [p["id"] for p in r.json()]
