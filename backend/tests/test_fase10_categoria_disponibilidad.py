def test_listar_restaurantes_incluye_categoria_y_disponibilidad(client, restaurante_con_mesa):
    r = client.get("/restaurantes")
    assert r.status_code == 200
    fila = next(x for x in r.json() if x["id"] == restaurante_con_mesa["restaurante"].id)
    assert fila["categoria"] is None
    assert fila["mesas_disponibles"] is True


def test_ocupar_mesa_hace_que_no_haya_disponibilidad(client, restaurante_con_mesa):
    mesa = restaurante_con_mesa["mesa"]
    client.post(
        f"/mesas/{mesa.id}/ocupar",
        json={"qr_token": mesa.qr_token, "nombre_invitado": "Ana"},
    )
    r = client.get("/restaurantes")
    fila = next(x for x in r.json() if x["id"] == restaurante_con_mesa["restaurante"].id)
    assert fila["mesas_disponibles"] is False


def test_crear_restaurante_con_categoria(client, admin_autenticado):
    r = client.post(
        "/restaurantes",
        json={"nombre": "Sushi test", "categoria": "Sushi", "menu_inicial": []},
        headers=admin_autenticado["headers"],
    )
    assert r.status_code == 201
    assert r.json()["categoria"] == "Sushi"

    from app.core.database import SessionLocal
    from app.models import Restaurante

    db = SessionLocal()
    db.query(Restaurante).filter(Restaurante.nombre == "Sushi test").delete()
    db.commit()
    db.close()
