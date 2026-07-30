from app.core.database import SessionLocal
from app.models import Restaurante, Usuario


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


def test_admin_crea_personal(client, restaurante_con_mesa, admin_autenticado):
    restaurante_id = restaurante_con_mesa["restaurante"].id
    r = client.post(
        f"/restaurantes/{restaurante_id}/personal",
        json={
            "nombre": "Mesero nuevo",
            "email": "mesero-nuevo@sacame-tests.dev",
            "password": "clave12345",
            "rol": "mesero",
        },
        headers=admin_autenticado["headers"],
    )
    assert r.status_code == 201
    assert r.json()["rol"] == "mesero"


def test_crear_personal_requiere_admin_general(client, restaurante_con_mesa, cliente_autenticado):
    restaurante_id = restaurante_con_mesa["restaurante"].id
    r = client.post(
        f"/restaurantes/{restaurante_id}/personal",
        json={
            "nombre": "Intento",
            "email": "intento@sacame-tests.dev",
            "password": "clave12345",
            "rol": "mesero",
        },
        headers=cliente_autenticado["headers"],
    )
    assert r.status_code == 403


def test_mesero_ve_pedidos_de_su_restaurante(
    client, restaurante_con_mesa, cliente_autenticado, mesero_autenticado
):
    _crear_pedido(client, restaurante_con_mesa, cliente_autenticado)

    r = client.get("/pedidos", headers=mesero_autenticado["headers"])
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["estado"] == "pendiente"
    assert data[0]["mesa_numero"] == restaurante_con_mesa["mesa"].numero
    assert data[0]["items"][0]["menu_item_nombre"] == restaurante_con_mesa["menu_item"].nombre


def test_mesero_confirma_pedido(
    client, restaurante_con_mesa, cliente_autenticado, mesero_autenticado
):
    pedido_id = _crear_pedido(client, restaurante_con_mesa, cliente_autenticado)

    r = client.post(f"/pedidos/{pedido_id}/confirmar", headers=mesero_autenticado["headers"])
    assert r.status_code == 200
    assert r.json()["estado"] == "confirmado"
    assert r.json()["confirmado_at"] is not None

    r2 = client.post(f"/pedidos/{pedido_id}/confirmar", headers=mesero_autenticado["headers"])
    assert r2.status_code == 409


def test_mesero_cancela_pedido(
    client, restaurante_con_mesa, cliente_autenticado, mesero_autenticado
):
    pedido_id = _crear_pedido(client, restaurante_con_mesa, cliente_autenticado)

    r = client.post(f"/pedidos/{pedido_id}/cancelar", headers=mesero_autenticado["headers"])
    assert r.status_code == 200
    assert r.json()["estado"] == "cancelado"


def test_mesero_no_ve_pedidos_de_otro_restaurante(
    client, restaurante_con_mesa, cliente_autenticado, admin_autenticado
):
    pedido_id = _crear_pedido(client, restaurante_con_mesa, cliente_autenticado)

    otro_restaurante = client.post(
        "/restaurantes",
        json={"nombre": "Otro restaurante de test", "menu_inicial": []},
        headers=admin_autenticado["headers"],
    ).json()
    try:
        mesero_otro = client.post(
            f"/restaurantes/{otro_restaurante['id']}/personal",
            json={
                "nombre": "Mesero de otro lado",
                "email": "mesero-otro@sacame-tests.dev",
                "password": "clave12345",
                "rol": "mesero",
            },
            headers=admin_autenticado["headers"],
        )
        login = client.post(
            "/auth/login",
            data={"username": "mesero-otro@sacame-tests.dev", "password": "clave12345"},
        )
        headers_otro = {"Authorization": f"Bearer {login.json()['access_token']}"}

        r = client.get("/pedidos", headers=headers_otro)
        assert r.json() == []

        r2 = client.post(f"/pedidos/{pedido_id}/confirmar", headers=headers_otro)
        assert r2.status_code == 404

        assert mesero_otro.status_code == 201
    finally:
        db = SessionLocal()
        db.query(Usuario).filter(Usuario.email == "mesero-otro@sacame-tests.dev").delete()
        db.query(Restaurante).filter(Restaurante.id == otro_restaurante["id"]).delete()
        db.commit()
        db.close()
