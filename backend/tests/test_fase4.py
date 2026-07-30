import time


def _crear_pedido(client, restaurante_con_mesa, cliente_autenticado):
    r = client.post(
        "/pedidos",
        json={
            "mesa_id": restaurante_con_mesa["mesa"].id,
            "items": [{"menu_item_id": restaurante_con_mesa["menu_item"].id, "cantidad": 1}],
        },
        headers=cliente_autenticado["headers"],
    )
    assert r.status_code == 201
    return r.json()["id"]


def test_cocina_ve_solo_confirmados_en_orden_fifo_por_confirmacion(
    client, restaurante_con_mesa, cliente_autenticado, mesero_autenticado, cocina_autenticado
):
    pedido_a = _crear_pedido(client, restaurante_con_mesa, cliente_autenticado)
    pedido_b = _crear_pedido(client, restaurante_con_mesa, cliente_autenticado)

    # Se confirma B antes que A: si el orden fuera por creación (created_at)
    # en vez de por confirmado_at, A aparecería primero. FIFO real es por
    # hora de llegada a cocina, no de creación del pedido.
    client.post(f"/pedidos/{pedido_b}/confirmar", headers=mesero_autenticado["headers"])
    time.sleep(0.05)
    client.post(f"/pedidos/{pedido_a}/confirmar", headers=mesero_autenticado["headers"])

    r = client.get("/pedidos", params={"estado": "confirmado"}, headers=cocina_autenticado["headers"])
    assert r.status_code == 200
    ids = [p["id"] for p in r.json()]
    assert ids == [pedido_b, pedido_a]
    assert all(p["estado"] == "confirmado" for p in r.json())


def test_cocina_no_ve_pedidos_pendientes_al_filtrar_confirmados(
    client, restaurante_con_mesa, cliente_autenticado, cocina_autenticado
):
    _crear_pedido(client, restaurante_con_mesa, cliente_autenticado)

    r = client.get("/pedidos", params={"estado": "confirmado"}, headers=cocina_autenticado["headers"])
    assert r.json() == []


def test_cocina_no_puede_confirmar_ni_cancelar(
    client, restaurante_con_mesa, cliente_autenticado, cocina_autenticado
):
    pedido_id = _crear_pedido(client, restaurante_con_mesa, cliente_autenticado)

    r = client.post(f"/pedidos/{pedido_id}/confirmar", headers=cocina_autenticado["headers"])
    assert r.status_code == 403

    r2 = client.post(f"/pedidos/{pedido_id}/cancelar", headers=cocina_autenticado["headers"])
    assert r2.status_code == 403
