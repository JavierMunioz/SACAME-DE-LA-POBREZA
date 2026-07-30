import secrets

import pytest
from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.main import app
from app.models import (
    Factura,
    ItemPedido,
    MenuItem,
    Mesa,
    Pedido,
    Reserva,
    Restaurante,
    Rol,
    SesionMesa,
    Usuario,
)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def cleanup_usuarios_de_test():
    yield
    # Defensa contra tests que fallan a mitad de camino y dejan reservas/pedidos
    # sin borrar: si no se limpian primero, el DELETE de usuarios truena por FK
    # y esa basura bloquea el cleanup de TODAS las corridas siguientes.
    db = SessionLocal()
    ids = [
        u.id
        for u in db.query(Usuario).filter(Usuario.email.like("%@sacame-tests.dev")).all()
    ]
    if ids:
        pedido_ids = [p.id for p in db.query(Pedido).filter(Pedido.cliente_id.in_(ids)).all()]
        db.query(ItemPedido).filter(ItemPedido.pedido_id.in_(pedido_ids)).delete(
            synchronize_session=False
        )
        db.query(Pedido).filter(Pedido.id.in_(pedido_ids)).delete(synchronize_session=False)
        db.query(SesionMesa).filter(SesionMesa.cliente_id.in_(ids)).delete(
            synchronize_session=False
        )
        db.query(Reserva).filter(Reserva.cliente_id.in_(ids)).delete(synchronize_session=False)
        db.query(Usuario).filter(Usuario.id.in_(ids)).delete(synchronize_session=False)
        db.commit()
    db.close()


@pytest.fixture
def restaurante_con_mesa():
    """Restaurante + mesa + item de menú para tests que necesitan datos base."""
    db = SessionLocal()
    restaurante = Restaurante(nombre="Restaurante de test")
    db.add(restaurante)
    db.flush()
    mesa = Mesa(
        restaurante_id=restaurante.id,
        numero=1,
        capacidad=4,
        qr_token=f"test-{secrets.token_hex(8)}",
    )
    item = MenuItem(restaurante_id=restaurante.id, nombre="Plato de test", precio=10000)
    db.add_all([mesa, item])
    db.commit()
    db.refresh(restaurante)
    db.refresh(mesa)
    db.refresh(item)
    yield {"restaurante": restaurante, "mesa": mesa, "menu_item": item}
    # Borrar primero lo que depende de la mesa (reservas, sesiones,
    # pedidos/items), si no la FK bloquea el delete de mesa y, más tarde,
    # el de usuarios.
    pedido_ids = [p.id for p in db.query(Pedido).filter(Pedido.mesa_id == mesa.id).all()]
    if pedido_ids:
        db.query(ItemPedido).filter(ItemPedido.pedido_id.in_(pedido_ids)).delete(
            synchronize_session=False
        )
        db.query(Pedido).filter(Pedido.id.in_(pedido_ids)).delete(synchronize_session=False)
    db.query(SesionMesa).filter(SesionMesa.mesa_id == mesa.id).delete()
    db.query(Factura).filter(Factura.mesa_id == mesa.id).delete()
    db.query(Reserva).filter(Reserva.mesa_id == mesa.id).delete()
    db.query(MenuItem).filter(MenuItem.restaurante_id == restaurante.id).delete()
    db.query(Mesa).filter(Mesa.restaurante_id == restaurante.id).delete()
    # Personal (mesero/cocina/admin_restaurante) creado para este restaurante
    # de test, ej. por el fixture mesero_autenticado.
    db.query(Usuario).filter(Usuario.restaurante_id == restaurante.id).delete()
    db.query(Restaurante).filter(Restaurante.id == restaurante.id).delete()
    db.commit()
    db.close()


@pytest.fixture
def cliente_autenticado(client):
    email = "cliente-fixture@sacame-tests.dev"
    client.post(
        "/auth/registro",
        json={"nombre": "Cliente fixture", "email": email, "password": "clave12345"},
    )
    login = client.post("/auth/login", data={"username": email, "password": "clave12345"})
    token = login.json()["access_token"]

    db = SessionLocal()
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    usuario_id = usuario.id
    db.close()

    return {"token": token, "usuario_id": usuario_id, "headers": {"Authorization": f"Bearer {token}"}}


@pytest.fixture
def mesero_autenticado(client, restaurante_con_mesa):
    email = "mesero-fixture@sacame-tests.dev"
    db = SessionLocal()
    db.add(
        Usuario(
            nombre="Mesero fixture",
            email=email,
            password_hash=hash_password("clave12345"),
            rol=Rol.MESERO,
            restaurante_id=restaurante_con_mesa["restaurante"].id,
        )
    )
    db.commit()
    db.close()

    login = client.post("/auth/login", data={"username": email, "password": "clave12345"})
    token = login.json()["access_token"]
    return {"token": token, "headers": {"Authorization": f"Bearer {token}"}}


@pytest.fixture
def cocina_autenticado(client, restaurante_con_mesa):
    email = "cocina-fixture@sacame-tests.dev"
    db = SessionLocal()
    db.add(
        Usuario(
            nombre="Cocina fixture",
            email=email,
            password_hash=hash_password("clave12345"),
            rol=Rol.COCINA,
            restaurante_id=restaurante_con_mesa["restaurante"].id,
        )
    )
    db.commit()
    db.close()

    login = client.post("/auth/login", data={"username": email, "password": "clave12345"})
    token = login.json()["access_token"]
    return {"token": token, "headers": {"Authorization": f"Bearer {token}"}}


@pytest.fixture
def admin_autenticado(client):
    email = "admin-fixture@sacame-tests.dev"
    db = SessionLocal()
    if not db.query(Usuario).filter(Usuario.email == email).first():
        db.add(
            Usuario(
                nombre="Admin fixture",
                email=email,
                password_hash=hash_password("clave12345"),
                rol=Rol.ADMIN_GENERAL,
            )
        )
        db.commit()
    db.close()

    login = client.post("/auth/login", data={"username": email, "password": "clave12345"})
    token = login.json()["access_token"]
    return {"token": token, "headers": {"Authorization": f"Bearer {token}"}}
