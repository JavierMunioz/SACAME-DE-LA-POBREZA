# Brain.md — Bitácora y metodología del proyecto

Este archivo se lee **antes de tocar cualquier cosa** del proyecto. Aquí vive el estado real: qué se ha hecho, qué falta, y las reglas fijas de cómo se trabaja. Si algo en el código contradice este archivo, este archivo manda hasta que se actualice explícitamente.

---

## Stack tecnológico

- **Backend:** Python (FastAPI)
- **Base de datos:** PostgreSQL
- **Frontend:** Vue 3 (Composition API)
- **Roles del sistema:** cliente, mesero, cocina, admin de restaurante

---

## Decisión: PostgreSQL en vez de MongoDB

Se evaluó Mongo vs una base relacional. Se elige **PostgreSQL** por:

- Las reservas y mesas necesitan garantizar que **nunca dos personas reserven la misma mesa a la misma hora**. Eso es un problema de integridad transaccional (constraints, locks a nivel de fila) — terreno natural de una base relacional. En Mongo esa lógica habría que blindarla a mano en la aplicación, con más riesgo de condiciones de carrera.
- El dominio es inherentemente relacional: `restaurante → mesas → reservas → pedidos → items_pedido → facturas`. Hay JOINs naturales todo el tiempo (ej: "todos los pedidos pendientes de un restaurante con su mesa y su mesero asignado").
- La facturación necesita consistencia fuerte: no se puede perder ni duplicar un pedido o un cobro.
- El volumen de datos de este proyecto no necesita la escalabilidad horizontal de Mongo; Postgres no tiene ningún problema con esta carga.

Mongo tendría sentido si el modelo fuera muy variable o de documentos sueltos (logs, catálogos con esquema cambiante) — no es el caso aquí.

Si más adelante se necesita tiempo real (pedidos apareciendo al instante en mesero/cocina), se puede sumar **Redis** o **WebSockets nativos de FastAPI** como capa adicional — eso no reemplaza a Postgres, lo complementa.

---

## Reglas de trabajo por área

### Frontend (Vue 3)
- Toda tarea de frontend usa la skill **taste skill** instalada para las decisiones de diseño visual antes de escribir código.
- Componentización por rol: `cliente/`, `mesero/`, `cocina/`.
- Un solo router, guards de ruta por rol.

### Backend (Python)
- Toda tarea de backend usa la **skill de backend** instalada.
- Endpoints documentados automáticamente vía OpenAPI/Swagger de FastAPI.
- Migraciones de base de datos versionadas (Alembic).

### Documentación de avance
Cada vez que se hace algo (feature, fix, decisión de arquitectura), se agrega una entrada en la Bitácora de abajo, **más reciente arriba**. Formato:

```
### [YYYY-MM-DD] Título corto
- Qué se hizo
- Por qué
- Qué queda pendiente / próximos pasos
```

No se borran entradas viejas. Si algo queda obsoleto, se marca como `(obsoleto, ver entrada del DD/MM)`.

---

## Bitácora

### [2026-07-29] Fase 1.5 completa: panel de administrador general
- Backend: `app/routers/restaurantes.py` — crear restaurante (con menú inicial opcional), listar/obtener restaurante, agregar ítem de menú, crear mesa, listar mesas, regenerar QR, servir el QR como PNG real (librería `qrcode`). Todo protegido con `require_roles(Rol.ADMIN_GENERAL)` excepto el listado público de restaurantes (útil para Fase 2).
- `scripts/crear_admin_general.py`: no hay endpoint HTTP para crear el primer `admin_general` a propósito — es un bootstrap manual por CLI, no una acción de la app.
- Frontend: la taste skill (`design-taste-frontend`) señaló que un panel admin está **fuera de su alcance** (está pensada para landing pages, no dashboards) y recomienda un design system real. Se eligió **Element Plus** (Vue 3) en vez de Tailwind a mano. Se limpió el CSS boilerplate del scaffold de Vite (grid de 2 columnas centrado que rompía cualquier layout real) y se forzó tema claro (no se implementó dark mode para el panel, fuera de alcance para una herramienta interna).
- Login real: `stores/auth.ts` ahora maneja JWT de verdad (antes era un stub que solo guardaba el rol sin autenticar). Token en `localStorage`, interceptor de axios en `api/client.ts` lo inyecta en cada request. Guard del router (`router/index.ts`) exige token + rol correcto o redirige a `/login`.
- El PNG del QR (`GET /mesas/{id}/qr.png`) está protegido por rol admin, así que no puede cargarse con `<img src="...">` directo (el navegador no manda el header `Authorization`). Se resolvió trayéndolo como blob autenticado vía axios y usando `URL.createObjectURL`.
- **Gotcha de infraestructura (dos veces en la misma sesión):** puerto 8000 también estaba ocupado en esta máquina (contenedor Docker `waygo_api` de otro proyecto). Se fijó el backend de este proyecto en el puerto **8001** (`VITE_API_BASE_URL` default en el frontend, instrucciones en CONTRIBUTING.md). Sumado a Postgres en 5434, esta máquina tiene varios proyectos compitiendo por los puertos por defecto — repasar `docker ps` / `lsof -iTCP -sTCP:LISTEN` antes de asumir un puerto libre.
- **Gotcha de CORS:** FastAPI sin `CORSMiddleware` deja pasar la request en el servidor (log mostraba `200 OK`) pero el navegador bloquea la respuesta para JS — se ve como un fallo silencioso desde el frontend. Se agregó `CORSMiddleware` en `main.py` con origen `settings.frontend_base_url`.
- Probado end-to-end en navegador real (Chrome vía MCP): login, crear restaurante con menú, crear dos mesas, ver sus QR (imágenes distintas), regenerar QR de una mesa y confirmar que cambia.
- Próximo paso: Fase 2 — flujo del cliente (listado de restaurantes, reserva, escaneo de QR contra el `qr_token`, menú + carrito). El endpoint de canje del QR (validar `token` contra la mesa) todavía no existe, se construye en Fase 2.

### [2026-07-29] Fase 1 completa: modelo de datos y autenticación
- 8 tablas en `backend/app/models/`: `usuarios`, `restaurantes`, `mesas`, `reservas`, `pedidos`, `items_pedido`, `menu`, `facturas`. Migración inicial con Alembic (`alembic/versions/072d96094a7e_...py`), aplicada y verificada contra Postgres real (`\dt`, `\d reservas`).
- **Constraint anti-doble-reserva:** índice único parcial en Postgres — `UNIQUE (mesa_id, inicio) WHERE estado = 'activa'`. Reservas canceladas no bloquean el horario. Probado de verdad: segunda reserva activa mismo mesa/horario lanza `IntegrityError`; tras cancelar la primera, una nueva sí entra.
- Gotcha resuelto: los `Enum` de SQLAlchemy por default guardan el *nombre* del miembro Python (`ACTIVA`) en vez del *valor* (`activa`) — rompía el índice parcial que comparaba contra `'activa'`. Fix: `values_callable=lambda e: [m.value for m in e]` en los 3 enums (`Rol`, `EstadoReserva`, `EstadoPedido`).
- **Autenticación:** JWT (`pyjwt` + `bcrypt`, sin passlib por incompatibilidades conocidas con bcrypt>=4.1). `POST /auth/registro` (solo crea rol `cliente` — autoregistro), `POST /auth/login` (OAuth2 password flow), `GET /auth/me`. Dependencies en `app/core/deps.py`: `get_current_user` y `require_roles(*roles)`.
- **Pendiente:** no hay endpoint para crear usuarios `mesero`/`cocina`/`admin_restaurante`/`admin_general` todavía — eso llega con el panel de administrador (Fase 1.5) y necesita bootstrap manual para el primer `admin_general`.
- Gotcha de infraestructura: `pydantic-settings` con `env_file="../.env"` dependía del cwd del proceso — si uvicorn/alembic corrían desde otro directorio, cargaba el default silenciosamente en vez de fallar. Fix: ruta absoluta calculada con `Path(__file__)` en `config.py`.
- Suite de tests con `pytest` + `httpx` (`backend/tests/`), corrida contra Postgres real (no mocks, consistente con la decisión de este proyecto). 6/6 verde.
- Próximo paso: Fase 1.5 — panel de administrador general (alta de restaurante, CRUD de mesas, generación/regeneración de QR firmado).

### [2026-07-29] Fase 0 completa: estructura base backend/frontend
- Se crea `backend/` (FastAPI + SQLAlchemy, `app/{core,models,routers,schemas}`) y `frontend/` (Vue 3 + Vite + TypeScript + Vue Router + Pinia).
- `docker-compose.yml` levanta PostgreSQL local en puerto **5434** (5432 y 5433 ya ocupados por otros proyectos en esta máquina — ajustar si se despliega en otra máquina).
- Endpoint `/health` en FastAPI, probado contra Postgres real (conexión SQLAlchemy verificada, no solo import).
- Router de Vue con una vista placeholder por rol (`cliente`, `mesero`, `cocina`, `admin`) y guard de ruta (`router/index.ts`) contra un store `stores/auth.ts` — **stub**, sin autenticación real todavía (eso es Fase 1).
- Verificado end-to-end: build, typecheck (`vue-tsc`) y dev server sirviendo las rutas por rol en el navegador.
- Próximo paso: Fase 1 — modelo de datos en Postgres (tablas `restaurantes`, `mesas`, `reservas`, `usuarios`, `pedidos`, `items_pedido`, `menu`, `facturas`) + autenticación real por rol + constraint anti-doble-reserva.

### [pendiente] Rol de administrador general + QR por mesa
- Se agrega un cuarto rol: **administrador general**, dueño de dar de alta restaurantes en la plataforma (antes solo existían cliente/mesero/cocina/admin de restaurante).
- El admin general crea el restaurante, define sus mesas, y genera un **QR único por mesa**.
- **Diseño del QR:** no es solo un identificador visual — codifica una URL firmada con `restaurante_id` + `mesa_id` (ej: `/mesa/{restaurante_id}/{mesa_id}?token=...`). El token evita que alguien fabrique un QR falso apuntando a una mesa que no le corresponde.
- Al escanear, la app reutiliza el flujo ya existente de "llegada a la mesa": valida si el usuario que escanea tiene una reserva activa para esa mesa/horario, o si la mesa está libre y se le ofrece usarla sin reserva.
- Si un QR impreso se pierde o daña, el admin general puede **regenerar** el QR de esa mesa — el token anterior queda invalidado automáticamente para que el QR viejo no sirva.
- Pendiente de definir: librería de generación de QR en backend (ej. `qrcode` en Python) y si el token es JWT de corta duración o un hash almacenado en la tabla `mesas`.

### [Setup inicial]
- Se crean Brain.md, Readme.md, CONTRIBUTING.md, Plan.md.
- Se decide stack: Python + FastAPI, PostgreSQL, Vue 3.
- Próximo paso: definir modelo de datos inicial en Postgres (restaurantes, mesas, reservas, pedidos, items_pedido, facturas) y arrancar el flujo del cliente (ver restaurantes → mesas → reserva).
