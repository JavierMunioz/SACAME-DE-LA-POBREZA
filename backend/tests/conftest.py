import pytest
from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.main import app
from app.models import Usuario


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def cleanup_usuarios_de_test():
    yield
    db = SessionLocal()
    db.query(Usuario).filter(Usuario.email.like("%@sacame-tests.dev")).delete()
    db.commit()
    db.close()
