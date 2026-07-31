def test_llamar_mesero_marca_la_sesion(client, restaurante_con_mesa, mesero_autenticado):
    mesa = restaurante_con_mesa["mesa"]
    restaurante_id = restaurante_con_mesa["restaurante"].id
    client.post(
        f"/mesas/{mesa.id}/ocupar", json={"qr_token": mesa.qr_token, "nombre_invitado": "Ana"}
    )

    r = client.post(f"/mesas/{mesa.id}/llamar-mesero")
    assert r.status_code == 200

    mesas = client.get(
        f"/restaurantes/{restaurante_id}/mesas", headers=mesero_autenticado["headers"]
    ).json()
    mesa_out = next(m for m in mesas if m["id"] == mesa.id)
    assert mesa_out["llamado_mesero"] is True


def test_llamar_mesero_sin_sesion_falla(client, restaurante_con_mesa):
    mesa = restaurante_con_mesa["mesa"]
    r = client.post(f"/mesas/{mesa.id}/llamar-mesero")
    assert r.status_code == 409


def test_mesero_atiende_el_llamado(client, restaurante_con_mesa, mesero_autenticado):
    mesa = restaurante_con_mesa["mesa"]
    restaurante_id = restaurante_con_mesa["restaurante"].id
    client.post(
        f"/mesas/{mesa.id}/ocupar", json={"qr_token": mesa.qr_token, "nombre_invitado": "Ana"}
    )
    client.post(f"/mesas/{mesa.id}/llamar-mesero")

    r = client.post(f"/mesas/{mesa.id}/atender-llamado", headers=mesero_autenticado["headers"])
    assert r.status_code == 200

    mesas = client.get(
        f"/restaurantes/{restaurante_id}/mesas", headers=mesero_autenticado["headers"]
    ).json()
    mesa_out = next(m for m in mesas if m["id"] == mesa.id)
    assert mesa_out["llamado_mesero"] is False


def test_canjear_qr_incluye_datos_reales_del_restaurante(client, restaurante_con_mesa):
    mesa = restaurante_con_mesa["mesa"]
    r = client.get(f"/mesas/qr/{mesa.qr_token}")
    data = r.json()
    assert data["restaurante_nombre"] == restaurante_con_mesa["restaurante"].nombre
    assert "restaurante_descripcion" in data
    assert "restaurante_categoria" in data
