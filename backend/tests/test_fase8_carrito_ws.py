def test_ws_sincroniza_carrito_entre_dos_conexiones(client, restaurante_con_mesa):
    mesa = restaurante_con_mesa["mesa"]
    item_id = restaurante_con_mesa["menu_item"].id

    ocupar = client.post(
        f"/mesas/{mesa.id}/ocupar",
        json={"qr_token": mesa.qr_token, "nombre_invitado": "Ana"},
    )
    token = ocupar.json()["token"]

    with client.websocket_connect(f"/mesas/{mesa.id}/ws?token={token}") as ws_dueno:
        snapshot_inicial = ws_dueno.receive_json()
        assert snapshot_inicial == {"tipo": "carrito", "items": []}

        with client.websocket_connect(f"/mesas/{mesa.id}/ws?token={token}") as ws_invitado:
            ws_invitado.receive_json()  # snapshot inicial también vacío

            ws_dueno.send_json(
                {"accion": "set_item", "menu_item_id": item_id, "cantidad": 2, "observaciones": None}
            )

            actualizado_dueno = ws_dueno.receive_json()
            actualizado_invitado = ws_invitado.receive_json()
            assert actualizado_dueno == actualizado_invitado
            assert actualizado_dueno["items"] == [
                {"menu_item_id": item_id, "cantidad": 2, "observaciones": None}
            ]

            ws_invitado.send_json(
                {"accion": "set_item", "menu_item_id": item_id, "cantidad": 0, "observaciones": None}
            )
            vaciado = ws_dueno.receive_json()
            assert vaciado["items"] == []


def test_ws_rechaza_token_invalido(client, restaurante_con_mesa):
    mesa = restaurante_con_mesa["mesa"]
    from starlette.websockets import WebSocketDisconnect

    try:
        with client.websocket_connect(f"/mesas/{mesa.id}/ws?token=no-existe"):
            pass
        assert False, "debería haber cerrado la conexión"
    except WebSocketDisconnect as exc:
        assert exc.code == 4401
