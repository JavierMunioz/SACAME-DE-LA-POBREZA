from datetime import datetime, timedelta, timezone


def test_ocupar_mesa_la_bloquea_para_otro_invitado(client, restaurante_con_mesa):
    mesa = restaurante_con_mesa["mesa"]

    r1 = client.post(
        f"/mesas/{mesa.id}/ocupar",
        json={"qr_token": mesa.qr_token, "nombre_invitado": "Ana"},
    )
    assert r1.status_code == 201

    r2 = client.post(
        f"/mesas/{mesa.id}/ocupar",
        json={"qr_token": mesa.qr_token, "nombre_invitado": "Beto"},
    )
    assert r2.status_code == 409

    qr = client.get(f"/mesas/qr/{mesa.qr_token}").json()
    assert qr["estado"] == "ocupada"
    assert qr["requiere_codigo"] is True


def test_unirse_con_codigo_correcto_devuelve_misma_sesion(client, restaurante_con_mesa):
    mesa = restaurante_con_mesa["mesa"]
    r1 = client.post(
        f"/mesas/{mesa.id}/ocupar",
        json={"qr_token": mesa.qr_token, "nombre_invitado": "Ana"},
    )
    codigo = r1.json()["codigo_acceso"]

    r2 = client.post(
        f"/mesas/{mesa.id}/unirse",
        json={"qr_token": mesa.qr_token, "codigo_acceso": codigo},
    )
    assert r2.status_code == 200
    assert r2.json()["token"] == r1.json()["token"]


def test_unirse_con_codigo_incorrecto_falla(client, restaurante_con_mesa):
    mesa = restaurante_con_mesa["mesa"]
    client.post(
        f"/mesas/{mesa.id}/ocupar",
        json={"qr_token": mesa.qr_token, "nombre_invitado": "Ana"},
    )
    r = client.post(
        f"/mesas/{mesa.id}/unirse",
        json={"qr_token": mesa.qr_token, "codigo_acceso": "0000"},
    )
    assert r.status_code == 401


def test_sesion_compartida_ve_mismo_token_pero_solo_dueno_tiene_token_dueno(
    client, restaurante_con_mesa
):
    mesa = restaurante_con_mesa["mesa"]

    r1 = client.post(
        f"/mesas/{mesa.id}/ocupar",
        json={"qr_token": mesa.qr_token, "nombre_invitado": "Ana"},
    )
    assert r1.json()["token_dueno"] is not None
    token = r1.json()["token"]
    codigo = r1.json()["codigo_acceso"]

    r2 = client.post(
        f"/mesas/{mesa.id}/unirse",
        json={"qr_token": mesa.qr_token, "codigo_acceso": codigo},
    )
    assert r2.json()["token"] == token
    assert r2.json()["token_dueno"] is None


def test_solo_el_dueno_puede_enviar_el_pedido(client, restaurante_con_mesa):
    mesa = restaurante_con_mesa["mesa"]
    item_id = restaurante_con_mesa["menu_item"].id

    r1 = client.post(
        f"/mesas/{mesa.id}/ocupar",
        json={"qr_token": mesa.qr_token, "nombre_invitado": "Ana"},
    )
    token_compartido = r1.json()["token"]
    token_dueno = r1.json()["token_dueno"]

    # Un dispositivo que solo tiene el token compartido (ej. se unió con
    # el código) no puede enviar el pedido.
    rechazado = client.post(
        "/pedidos",
        json={
            "mesa_id": mesa.id,
            "sesion_token": token_compartido,
            "items": [{"menu_item_id": item_id, "cantidad": 1}],
        },
    )
    assert rechazado.status_code == 401

    # El dueño, con su token_dueno, sí puede.
    aceptado = client.post(
        "/pedidos",
        json={
            "mesa_id": mesa.id,
            "sesion_token": token_dueno,
            "items": [{"menu_item_id": item_id, "cantidad": 1}],
        },
    )
    assert aceptado.status_code == 201
    assert aceptado.json()["nombre_invitado"] == "Ana"


def test_reserva_con_check_in_ocupa_la_mesa(client, restaurante_con_mesa, cliente_autenticado):
    mesa = restaurante_con_mesa["mesa"]
    ahora = datetime.now(timezone.utc)

    reserva = client.post(
        "/reservas",
        json={"mesa_id": mesa.id, "inicio": ahora.isoformat(), "duracion_minutos": 90},
        headers=cliente_autenticado["headers"],
    ).json()

    r = client.post(
        f"/mesas/{mesa.id}/ocupar",
        json={"qr_token": mesa.qr_token, "reserva_id": reserva["id"]},
        headers=cliente_autenticado["headers"],
    )
    assert r.status_code == 201

    qr = client.get(f"/mesas/qr/{mesa.qr_token}").json()
    assert qr["estado"] == "ocupada"


def test_reserva_vencida_sin_checkin_se_libera(client, restaurante_con_mesa, cliente_autenticado):
    mesa = restaurante_con_mesa["mesa"]
    # Reserva creada "en el pasado" respecto a su propio horario, para que
    # el plazo de check-in (inicio - 15 min) ya haya pasado al consultar.
    inicio = datetime.now(timezone.utc) + timedelta(days=1)
    client.post(
        "/reservas",
        json={"mesa_id": mesa.id, "inicio": inicio.isoformat(), "duracion_minutos": 90},
        headers=cliente_autenticado["headers"],
    )

    _forzar_reserva_vieja(mesa.id, inicio)

    qr = client.get(f"/mesas/qr/{mesa.qr_token}").json()
    assert qr["estado"] == "libre"
    assert qr["mesa_libre_ahora"] is True


def _forzar_reserva_vieja(mesa_id: int, inicio):
    """Reescribe created_at de la reserva a mucho antes de su propio plazo
    de check-in, simulando que fue hecha con anticipación real (si no, la
    excepción de 'reserva de último momento' la protege de expirar)."""
    from datetime import timedelta

    from app.core.database import SessionLocal
    from app.models import EstadoReserva, Reserva

    db = SessionLocal()
    reserva = (
        db.query(Reserva)
        .filter(Reserva.mesa_id == mesa_id, Reserva.estado == EstadoReserva.ACTIVA)
        .order_by(Reserva.id.desc())
        .first()
    )
    reserva.created_at = inicio - timedelta(days=1)
    db.commit()
    db.close()


def test_factura_libera_la_mesa_y_cierra_la_sesion(
    client, restaurante_con_mesa, mesero_autenticado
):
    mesa = restaurante_con_mesa["mesa"]
    item_id = restaurante_con_mesa["menu_item"].id

    ocupar = client.post(
        f"/mesas/{mesa.id}/ocupar",
        json={"qr_token": mesa.qr_token, "nombre_invitado": "Ana"},
    )
    sesion_token = ocupar.json()["token_dueno"]

    pedido = client.post(
        "/pedidos",
        json={
            "mesa_id": mesa.id,
            "sesion_token": sesion_token,
            "items": [{"menu_item_id": item_id, "cantidad": 1}],
        },
    ).json()
    client.post(f"/pedidos/{pedido['id']}/confirmar", headers=mesero_autenticado["headers"])

    factura = client.post(
        f"/mesas/{mesa.id}/factura",
        json={"incluye_propina": False, "porcentaje_propina": 0},
        headers=mesero_autenticado["headers"],
    )
    assert factura.status_code == 201

    qr = client.get(f"/mesas/qr/{mesa.qr_token}").json()
    assert qr["estado"] == "libre"
    assert qr["requiere_codigo"] is False

    # La mesa está libre de nuevo: se puede ocupar sin código.
    r = client.post(
        f"/mesas/{mesa.id}/ocupar",
        json={"qr_token": mesa.qr_token, "nombre_invitado": "Otro comensal"},
    )
    assert r.status_code == 201
