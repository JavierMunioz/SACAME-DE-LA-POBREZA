from datetime import datetime, timedelta, timezone

from app.core.database import SessionLocal
from app.models import EstadoPedido, Pedido, Reserva


def _crear_confirmar_y_facturar(client, restaurante_con_mesa, cliente_autenticado, mesero_autenticado, cantidad=1):
    mesa_id = restaurante_con_mesa["mesa"].id
    r = client.post(
        "/pedidos",
        json={
            "mesa_id": mesa_id,
            "items": [
                {"menu_item_id": restaurante_con_mesa["menu_item"].id, "cantidad": cantidad}
            ],
        },
        headers=cliente_autenticado["headers"],
    )
    pedido_id = r.json()["id"]
    client.post(f"/pedidos/{pedido_id}/confirmar", headers=mesero_autenticado["headers"])
    # Solo se factura lo entregado (ver Brain.md).
    db = SessionLocal()
    db_pedido = db.get(Pedido, pedido_id)
    db_pedido.estado = EstadoPedido.ENTREGADO
    db.commit()
    db.close()
    factura = client.post(
        f"/mesas/{mesa_id}/factura",
        json={"incluye_propina": False},
        headers=mesero_autenticado["headers"],
    )
    return factura.json()


def test_estadisticas_sin_facturas_da_ceros(client, restaurante_con_mesa, admin_autenticado):
    restaurante_id = restaurante_con_mesa["restaurante"].id
    r = client.get(
        f"/restaurantes/{restaurante_id}/estadisticas", headers=admin_autenticado["headers"]
    )
    assert r.status_code == 200
    data = r.json()
    assert data["revenue_hoy"] == "0"
    assert data["revenue_ayer"] == "0"
    assert data["variacion_pct"] is None
    assert data["mesas_total"] == 1
    assert data["mesas_ocupadas"] == 0
    assert data["platos_mas_vendidos_hoy"] == []


def test_estadisticas_revenue_y_top_platos_reflejan_factura_real(
    client, restaurante_con_mesa, cliente_autenticado, mesero_autenticado, admin_autenticado
):
    restaurante_id = restaurante_con_mesa["restaurante"].id
    factura = _crear_confirmar_y_facturar(
        client, restaurante_con_mesa, cliente_autenticado, mesero_autenticado, cantidad=3
    )

    r = client.get(
        f"/restaurantes/{restaurante_id}/estadisticas", headers=admin_autenticado["headers"]
    )
    data = r.json()
    assert data["revenue_hoy"] == factura["total"]
    assert len(data["platos_mas_vendidos_hoy"]) == 1
    assert data["platos_mas_vendidos_hoy"][0]["cantidad_vendida"] == 3
    assert data["platos_mas_vendidos_hoy"][0]["nombre"] == "Plato de test"


def test_estadisticas_mesas_ocupadas_refleja_sesion_activa(
    client, restaurante_con_mesa, admin_autenticado
):
    mesa = restaurante_con_mesa["mesa"]
    restaurante_id = restaurante_con_mesa["restaurante"].id
    client.post(
        f"/mesas/{mesa.id}/ocupar",
        json={"qr_token": mesa.qr_token, "nombre_invitado": "Ana"},
    )

    r = client.get(
        f"/restaurantes/{restaurante_id}/estadisticas", headers=admin_autenticado["headers"]
    )
    data = r.json()
    assert data["mesas_ocupadas"] == 1


def test_listar_mesas_admin_muestra_reservada(
    client, restaurante_con_mesa, cliente_autenticado, admin_autenticado
):
    mesa = restaurante_con_mesa["mesa"]
    restaurante_id = restaurante_con_mesa["restaurante"].id
    ahora = datetime.now(timezone.utc)

    # Directo en la base: la regla de 2h de anticipación impediría
    # reservar "para ahora" desde la API, pero acá se prueba el estado
    # tri-estado del listado de mesas, no esa regla.
    db = SessionLocal()
    db.add(
        Reserva(
            mesa_id=mesa.id,
            cliente_id=cliente_autenticado["usuario_id"],
            inicio=ahora,
            duracion_minutos=90,
        )
    )
    db.commit()
    db.close()

    r = client.get(
        f"/restaurantes/{restaurante_id}/mesas", headers=admin_autenticado["headers"]
    )
    mesas = r.json()
    assert next(m for m in mesas if m["id"] == mesa.id)["estado"] == "reservada"
