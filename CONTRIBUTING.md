# CONTRIBUTING.md — Cómo trabajar sobre este repo

## Antes de tocar código

1. Lee `Brain.md` — ahí está el estado real del proyecto y las reglas de cada área (frontend/backend).
2. Revisa `Plan.md` para saber en qué fase del MVP estamos.

## Ramas

- `main` — siempre desplegable. **Nadie hace push directo aquí.**
- `feature/nombre-corto` — nueva funcionalidad (ej. `feature/reserva-mesa`)
- `fix/nombre-corto` — corrección de bug (ej. `fix/qr-no-valida-reserva`)
- `chore/nombre-corto` — tareas de mantenimiento, dependencias, configuración

## Commits

Se usa el formato de **Conventional Commits**:

```
feat: agregar validación de QR contra reserva activa
fix: corregir orden de la comanda de cocina
docs: actualizar Brain.md con decisión de base de datos
refactor: separar lógica de mesas del servicio de reservas
chore: actualizar dependencias de FastAPI
```

Reglas:
- Un commit = un cambio lógico. No mezclar un fix con una feature en el mismo commit.
- Mensaje en modo imperativo, en minúsculas, sin punto final.

## Pull Requests

1. Crear la rama desde `main` actualizado.
2. Antes de abrir el PR: correr tests locales y verificar que el linter pase.
3. El PR debe describir:
   - Qué problema resuelve o qué agrega.
   - Cómo probarlo manualmente.
4. **Ningún PR se mergea sin al menos una revisión aprobada.**
5. Al mergear, actualizar la sección de Bitácora en `Brain.md` con lo que se hizo.

## Buenas prácticas generales

- No subir archivos `.env` ni credenciales — usar `.env.example` como referencia.
- Migraciones de base de datos siempre versionadas (Alembic), nunca cambios manuales directos en producción.
- Todo endpoint nuevo del backend debe quedar documentado automáticamente vía OpenAPI (FastAPI lo genera solo si el código está bien tipado).
- Todo componente nuevo del frontend sigue las decisiones de diseño de la **taste skill** — no se improvisa estilo a mano.

## Entorno local

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

(Ajustar cuando se defina la estructura final de carpetas.)
