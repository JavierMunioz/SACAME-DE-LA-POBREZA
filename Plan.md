# Plan.md — Roadmap hacia el MVP

Plan derivado de `Readme.md`. Cada fase se marca como completa solo cuando funciona de punta a punta, no solo cuando el código "está escrito".

---

## Fase 0 — Setup del proyecto
- [x] Repositorio inicial + estructura de carpetas (`backend/`, `frontend/`)
- [x] PostgreSQL corriendo local (docker-compose)
- [x] FastAPI base + conexión a la base de datos
- [x] Vue 3 base + routing por rol

## Fase 1 — Modelo de datos y autenticación
- [x] Tablas: `restaurantes`, `mesas`, `reservas`, `usuarios`, `pedidos`, `items_pedido`, `menu`, `facturas`
- [x] Constraint que impide doble reserva de la misma mesa en el mismo horario
- [x] Autenticación básica y roles (**administrador general** / cliente / mesero / cocina / admin restaurante)

## Fase 1.5 — Administrador general
- [x] Panel para crear un restaurante nuevo (datos generales + menú inicial)
- [x] CRUD de mesas por restaurante (número, capacidad)
- [x] Generación de código QR único por mesa (URL con `restaurante_id` + `mesa_id`)
- [x] Regenerar/invalidar QR de una mesa (si se pierde o daña el impreso)
- [x] Vista para descargar/imprimir el lote de QRs de un restaurante

## Fase 2 — Flujo del cliente
- [x] Listado de restaurantes afiliados
- [x] Vista de restaurante + mesas disponibles por fecha/hora
- [x] Reserva online
- [x] Escaneo de QR de mesa:
  - [x] Caso: reserva propia confirmada
  - [x] Caso: mesa libre sin reserva → aceptar uso
- [x] Menú + carrito + envío de pedido

## Fase 3 — Flujo del mesero
- [x] Comanda principal (estación fija, táctil): lista de pedidos entrantes en tiempo real
- [x] Confirmar / cancelar pedido
- [x] Envío del pedido confirmado a cocina

## Fase 4 — Flujo de cocina
- [ ] Pantalla de comanda de cocina, orden FIFO por hora de llegada
- [ ] Detalle completo del pedido (mesa, productos, observaciones)

## Fase 5 — Facturación
- [ ] Generar voucher de factura desde la comanda principal
- [ ] Opción de incluir propina o no
- [ ] Botón "Factura electrónica" visible pero deshabilitado (en gris) — no se desarrolla en esta fase

## Fase 6 — Endurecimiento para producción
- [ ] Manejo de errores y reconexión en tiempo real (mesero/cocina)
- [ ] Logs y monitoreo básico
- [ ] Variables de entorno y despliegue (definir hosting)
- [ ] Pruebas de carga básicas en horario pico simulado

---

## Fuera de alcance del MVP (explícitamente pospuesto)
- Facturación electrónica DIAN real
- Pagos en línea desde la app
- Multi-idioma
- App nativa (se mantiene 100% navegador)
