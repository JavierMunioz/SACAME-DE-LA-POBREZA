# App de Reservas y Pedidos para Restaurantes

Aplicación web (navegador, sin app nativa) que conecta a **clientes**, **meseros** y **cocina** de restaurantes afiliados, cubriendo el ciclo completo desde la reserva de mesa hasta el pedido y la facturación en sitio.

## ¿Qué resuelve?

- Los clientes reservan mesa online y confirman su llegada escaneando el QR de la mesa.
- Si la mesa está libre y sin reserva, cualquier cliente puede pedir usarla sin necesidad de reserva previa.
- Una vez confirmada la mesa, el cliente ve el menú del restaurante y hace su pedido desde el celular.
- El mesero ve todos los pedidos entrantes en tiempo real desde una **comanda principal** (estación fija, táctil), revisa que sean coherentes y los confirma.
- Al confirmar, el pedido pasa automáticamente a la pantalla de cocina, ordenado por hora de llegada, con el detalle completo (observaciones incluidas).
- Desde la misma comanda principal, el mesero puede **generar la factura/voucher** de la mesa al cerrar el consumo.

## Roles

| Rol | Qué hace |
|---|---|
| **Administrador general** | Da de alta restaurantes en la plataforma, configura sus mesas y genera el código QR único de cada mesa |
| **Cliente** | Ve restaurantes afiliados → selecciona uno → ve mesas disponibles → reserva (fecha/hora) → llega y escanea QR → ve menú → pide |
| **Mesero** | Ve pedidos entrantes → confirma o cancela → gestiona mesas → genera factura/voucher desde la comanda principal |
| **Cocina** | Ve la comanda de pedidos confirmados, en orden de llegada, con el detalle de cada plato |

## Flujo del administrador general

1. Crea un restaurante nuevo (nombre, datos generales, menú inicial) para que quede disponible en el listado que ven los clientes.
2. Define las mesas de ese restaurante (número, capacidad).
3. Por cada mesa, genera un **código QR único** que la identifica.
4. El QR de cada mesa apunta a una URL que codifica `restaurante_id` + `mesa_id`. Al escanearlo, la app lleva al cliente directo al flujo de "llegada a la mesa" descrito arriba (valida si hay una reserva activa a su nombre, o si la mesa está libre para usarla sin reserva).
5. El administrador puede regenerar el QR de una mesa si se pierde o daña el impreso (el anterior queda invalidado).

## Flujo del cliente

1. Ve los restaurantes que tienen el servicio contratado.
2. Entra a un restaurante y ve su información general.
3. Ve las mesas disponibles, elige fecha y hora, reserva.
4. Debe llegar 15 minutos antes de su reserva.
5. Escanea el QR de la mesa:
   - **Si tenía reserva:** el sistema lo saluda por su nombre y confirma la reserva.
   - **Si no tenía reserva y la mesa está libre:** el sistema le pregunta si desea usarla; si acepta, se le asigna.
6. Ve el menú, agrega productos al carrito y envía el pedido.

## Flujo del mesero

1. Ve todos los pedidos en curso generados desde la app, en tiempo real.
2. Revisa cada pedido y confirma que sea coherente.
3. Al confirmar, el pedido se envía a cocina.
4. **Facturación:** desde la comanda principal, al cerrar la mesa el mesero puede generar la factura:
   - Se emite como el **voucher típico** con el que actualmente facturan los restaurantes en Colombia.
   - Se ofrece la opción de **incluir propina o no** antes de generar el total.
   - Hay un botón adicional de **"Factura electrónica"** — mostrado en gris, **aún no desarrollado** — reservado para una fase futura del proyecto (integración con facturación electrónica DIAN).

## Flujo de cocina

1. Recibe los pedidos confirmados por el mesero, ordenados por hora de llegada (FIFO).
2. Ve el detalle completo de cada pedido: mesa, productos, observaciones (ej. "sin cebolla").

## Stack técnico

Ver `Brain.md` para el detalle y las razones de cada decisión técnica.

- Backend: Python (FastAPI)
- Base de datos: PostgreSQL
- Frontend: Vue 3

## Estado del proyecto

En construcción. Ver `Plan.md` para el roadmap hacia el MVP.
