def test_admin_crea_y_lista_categorias(client, restaurante_con_mesa, admin_autenticado):
    restaurante_id = restaurante_con_mesa["restaurante"].id

    r1 = client.post(
        f"/restaurantes/{restaurante_id}/categorias",
        json={"nombre": "Entradas"},
        headers=admin_autenticado["headers"],
    )
    assert r1.status_code == 201
    assert r1.json()["orden"] == 0

    r2 = client.post(
        f"/restaurantes/{restaurante_id}/categorias",
        json={"nombre": "Postres"},
        headers=admin_autenticado["headers"],
    )
    assert r2.status_code == 201
    assert r2.json()["orden"] == 1

    # listar es público, sin auth.
    listado = client.get(f"/restaurantes/{restaurante_id}/categorias")
    assert listado.status_code == 200
    nombres = [c["nombre"] for c in listado.json()]
    assert nombres == ["Entradas", "Postres"]


def test_no_se_puede_repetir_nombre_de_categoria(client, restaurante_con_mesa, admin_autenticado):
    restaurante_id = restaurante_con_mesa["restaurante"].id
    client.post(
        f"/restaurantes/{restaurante_id}/categorias",
        json={"nombre": "Bebidas"},
        headers=admin_autenticado["headers"],
    )
    r = client.post(
        f"/restaurantes/{restaurante_id}/categorias",
        json={"nombre": "Bebidas"},
        headers=admin_autenticado["headers"],
    )
    assert r.status_code == 409


def test_plato_puede_estar_en_varias_categorias(client, restaurante_con_mesa, admin_autenticado):
    restaurante_id = restaurante_con_mesa["restaurante"].id
    cat1 = client.post(
        f"/restaurantes/{restaurante_id}/categorias",
        json={"nombre": "Para compartir"},
        headers=admin_autenticado["headers"],
    ).json()
    cat2 = client.post(
        f"/restaurantes/{restaurante_id}/categorias",
        json={"nombre": "Vegetariano"},
        headers=admin_autenticado["headers"],
    ).json()

    item = client.post(
        f"/restaurantes/{restaurante_id}/menu",
        json={
            "nombre": "Papas bravas",
            "precio": "12000",
            "categoria_ids": [cat1["id"], cat2["id"]],
        },
        headers=admin_autenticado["headers"],
    )
    assert item.status_code == 201
    nombres_categorias = {c["nombre"] for c in item.json()["categorias"]}
    assert nombres_categorias == {"Para compartir", "Vegetariano"}

    # se refleja en el detalle del restaurante.
    detalle = client.get(f"/restaurantes/{restaurante_id}").json()
    plato = next(m for m in detalle["menu"] if m["id"] == item.json()["id"])
    assert {c["nombre"] for c in plato["categorias"]} == {"Para compartir", "Vegetariano"}
    assert {c["nombre"] for c in detalle["categorias_menu"]} == {"Para compartir", "Vegetariano"}


def test_categoria_de_otro_restaurante_se_rechaza(client, restaurante_con_mesa, admin_autenticado):
    from app.core.database import SessionLocal
    from app.models import CategoriaMenu, Restaurante

    restaurante_id = restaurante_con_mesa["restaurante"].id
    db = SessionLocal()
    otro = Restaurante(nombre="Otro restaurante (test categorias)")
    db.add(otro)
    db.commit()
    otro_id = otro.id
    db.close()

    try:
        cat_ajena = client.post(
            f"/restaurantes/{otro_id}/categorias",
            json={"nombre": "Ajena"},
            headers=admin_autenticado["headers"],
        ).json()

        r = client.post(
            f"/restaurantes/{restaurante_id}/menu",
            json={"nombre": "Plato", "precio": "1000", "categoria_ids": [cat_ajena["id"]]},
            headers=admin_autenticado["headers"],
        )
        assert r.status_code == 422
    finally:
        db = SessionLocal()
        db.query(CategoriaMenu).filter(CategoriaMenu.restaurante_id == otro_id).delete()
        db.query(Restaurante).filter(Restaurante.id == otro_id).delete()
        db.commit()
        db.close()


def test_editar_item_reemplaza_categorias_y_lista_vacia_las_saca(
    client, restaurante_con_mesa, admin_autenticado
):
    restaurante_id = restaurante_con_mesa["restaurante"].id
    item_id = restaurante_con_mesa["menu_item"].id
    cat = client.post(
        f"/restaurantes/{restaurante_id}/categorias",
        json={"nombre": "Principales"},
        headers=admin_autenticado["headers"],
    ).json()

    r1 = client.put(
        f"/restaurantes/{restaurante_id}/menu/{item_id}",
        json={"categoria_ids": [cat["id"]]},
        headers=admin_autenticado["headers"],
    )
    assert [c["id"] for c in r1.json()["categorias"]] == [cat["id"]]

    # no mandar categoria_ids no las toca.
    r2 = client.put(
        f"/restaurantes/{restaurante_id}/menu/{item_id}",
        json={"precio": "9999"},
        headers=admin_autenticado["headers"],
    )
    assert [c["id"] for c in r2.json()["categorias"]] == [cat["id"]]

    # mandar lista vacía sí las saca.
    r3 = client.put(
        f"/restaurantes/{restaurante_id}/menu/{item_id}",
        json={"categoria_ids": []},
        headers=admin_autenticado["headers"],
    )
    assert r3.json()["categorias"] == []


def test_borrar_categoria_no_borra_los_platos(client, restaurante_con_mesa, admin_autenticado):
    restaurante_id = restaurante_con_mesa["restaurante"].id
    item_id = restaurante_con_mesa["menu_item"].id
    cat = client.post(
        f"/restaurantes/{restaurante_id}/categorias",
        json={"nombre": "Temporal"},
        headers=admin_autenticado["headers"],
    ).json()
    client.put(
        f"/restaurantes/{restaurante_id}/menu/{item_id}",
        json={"categoria_ids": [cat["id"]]},
        headers=admin_autenticado["headers"],
    )

    r = client.delete(
        f"/restaurantes/{restaurante_id}/categorias/{cat['id']}",
        headers=admin_autenticado["headers"],
    )
    assert r.status_code == 204

    detalle = client.get(f"/restaurantes/{restaurante_id}").json()
    plato = next(m for m in detalle["menu"] if m["id"] == item_id)
    assert plato["categorias"] == []
    assert detalle["categorias_menu"] == []


def test_admin_restaurante_no_gestiona_categorias_de_otro(client, restaurante_con_mesa):
    from app.core.database import SessionLocal
    from app.core.security import hash_password
    from app.models import Restaurante, Rol, Usuario

    restaurante_id = restaurante_con_mesa["restaurante"].id
    db = SessionLocal()
    db.add(
        Usuario(
            nombre="Admin local",
            email="admin-categorias@sacame-tests.dev",
            password_hash=hash_password("clave12345"),
            rol=Rol.ADMIN_RESTAURANTE,
            restaurante_id=restaurante_id,
        )
    )
    otro = Restaurante(nombre="Otro restaurante (test categorias 2)")
    db.add(otro)
    db.commit()
    otro_id = otro.id
    db.close()
    login = client.post(
        "/auth/login",
        data={"username": "admin-categorias@sacame-tests.dev", "password": "clave12345"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    try:
        # gestiona el suyo sin problema.
        r_propio = client.post(
            f"/restaurantes/{restaurante_id}/categorias",
            json={"nombre": "Entradas"},
            headers=headers,
        )
        assert r_propio.status_code == 201

        # pero no el de otro restaurante.
        r_ajeno = client.post(
            f"/restaurantes/{otro_id}/categorias", json={"nombre": "Entradas"}, headers=headers
        )
        assert r_ajeno.status_code == 403
    finally:
        db = SessionLocal()
        db.query(Restaurante).filter(Restaurante.id == otro_id).delete()
        db.commit()
        db.close()
