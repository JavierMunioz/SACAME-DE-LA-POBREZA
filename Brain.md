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
