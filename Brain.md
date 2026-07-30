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

### [2026-07-30] Carrito compartido en vivo por WebSocket + solo el dueño de la mesa envía el pedido
Pedido directo del usuario tras la entrega de la sesión de mesa: el código de 4 dígitos ya permitía que varios dispositivos compartieran una sesión, pero cada uno tenía su propio carrito local — no se veían los platos que sumaba el otro hasta que alguien mandaba el pedido. Además cualquiera de la mesa podía enviar, no solo quien la abrió.

- **`token_dueno`** (columna nueva en `SesionMesa`, separada del `token` compartido): `POST /mesas/{id}/ocupar` devuelve ambos; `POST /mesas/{id}/unirse` solo devuelve el `token` compartido (`token_dueno: null`). `POST /pedidos` ahora valida el `sesion_token` recibido contra `token_dueno`, no contra `token` — un dispositivo que se sumó con el código puede ver y editar el carrito, pero un 401 lo frena si intenta enviar el pedido. Migración con backfill (filas viejas de `sesiones_mesa` reciben un `token_dueno` nuevo antes de poner la columna `NOT NULL`).
- **Carrito compartido en vivo:** `WS /mesas/{id}/ws?token=<token compartido>` (`app/core/carrito_mesa.py`, `GestorCarritosMesa`). Estado en memoria del proceso, no en Postgres — es pre-pedido, transitorio, y este proyecto no tiene infraestructura multi-worker/Redis (si algún día se escala a varios workers esto necesitaría moverse a pub/sub). Al conectar manda el snapshot actual; cualquier `{"accion":"set_item", menu_item_id, cantidad, observaciones}` de cualquier conectado se aplica y se rebroadcastea a todos los de esa mesa. Se limpia (broadcast de carrito vacío) al facturar (`generar_factura`, ahora `async def`) y al crear el pedido exitosamente — así todos los dispositivos ven el carrito vaciarse sin recargar.
- **Frontend (`MesaView.vue`):** el `carrito` reactivo dejó de mutarse a mano — `sumar`/`restar` mandan el mensaje WS y el render lo actualiza el broadcast entrante, así el número que ves es siempre el que el servidor confirmó, no un optimista local que puede desincronizarse. `esDueno = !!sesion.token_dueno` gatea el botón "Enviar pedido": quien se unió por código ve el carrito y puede sumar/restar, pero en la barra inferior le aparece "Solo quien abrió la mesa puede enviar" en vez del botón.
- Nueva ruta WS no pasa por el guard HTTP normal — la propia query `token` contra `SesionMesa.token` activa (`cerrada_at IS NULL`) es la autenticación; token inválido cierra la conexión con código `4401`.
- **Probado en vivo con dos pestañas** (limpiando `localStorage` entre ellas): dueña reclama mesa → segundo dispositivo se une con el código de 4 dígitos → ese dispositivo suma un plato → aparece al instante en la pantalla de la dueña sin recargar → dueña envía el pedido → el carrito se vacía en tiempo real también en el dispositivo del que se sumó.
- 2 tests nuevos de WebSocket (`test_fase8_carrito_ws.py`, usando `TestClient.websocket_connect`) + 1 test reescrito de "ambos pueden pedir" a "solo el dueño puede pedir" (`test_solo_el_dueno_puede_enviar_el_pedido`). Suite completa: 49/49.

### [2026-07-30] Sesión de mesa: estados libre/reservada/ocupada, check-in con auto-liberación, código de 4 dígitos para compartir
Pedido directo del usuario tras probar el flujo de invitado: pedir sin cuenta funcionaba pero no sabíamos quién pedía, y cualquier dispositivo podía escanear la misma mesa y pedir por separado sin saberlo — cero bloqueo real. Se agregó un concepto de dominio nuevo: **sesión de mesa**.

- **`Mesa.estado`** (nuevo, `libre`/`ocupada`, enum stored): transaccional, cambia por evento (se ocupa al reclamar, se libera al facturar). Deliberadamente NO incluye `reservada` — ese estado es function de la hora actual contra la ventana de una reserva, y guardarlo arrastraría un valor viejo sin un cron que lo actualice. `reservada` se computa al vuelo en `GET /mesas/qr/{token}` (campo `estado` del schema, tri-estado de presentación) reusando el cálculo de `mesa_libre_ahora` que ya existía.
- **`SesionMesa`** (tabla nueva): se abre cuando alguien reclama la mesa — invitado con nombre (`POST /mesas/{id}/ocupar` con `nombre_invitado`), cliente logueado sin reserva, o cliente con reserva propia (`reserva_id`, hace check-in). Tiene un `token` opaco (autoriza pedir) y un `codigo_acceso` de 4 dígitos (lo que el que abrió la mesa comparte de palabra con el resto). Índice único parcial `WHERE cerrada_at IS NULL`: solo una sesión abierta por mesa. `POST /mesas/{id}/unirse` con el código devuelve el mismo token — todos los dispositivos de la mesa comparten sesión y ven/piden lo mismo.
- **Pedido** ahora tiene `sesion_mesa_id` y `nombre_invitado` (snapshot al momento del pedido, no sigue cambios posteriores de la sesión). `POST /pedidos` exige `sesion_token` si quien pide es anónimo (401 si falta o si la sesión ya cerró) — un invitado ya no puede pedir sin haber reclamado la mesa primero. Para clientes logueados el `sesion_token` es opcional (compatibilidad con el flujo directo que ya tenían mesero/cocina/admin en sus tests, que no ejercitan el escaneo real).
- **Check-in de reserva:** `MINUTOS_LLEGADA_ANTICIPADA = 15` (ya existía como ventana de bloqueo) se reutiliza como **plazo de check-in**: si no se hace `POST /mesas/{id}/ocupar` con `reserva_id` antes de `inicio - 15min`, la reserva se marca `EXPIRADA` sola (lazy, corrida en cada lectura relevante — no hay worker en background en este proyecto) y la mesa queda libre para otro. Excepción necesaria: una reserva hecha *después* de su propio plazo de check-in (ej. "reservo para ahora mismo") no expira — no tuvo ventana real para hacer check-in con anticipación (`if r.created_at >= deadline: continue`). Sin esto, `test_canje_qr_con_reserva_propia` fallaba: una reserva creada con `inicio=ahora` se auto-expiraba en el mismo request que la creaba.
- **Cierre:** generar factura (`POST /mesas/{id}/factura`, el "cerrar mesa" del mesero) ahora también cierra la `SesionMesa` activa y pone `Mesa.estado = libre` — no hay un endpoint separado de "cerrar mesa", ese ya era el momento real de cierre en el dominio.
- **Frontend (`MesaView.vue`):** guarda el `SesionMesa` en `localStorage` por mesa (`sesion-mesa-{id}`) para sobrevivir un reload sin volver a pedir nombre/código. Al cargar, si la mesa ya no requiere código (se liberó, ej. por factura) descarta cualquier sesión guardada vieja — verificado en vivo: recargar después de facturar vuelve a pedir el nombre en vez de mostrar el menú viejo. Si un pedido falla con 401 (sesión cerrada en el medio), limpia el storage y muestra el estado de "hay que volver a abrir la mesa" en vez de un error genérico.
- **Mesero** ahora ve `nombre_invitado` en la tarjeta de cada pedido de invitado (`mesero/HomeView.vue`), con chip "invitado" — es la respuesta directa a "necesito saber quién pidió".
- **Admin** ve badge libre/ocupada en cada tarjeta de mesa (`RestauranteDetalleView.vue`), reusando los tokens semánticos success/danger del design system Epicurean.
- **Probado en vivo con dos pestañas** simulando dos dispositivos (limpiando `localStorage` entre ellas para no compartir sesión falsamente, ya que ambas viven en el mismo perfil de Chrome): dispositivo 1 reclama con nombre → dispositivo 2 ve "mesa ocupada", código incorrecto rechaza (401), código correcto une la sesión y pide con el mismo `token` → mesero confirma y factura → mesa vuelve a `libre` y la sesión queda `cerrada_at` seteado → dispositivo 1 recarga y la app descarta su sesión vieja y vuelve a pedir nombre.
- **Deliberadamente NO implementado:** un job en background que expire reservas proactivamente (se resuelve lazy, en cada lectura relevante, consistente con el patrón ya usado en el resto del proyecto); mostrar `nombre_invitado` en la pantalla de cocina (no lo pidió el usuario, cocina trabaja por número de orden no por comensal).
- Suite completa: 46/46 (5 tests nuevos en `test_fase7_sesiones_mesa.py`, más los 2 tests de `test_fase6_invitado.py` reescritos para el nuevo flujo).

### [2026-07-30] Pivot de design system: de la paleta esmeralda propia a "Epicurean" (export de Google Stitch)
El usuario rechazó el rediseño esmeralda de la entrada anterior ("un asko diseñando") y proveyó su propia línea de diseño: un export de Google Stitch (`stitch_gastroflow_os.zip`) con un `DESIGN.md` (tokens YAML + prosa, sistema "Epicurean System") y 4 mockups HTML/PNG (admin dashboard, KDS, comanda mesero, menú cliente mobile). Se abandonó la paleta esmeralda propia y se reconstruyó el design system para calzar exacto con esos tokens, reusando la arquitectura funcional ya construida.

- **Paleta:** negro/"Modern Charcoal" `#18181b` como primario (botones, marca, texto de alta jerarquía) + "Gastro Indigo" `#4f46e5` como acento funcional único (links, hover, foco, badges activos). Nada de verde esmeralda ni beige.
- **Tipografía:** `Geist Variable` (antes Outfit) + `Geist Mono Variable` (nuevo, para números de orden/precios/reloj — alineación vertical perfecta en tablas).
- **Tokens:** radios (`sm:.5rem md:.75rem lg:1rem xl:1.5rem full`), sombras (`--shadow-sm/md/lg` con valores exactos del DESIGN.md), espaciado en escala de 4px, sidebar fijo de 280px.
- **Componente nuevo:** `AppSidebar.vue` — sidebar reusable (280px, logo negro con ícono `KnifeFork`, footer con salir) usado en admin y mesero. Cocina NO lleva sidebar (KDS full-width, fiel al mockup).
- **Feature real agregada (no cosmética):** el mockup de KDS mostraba estados intermedios de cocina que no existían (`EstadoPedido` solo tenía pendiente→confirmado→entregado). Se agregó `PREPARANDO` y `LISTO` de verdad: migración Alembic (`ALTER TYPE ... ADD VALUE`, no se puede hacer downgrade de un enum en Postgres), dos endpoints nuevos (`marcar-preparando`, `marcar-listo`, ambos 409 si el estado previo no es el esperado), filtro de cocina por `estado IN (confirmado, preparando, listo)`, y facturación ahora acepta pedidos en cualquiera de esos 3 estados (antes solo `confirmado`). 5 tests nuevos en `test_fase6_kds.py`, suite completa 37/37.
- **Qué se dejó fuera a propósito (aunque el mockup lo mostraba):** la vista de mesero NO se convirtió en un mapa de mesas literal (requeriría un concepto nuevo de "estado de mesa" persistente que no existe en el dominio — hoy solo `Pedido.estado` existe, no hay máquina de estados por mesa). Tampoco se fabricaron fotos de platos, categorías de menú, ni flag de "especial del chef" (el modelo `MenuItem` no tiene esos campos). Se aplicó el lenguaje visual del mockup a la estructura de datos real, no al revés.
- **Gotcha de credenciales de prueba:** para probar en navegador real se resetearon las contraseñas de las cuentas seed (`admin@sacame.dev`, `mesero1@sacame.dev`, `cocina1@sacame.dev`) a `Test1234!` vía script directo con `hash_password` — no hay endpoint de reset, es solo para desarrollo local.
- Probado end-to-end en navegador real: login admin (sidebar + personal + QR), cocina (click real Preparando→Listo, contador de footer actualiza, toast de "mesa lista"), mesero (ve el pedido como "LISTO PARA SERVIR" con el badge correcto), y guest checkout completo (escaneo QR sin cuenta → carrito → pedido enviado → verificado en Postgres `cliente_id = NULL`).
- Recordatorio de infraestructura (ya documentado antes, se repitió el error en esta sesión): el frontend por default apunta a `VITE_API_BASE_URL=http://localhost:8001`, no 8000 — arrancar el backend en el puerto equivocado da "Email o contraseña incorrectos" en vez de un error de red claro, porque el login falla silenciosamente contra un backend que no es el correcto.
- Próximo paso: mergear PR (retoma el mismo PR #13, ahora con el pivot de paleta) y seguir con lo que quede del roadmap original si el usuario lo pide.

### [2026-07-30] Pedido sin cuenta (guest checkout) + rediseño completo del design system (obsoleto, paleta reemplazada — ver entrada de arriba)
Esto no es una fase del roadmap original — pedido directo del usuario tras probar el MVP: (1) bug real, no se podía pedir sin crear cuenta; (2) el look visual era "horrible", pidió un rediseño a nivel Stripe/Linear/Notion/Toast POS con un brief extenso de Principal Product Designer.

**Guest checkout (backend):**
- `get_current_user_opcional` en `deps.py`: como `get_current_user` pero devuelve `None` en vez de 401 si no hay token o es inválido (usa `OAuth2PasswordBearer(auto_error=False)`).
- `GET /mesas/qr/{token}` y `POST /pedidos` ahora aceptan tanto invitado como cliente logueado. Si hay usuario pero no es rol `cliente` (ej. un mesero), 403. `Pedido.cliente_id` queda `NULL` para invitados (el modelo ya lo soportaba desde Fase 1, nullable).
- `/cliente` y `/cliente/restaurantes/:id` ahora son rutas públicas (sin `meta.rol`) — bar navegar y ver el menú no requiere cuenta. Reservar sí, porque necesita identidad para el saludo al escanear el QR — el gate se aplica recién al hacer click en "Reservar" (`if (!auth.token) router.push('/login?redirect=...')`), no antes.
- **Decisión de diseño:** reservar mesa con anticipación sigue pidiendo cuenta; escanear el QR de una mesa y pedir en el momento no. Es la distinción real entre "necesito saber quién sos para saludarte/reservarte" vs. "solo necesito saber qué mesa y qué pediste".

**Rediseño (design system):**
- La taste skill (`design-taste-frontend`) fue invocada de nuevo. Marca explícitamente los paneles operativos (mesero/cocina/admin) como fuera de su alcance (Sección 13: "dashboards / dense product UI", usar un design system real en vez de sus reglas de landing page) — se adaptó el espíritu (paleta, tipografía, densidad, estados) sin aplicarle literalmente las reglas de landing page a esas 3 pantallas.
- **Paleta:** un solo acento (verde esmeralda `#10a05f`), grises cálidos neutros (nunca negro/blanco puro), estados semánticos (verde=confirmado, naranja=pendiente, rojo=cancelado, azul=info). Deliberadamente NO beige+brass (paleta prohibida por la skill para briefs "premium consumer") y NO AI-purple.
- **Tipografía:** `Outfit Variable` (headings) + `Inter Variable` (body), self-hosted vía `@fontsource-variable/*` (cero llamadas de red externas). Inter para body es una excepción consciente a la regla "Inter discouraged as default" de la skill — se justifica porque el brief pide explícitamente pensar en "usuarios con poca experiencia tecnológica" y Inter es la opción de máxima legibilidad probada, no un default perezoso.
- **Implementación técnica:** sin React/Tailwind (proyecto es Vue 3), así que el sistema es CSS custom properties puras (`frontend/src/assets/design-system.css`) que también sobrescriben las variables `--el-*` de Element Plus (cargado antes que nuestro CSS a propósito, para que gane la cascada) — así los componentes de Element Plus (inputs, diálogos, tablas) heredan el sistema en vez de mantener dos lenguajes visuales en paralelo.
- Se rediseñaron las 8 vistas existentes: Login, Registro, cliente (listado + detalle/reserva + pantalla de QR/menú/carrito con barra sticky de checkout), mesero (comanda agrupada + facturación), cocina (estilo KDS: tarjetas grandes, tiempo transcurrido en vivo con escalado de color por urgencia), admin (restaurantes + detalle con mesas/QR/personal).
- **Qué NO se construyó, a propósito:** el brief del usuario listaba decenas de pantallas que no existen todavía como feature (galería, mapa, horario, categorías/buscador/filtros de menú, estados "preparando/listo" en cocina — solo existe pendiente→confirmado→entregado, dashboard de estadísticas admin, gestión de usuarios/configuración). Construir eso es features nuevas, no rediseño de lo que ya está, y se dejó fuera de esta pasada para no inflar el scope sin que el usuario lo pida explícitamente. Si en algún momento se quiere agregar estados intermedios de cocina ("preparando"), es un cambio de arquitectura real (nuevo estado en `EstadoPedido`, visibilidad cruzada mesero/cocina), no cosmético.
- Gotcha de build: `npx vue-tsc --noEmit` manual no atrapó 2 errores reales que sí aparecieron en `npm run build` (que corre `vue-tsc` con otra configuración/rigor). Los errores eran legítimos: acceso a índice de `Record` sin narrow (`qrUrls[mesa.id]` podía ser `undefined`, TS no narrowea una segunda lectura de la misma expresión de índice sin pasar por una constante local) y `window` referenciado directo en el template de un SFC (hay que exponerlo vía una función en `<script setup>`, no usarlo suelto en el `@click`). **Lección: correr `npm run build` real antes de dar por cerrada una tarea de frontend, no solo el typecheck standalone.**
- Probado end-to-end en navegador real: pedido completo sin cuenta (verificado `cliente_id = NULL` en la base), visible en la comanda del mesero y en cocina con badge/tiempo correctos, gate de reserva redirige a login con `redirect` query, panel admin funcionando con el nuevo sistema.

### [2026-07-30] Fase 5 completa: facturación
- Backend: `POST /mesas/{id}/factura` (mesero/admin_restaurante) agrupa todos los pedidos `confirmado` sin facturar de la mesa, calcula `subtotal` (suma de `cantidad * precio_unitario` de todos sus items), `propina` opcional (`porcentaje_propina`, default 10%) y `total`. Al facturar, cada pedido pasa a `entregado` y queda linkeado con `factura_id` — así no se puede facturar dos veces lo mismo (422 si se reintenta sobre una mesa sin pedidos confirmados pendientes).
- Solo se factura lo `confirmado` (ya pasó por cocina), nunca lo `pendiente` — no tiene sentido cobrar algo que la cocina ni recibió todavía.
- `GET /facturas/{id}` para reconsultar el voucher ya emitido.
- Frontend: la comanda del mesero ahora agrupa las mesas con pedidos confirmados en una franja "Listas para cerrar", con un botón por mesa. Al cerrar se abre un diálogo (propina sí/no + porcentaje) y después un voucher imprimible: ítems, subtotal, propina (solo si aplica), total, y el botón **"Factura electrónica" deshabilitado en gris** tal como pide el Readme (reservado para una fase futura con DIAN).
- Probado en vivo con dos mesas reales: una con propina (10% sobre $112.000 = $11.200, total $123.200) y otra sin propina (total = subtotal, sin mostrar la línea de propina). Verificado también contra la base de datos: pedido pasa a `entregado` con el `factura_id` correcto.
- 6 tests nuevos (29 en total): factura con/sin propina, no se puede facturar dos veces, no se puede facturar mesa sin pedidos confirmados, obtener factura, cliente no puede facturar (403).
- **Todos los PRs de fases 0 a 4 se mergearon a `main`** en esta sesión (PRs #1, #7, #8, #9, #10, #11 — los #2 a #6 originales quedaron cerrados/huérfanos porque GitHub cierra automáticamente un PR apilado cuando se borra su rama base al mergear el anterior; se resolvió rebaseando cada rama sobre `main` actualizado y abriendo un PR de reemplazo apuntando directo a `main`). Lección para la próxima tanda de PRs apilados: o no usar `--delete-branch` hasta mergear todo el stack, o mergear con retarget manual de la base antes de borrar.
- Con Fase 5 el ciclo de negocio queda funcionalmente completo: reserva → pedido → confirmación → cocina → factura. Falta Fase 6 (endurecimiento para producción): manejo de errores/reconexión, logs, variables de entorno y despliegue, pruebas de carga.

### [2026-07-29] Fase 4 completa: flujo de cocina
- Backend: `GET /pedidos` ahora acepta rol `cocina` además de mesero/admin_restaurante, y un query param `estado` opcional. **Detalle importante:** cuando se filtra por `estado=confirmado`, el orden pasa de `created_at` a `confirmado_at` — el FIFO de cocina es por hora de llegada *a cocina* (cuándo el mesero confirmó), no por hora en que el cliente hizo el pedido. Probado explícitamente con un caso donde el pedido creado primero se confirma segundo: aparece segundo en la comanda de cocina, no primero.
- Frontend: `cocina/HomeView.vue`, mismo patrón de polling que `mesero/HomeView.vue` (5s), pero de solo lectura — sin botones de confirmar/cancelar (esos son atribución del mesero, no de cocina; el backend también lo bloquea con 403 si cocina intenta pegarle a esos endpoints).
- Cuenta de cocina se crea desde el mismo diálogo "Nueva cuenta" del panel admin que ya existía para mesero (el selector de rol ya incluía "Cocina" desde Fase 3, no hizo falta tocar esa UI).
- Probado end-to-end en navegador real: dos pedidos confirmados en orden inverso al de creación, la comanda de cocina los muestra en el orden de confirmación correcto (#1 el confirmado primero), con observaciones destacadas visualmente.
- Con Fase 4 se completa el ciclo completo cliente → mesero → cocina descrito en el Readme. Falta Fase 5 (facturación) y Fase 6 (endurecimiento para producción).

### [2026-07-29] Fase 3 completa: flujo del mesero
- **Prerequisito no contemplado en el Plan original:** no existía forma de crear cuentas `mesero`/`cocina`/`admin_restaurante` (solo bootstrap de `admin_general` por CLI y autoregistro de `cliente`). Se agregó `POST /restaurantes/{id}/personal` (admin_general) y una sección "Personal" en el panel admin (`RestauranteDetalleView.vue`) para altas de personal scoped a un restaurante.
- Backend: `GET /pedidos` (mesero o admin_restaurante, filtrado por `usuario.restaurante_id`), `POST /pedidos/{id}/confirmar`, `POST /pedidos/{id}/cancelar`. Ambos solo permiten actuar sobre pedidos `pendiente` (409 si no) y están scoped al restaurante del mesero — probado que un mesero de otro restaurante ni ve ni puede confirmar pedidos ajenos (test + verificado a mano).
- **"Tiempo real" implementado como polling simple** (`setInterval` cada 5s en `mesero/HomeView.vue`), no WebSockets. Decisión consciente y documentada, consistente con la nota original de este archivo ("si más adelante se necesita tiempo real, se puede sumar Redis o WebSockets — no es obligatorio ahora"). Si el volumen de pedidos crece o la latencia de 5s se vuelve un problema real, ahí se justifica el salto a WebSockets nativos de FastAPI.
- **Bug real encontrado y corregido en el guard del router:** cuando un usuario autenticado con un rol entraba (por URL directa, no navegación in-app) a una ruta que exige otro rol, el guard hacía `return false` — Vue Router cancela la navegación pero, al ser una carga de página fresca, no hay "ruta anterior" a la que volver: quedaba una pantalla en blanco sin ningún mensaje. Se detectó probando el panel admin logueado como mesero por error. Fix: el guard ahora redirige al home del rol real del usuario (mapa `rolAHome` centralizado en `stores/auth.ts`, reusado también en `LoginView.vue` para no duplicarlo).
- Gotcha de tests (otra vez el mismo patrón que Fase 2, pero con una FK nueva): el fixture `mesero_autenticado` crea un `Usuario` con `restaurante_id` apuntando al restaurante de test — si `restaurante_con_mesa` intentaba borrar el restaurante sin borrar antes ese personal, el DELETE fallaba por FK y dejaba basura que bloqueaba corridas futuras. Mismo fix de siempre: borrar dependientes antes, en el orden correcto.
- **Nota para más adelante (Fase 6 / infraestructura de tests):** esta sesión viene reusando la base de datos de desarrollo real para correr los tests, con limpieza manual cuando algo queda huérfano por una corrida fallida. Funciona pero es frágil. La solución de fondo es una base de datos de test dedicada y efímera (se crea y se destruye por corrida, o al menos por sesión de CI) para que un test roto nunca deje basura que afecte corridas futuras.
- Probado end-to-end en navegador real: admin crea cuenta de mesero desde el panel → login como mesero → comanda muestra los pedidos reales de Fase 2 (con sus observaciones) → confirmar pasa a estado "confirmado" y desaparecen los botones → verificado también contra la base de datos.
- Próximo paso: Fase 4 — flujo de cocina (mismo patrón de polling, filtra por `estado=confirmado`, orden FIFO por `confirmado_at`).

### [2026-07-29] Fase 2 completa: flujo del cliente
- Backend: `GET /restaurantes/{id}/disponibilidad` (público, calcula mesas ocupadas por solapamiento de horario en Python, no en SQL — volumen bajo, no lo justifica), `POST /reservas` (rol cliente, usa el constraint anti-doble-reserva de Fase 1), `GET /mesas/qr/{token}` (canje de QR: identifica mesa+restaurante+menú y si el usuario autenticado tiene reserva propia vigente o si la mesa está libre ahora mismo), `POST /pedidos` (rol cliente, valida que los ítems de menú pertenezcan al restaurante de la mesa, congela `precio_unitario`).
- **Regla de "reserva vigente":** ventana de `reserva.inicio - 15min` a `reserva.inicio + duracion_minutos` (los 15 min replican la regla del Readme de llegar antes). Fuera de esa ventana la mesa se considera libre aunque tenga una reserva activa para más tarde — se probó en vivo: reserva para las 20:00 de hoy, mesa sigue apareciendo "libre ahora" a media tarde.
- **Limitación conocida y aceptada:** el constraint de DB (Fase 1) es un unique exacto sobre `(mesa_id, inicio)`, no un exclusion constraint por rango. Dos reservas con `inicio` distinto pero horarios que se solapan en duración NO están bloqueadas a nivel de base de datos — el endpoint de disponibilidad sí detecta el solapamiento (chequeo en Python), pero nada impide crear la reserva vía API si el cliente ignora la disponibilidad mostrada. Aceptado como simplificación de MVP; si se vuelve un problema real, la solución es un exclusion constraint de Postgres con `btree_gist` sobre un rango `tsrange`.
- Frontend: `RegistroView.vue` (autoregistro, siempre rol cliente), `cliente/HomeView.vue` (listado real), `cliente/RestauranteView.vue` (buscar disponibilidad por fecha/hora + reservar), `MesaView.vue` en `/mesa/:restauranteId/:mesaId?token=` (pantalla que resulta de escanear el QR: saluda por nombre si hay reserva propia, ofrece "usar esta mesa" si está libre, o avisa que está ocupada; carrito local con +/- por ítem, envía el pedido y vuelve a `/cliente`).
- Router: se agregó un segundo tipo de ruta protegida (`meta.requiereAuth`) distinta de las rutas por rol (`meta.rol`) — la pantalla de mesa no pertenece a ningún rol específico, solo necesita saber quién escanea para el chequeo de reserva propia.
- Tests: `tests/test_fase2.py` (8 tests) contra Postgres real, mismo criterio que Fase 1 (nada de mocks).
- Gotcha de tests: la limpieza automática de usuarios de prueba (`cleanup_usuarios_de_test` en `conftest.py`) fallaba por FK si un test dejaba reservas/pedidos sin borrar antes de intentar borrar el usuario — un test que rompe a mitad de camino dejaba basura que bloqueaba el cleanup de **todas** las corridas siguientes (incluso tests que no tenían nada que ver). Se hizo el cleanup defensivo: borra reservas/pedidos/items de los usuarios de test antes de borrar los usuarios, no solo lo que cada fixture cree que creó.
- Probado end-to-end en navegador real: registro→login→listado→reserva de mesa→escaneo de QR real (caso mesa libre con "usar esta mesa" y caso reserva propia con saludo)→carrito→pedido, verificado también contra la base de datos directamente.
- Próximo paso: Fase 3 — flujo del mesero (comanda principal con los pedidos entrantes en tiempo real, confirmar/cancelar, envío a cocina). Ahí probablemente entra WebSockets o polling, ver la nota de Brain.md sobre Redis/WebSockets como capa adicional a Postgres.

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
