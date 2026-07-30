"""Crea el primer usuario admin_general. Uso:

    python scripts/crear_admin_general.py nombre@correo.com "Nombre Apellido"

Pide la contraseña por input oculto. No hay endpoint HTTP para esto a
propósito: dar de alta un admin_general es un acto de confianza fuera de
banda, no una acción de la app.
"""

import getpass
import sys

sys.path.insert(0, ".")

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import Rol, Usuario


def main():
    if len(sys.argv) != 3:
        print('Uso: python scripts/crear_admin_general.py email "Nombre Apellido"')
        sys.exit(1)

    email, nombre = sys.argv[1], sys.argv[2]
    password = getpass.getpass("Contraseña: ")
    password2 = getpass.getpass("Repetir contraseña: ")
    if password != password2:
        print("Las contraseñas no coinciden")
        sys.exit(1)

    db = SessionLocal()
    try:
        if db.query(Usuario).filter(Usuario.email == email).first():
            print(f"Ya existe un usuario con email {email}")
            sys.exit(1)

        usuario = Usuario(
            nombre=nombre,
            email=email,
            password_hash=hash_password(password),
            rol=Rol.ADMIN_GENERAL,
        )
        db.add(usuario)
        db.commit()
        print(f"admin_general creado: {email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
