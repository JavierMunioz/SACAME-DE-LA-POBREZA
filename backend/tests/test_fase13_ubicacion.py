from app.core.database import SessionLocal
from app.models import Restaurante

# Bogotá, Plaza de Bolívar — coordenadas de referencia para los tests.
LAT_RESTAURANTE = 4.598056
LNG_RESTAURANTE = -74.075833

# A ~50m de distancia (dentro del radio de tolerancia).
LAT_CERCA = 4.598500
LNG_CERCA = -74.075833

# A varios km de distancia (claramente "en otra parte").
LAT_LEJOS = 4.650000
LNG_LEJOS = -74.100000


def _setear_ubicacion(restaurante_id: int, lat: float | None, lng: float | None) -> None:
    db = SessionLocal()
    r = db.get(Restaurante, restaurante_id)
    r.latitud = lat
    r.longitud = lng
    db.commit()
    db.close()


def test_sin_ubicacion_configurada_no_exige_geolocalizacion(client, restaurante_con_mesa):
    mesa = restaurante_con_mesa["mesa"]
    qr = client.get(f"/mesas/qr/{mesa.qr_token}").json()
    assert qr["requiere_ubicacion"] is False

    r = client.post(
        f"/mesas/{mesa.id}/ocupar",
        json={"qr_token": mesa.qr_token, "nombre_invitado": "Ana"},
    )
    assert r.status_code == 201


def test_con_ubicacion_configurada_exige_geolocalizacion(client, restaurante_con_mesa):
    mesa = restaurante_con_mesa["mesa"]
    _setear_ubicacion(restaurante_con_mesa["restaurante"].id, LAT_RESTAURANTE, LNG_RESTAURANTE)

    qr = client.get(f"/mesas/qr/{mesa.qr_token}").json()
    assert qr["requiere_ubicacion"] is True

    # Sin lat/lng en el body: rechazado.
    r = client.post(
        f"/mesas/{mesa.id}/ocupar",
        json={"qr_token": mesa.qr_token, "nombre_invitado": "Ana"},
    )
    assert r.status_code == 422


def test_ocupar_lejos_del_restaurante_se_rechaza(client, restaurante_con_mesa):
    mesa = restaurante_con_mesa["mesa"]
    _setear_ubicacion(restaurante_con_mesa["restaurante"].id, LAT_RESTAURANTE, LNG_RESTAURANTE)

    r = client.post(
        f"/mesas/{mesa.id}/ocupar",
        json={
            "qr_token": mesa.qr_token,
            "nombre_invitado": "Ana",
            "lat": LAT_LEJOS,
            "lng": LNG_LEJOS,
        },
    )
    assert r.status_code == 403


def test_ocupar_cerca_del_restaurante_se_acepta(client, restaurante_con_mesa):
    mesa = restaurante_con_mesa["mesa"]
    _setear_ubicacion(restaurante_con_mesa["restaurante"].id, LAT_RESTAURANTE, LNG_RESTAURANTE)

    r = client.post(
        f"/mesas/{mesa.id}/ocupar",
        json={
            "qr_token": mesa.qr_token,
            "nombre_invitado": "Ana",
            "lat": LAT_CERCA,
            "lng": LNG_CERCA,
        },
    )
    assert r.status_code == 201


def test_admin_restaurante_puede_editar_su_ubicacion(client, restaurante_con_mesa):
    from app.core.security import hash_password
    from app.models import Rol, Usuario

    restaurante_id = restaurante_con_mesa["restaurante"].id
    db = SessionLocal()
    db.add(
        Usuario(
            nombre="Admin local",
            email="admin-ubicacion@sacame-tests.dev",
            password_hash=hash_password("clave12345"),
            rol=Rol.ADMIN_RESTAURANTE,
            restaurante_id=restaurante_id,
        )
    )
    db.commit()
    db.close()
    login = client.post(
        "/auth/login",
        data={"username": "admin-ubicacion@sacame-tests.dev", "password": "clave12345"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    r = client.put(
        f"/restaurantes/{restaurante_id}",
        json={"latitud": LAT_RESTAURANTE, "longitud": LNG_RESTAURANTE},
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["latitud"] == LAT_RESTAURANTE
    assert r.json()["longitud"] == LNG_RESTAURANTE
    # el nombre no se tocó (update parcial).
    assert r.json()["nombre"] == restaurante_con_mesa["restaurante"].nombre
