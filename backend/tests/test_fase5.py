from decimal import Decimal

from app.core.database import SessionLocal
from app.models import EstadoPedido, Pedido


def _crear_y_confirmar_pedido(client, restaurante_con_mesa, cliente_autenticado, mesero_autenticado, cantidad=1):
    r = client.post(
        "/pedidos",
        json={
            "mesa_id": restaurante_con_mesa["mesa"].id,
            "items": [
                {"menu_item_id": restaurante_con_mesa["menu_item"].id, "cantidad": cantidad}
            ],
        },
        headers=cliente_autenticado["headers"],
    )
    pedido_id = r.json()["id"]
    client.post(f"/pedidos/{pedido_id}/confirmar", headers=mesero_autenticado["headers"])
    # Solo se factura lo entregado (ver Brain.md) — acá se prueba
    # facturación, no el recorrido completo por cocina, así que se salta
    # directo a "entregado" en la base.
    db = SessionLocal()
    pedido = db.get(Pedido, pedido_id)
    pedido.estado = EstadoPedido.ENTREGADO
    db.commit()
    db.close()
    return pedido_id


def test_generar_factura_sin_propina(
    client, restaurante_con_mesa, cliente_autenticado, mesero_autenticado
):
    _crear_y_confirmar_pedido(client, restaurante_con_mesa, cliente_autenticado, mesero_autenticado)
    mesa_id = restaurante_con_mesa["mesa"].id

    r = client.post(
        f"/mesas/{mesa_id}/factura",
        json={"incluye_propina": False},
        headers=mesero_autenticado["headers"],
    )
    assert r.status_code == 201
    data = r.json()
    assert Decimal(data["subtotal"]) == Decimal("10000.00")
    assert Decimal(data["propina"]) == Decimal("0")
    assert Decimal(data["total"]) == Decimal("10000.00")
    assert len(data["items"]) == 1


def test_generar_factura_con_propina(
    client, restaurante_con_mesa, cliente_autenticado, mesero_autenticado
):
    _crear_y_confirmar_pedido(
        client, restaurante_con_mesa, cliente_autenticado, mesero_autenticado, cantidad=2
    )
    mesa_id = restaurante_con_mesa["mesa"].id

    r = client.post(
        f"/mesas/{mesa_id}/factura",
        json={"incluye_propina": True, "porcentaje_propina": "0.10"},
        headers=mesero_autenticado["headers"],
    )
    assert r.status_code == 201
    data = r.json()
    assert Decimal(data["subtotal"]) == Decimal("20000.00")
    assert Decimal(data["propina"]) == Decimal("2000.00")
    assert Decimal(data["total"]) == Decimal("22000.00")


def test_pedido_facturado_no_se_puede_facturar_dos_veces(
    client, restaurante_con_mesa, cliente_autenticado, mesero_autenticado
):
    _crear_y_confirmar_pedido(client, restaurante_con_mesa, cliente_autenticado, mesero_autenticado)
    mesa_id = restaurante_con_mesa["mesa"].id

    client.post(
        f"/mesas/{mesa_id}/factura",
        json={"incluye_propina": False},
        headers=mesero_autenticado["headers"],
    )
    r2 = client.post(
        f"/mesas/{mesa_id}/factura",
        json={"incluye_propina": False},
        headers=mesero_autenticado["headers"],
    )
    assert r2.status_code == 422


def test_no_se_puede_facturar_mesa_sin_pedidos_confirmados(
    client, restaurante_con_mesa, mesero_autenticado
):
    mesa_id = restaurante_con_mesa["mesa"].id
    r = client.post(
        f"/mesas/{mesa_id}/factura",
        json={"incluye_propina": False},
        headers=mesero_autenticado["headers"],
    )
    assert r.status_code == 422


def test_obtener_factura(
    client, restaurante_con_mesa, cliente_autenticado, mesero_autenticado
):
    _crear_y_confirmar_pedido(client, restaurante_con_mesa, cliente_autenticado, mesero_autenticado)
    mesa_id = restaurante_con_mesa["mesa"].id

    creada = client.post(
        f"/mesas/{mesa_id}/factura",
        json={"incluye_propina": False},
        headers=mesero_autenticado["headers"],
    ).json()

    r = client.get(f"/facturas/{creada['id']}", headers=mesero_autenticado["headers"])
    assert r.status_code == 200
    assert r.json()["id"] == creada["id"]


def test_cliente_no_puede_generar_factura(
    client, restaurante_con_mesa, cliente_autenticado
):
    mesa_id = restaurante_con_mesa["mesa"].id
    r = client.post(
        f"/mesas/{mesa_id}/factura",
        json={"incluye_propina": False},
        headers=cliente_autenticado["headers"],
    )
    assert r.status_code == 403
