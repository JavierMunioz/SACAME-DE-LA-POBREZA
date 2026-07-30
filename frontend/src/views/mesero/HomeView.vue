<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Tickets, Grid } from '@element-plus/icons-vue'
import {
  cancelarPedido,
  confirmarPedido,
  crearPedido,
  listarPedidos,
  marcarEntregado,
  type Pedido,
} from '../../api/pedidos'
import { generarFactura, type Factura } from '../../api/facturas'
import { liberarMesa, ocuparMesaStaff } from '../../api/mesas'
import { listarMesas, obtenerRestaurante, type Mesa, type MenuItem } from '../../api/restaurantes'
import { useAuthStore } from '../../stores/auth'
import AppTopNav from '../../components/AppTopNav.vue'

// Sin infraestructura de tiempo real todavía (ver Brain.md): se refresca
// por polling cada 5s, simple y suficiente para el volumen de un MVP.
const INTERVALO_POLLING_MS = 5000

const pedidos = ref<Pedido[]>([])
const cargando = ref(true)
const procesando = ref<number | null>(null)
let intervalo: ReturnType<typeof setInterval> | undefined

const router = useRouter()
const auth = useAuthStore()

const vista = ref<'pedidos' | 'mesas'>('pedidos')
const mesas = ref<Mesa[]>([])
const menu = ref<MenuItem[]>([])
const cargandoMesas = ref(true)
const procesandoMesa = ref<number | null>(null)

async function cargar() {
  pedidos.value = await listarPedidos()
  cargando.value = false
}

async function cargarMesas() {
  if (!auth.usuario?.restaurante_id) return
  const [m, r] = await Promise.all([
    listarMesas(auth.usuario.restaurante_id),
    obtenerRestaurante(auth.usuario.restaurante_id),
  ])
  mesas.value = m
  menu.value = r.menu
  cargandoMesas.value = false
}

const ESTADOS_ACTIVOS = ['pendiente', 'confirmado', 'preparando', 'listo']

// Una vez entregado, el pedido sale de la comanda activa (ya no hay nada
// que el mesero tenga que hacer con él salvo facturarlo). Solo se puede
// facturar lo entregado (ver Brain.md) — "listo" es cocina avisando que
// ya se puede servir, no que ya se sirvió.
const pedidosActivos = computed(() =>
  pedidos.value.filter((p) => ESTADOS_ACTIVOS.includes(p.estado)),
)

const mesasParaCerrar = computed(() => {
  const vistas = new Map<number, number>()
  for (const p of pedidos.value) {
    if (p.estado === 'entregado' && p.factura_id === null) vistas.set(p.mesa_id, p.mesa_numero)
  }
  return [...vistas.entries()].map(([mesa_id, mesa_numero]) => ({ mesa_id, mesa_numero }))
})

const etiquetaEstado: Record<string, string> = {
  pendiente: 'Pendiente',
  confirmado: 'En cocina',
  preparando: 'Preparando',
  listo: 'Listo para servir',
  entregado: 'Entregado',
}

async function confirmar(pedido: Pedido) {
  procesando.value = pedido.id
  try {
    await confirmarPedido(pedido.id)
    ElMessage.success(`Mesa ${pedido.mesa_numero} enviada a cocina`)
    await cargar()
  } catch {
    ElMessage.error('No se pudo confirmar el pedido')
  } finally {
    procesando.value = null
  }
}

async function cancelar(pedido: Pedido) {
  procesando.value = pedido.id
  try {
    await cancelarPedido(pedido.id)
    ElMessage.info(`Pedido de mesa ${pedido.mesa_numero} cancelado`)
    await cargar()
  } catch {
    ElMessage.error('No se pudo cancelar el pedido')
  } finally {
    procesando.value = null
  }
}

async function entregar(pedido: Pedido) {
  procesando.value = pedido.id
  try {
    await marcarEntregado(pedido.id)
    ElMessage.success(`Mesa ${pedido.mesa_numero} entregada`)
    await cargar()
  } catch {
    ElMessage.error('No se pudo marcar como entregado')
  } finally {
    procesando.value = null
  }
}

const dialogoFacturaAbierto = ref(false)
const generandoFactura = ref(false)
const mesaAFacturar = ref<{ mesa_id: number; mesa_numero: number } | null>(null)
const formFactura = reactive({ incluirPropina: false, porcentaje: 10 })

const voucherAbierto = ref(false)
const voucher = ref<Factura | null>(null)

function abrirDialogoFactura(mesa: { mesa_id: number; mesa_numero: number }) {
  mesaAFacturar.value = mesa
  formFactura.incluirPropina = false
  formFactura.porcentaje = 10
  dialogoFacturaAbierto.value = true
}

async function confirmarFactura() {
  if (!mesaAFacturar.value) return
  generandoFactura.value = true
  try {
    voucher.value = await generarFactura(mesaAFacturar.value.mesa_id, {
      incluye_propina: formFactura.incluirPropina,
      porcentaje_propina: (formFactura.porcentaje / 100).toFixed(2),
    })
    dialogoFacturaAbierto.value = false
    voucherAbierto.value = true
    await cargar()
  } catch {
    ElMessage.error('No se pudo generar la factura')
  } finally {
    generandoFactura.value = false
  }
}

function cerrarSesion() {
  auth.logout()
  router.push('/login')
}

function imprimir() {
  window.print()
}

const etiquetaEstadoMesa: Record<Mesa['estado'], string> = {
  libre: 'Libre',
  reservada: 'Reservada',
  ocupada: 'Ocupada',
}

const dialogoOcuparAbierto = ref(false)
const mesaAOcupar = ref<Mesa | null>(null)
const nombreOcupar = ref('')

function abrirDialogoOcupar(mesa: Mesa) {
  mesaAOcupar.value = mesa
  nombreOcupar.value = ''
  dialogoOcuparAbierto.value = true
}

async function confirmarOcupar() {
  if (!mesaAOcupar.value) return
  const numero = mesaAOcupar.value.numero
  procesandoMesa.value = mesaAOcupar.value.id
  try {
    const sesion = await ocuparMesaStaff(mesaAOcupar.value.id, nombreOcupar.value || undefined)
    dialogoOcuparAbierto.value = false
    await cargarMesas()
    await ElMessageBox.alert(
      `Código de acceso: <strong style="font-size:1.5rem;letter-spacing:0.1em">${sesion.codigo_acceso}</strong><br>Si el cliente quiere pedir después desde su celular, escanea el QR de la mesa y usa este código para sumarse.`,
      `Mesa ${numero} ocupada`,
      { dangerouslyUseHTMLString: true, confirmButtonText: 'Listo' },
    )
  } catch {
    ElMessage.error('No se pudo ocupar la mesa')
  } finally {
    procesandoMesa.value = null
  }
}

async function liberar(mesa: Mesa) {
  try {
    await ElMessageBox.confirm(
      `¿Liberar la mesa ${mesa.numero}? Esto no genera factura.`,
      'Liberar mesa',
      { type: 'warning' },
    )
  } catch {
    return
  }
  procesandoMesa.value = mesa.id
  try {
    await liberarMesa(mesa.id)
    ElMessage.success(`Mesa ${mesa.numero} liberada`)
    await cargarMesas()
  } catch (e: unknown) {
    const status = (e as { response?: { status?: number } })?.response?.status
    ElMessage.error(
      status === 409
        ? 'Esta mesa tiene pedidos sin facturar. Facturá primero.'
        : 'No se pudo liberar la mesa',
    )
  } finally {
    procesandoMesa.value = null
  }
}

const dialogoPedidoAbierto = ref(false)
const mesaPedido = ref<Mesa | null>(null)
const cantidades = reactive<Record<number, number>>({})
const observacionesPorItem = reactive<Record<number, string>>({})
const enviandoPedido = ref(false)

function abrirDialogoPedido(mesa: Mesa) {
  mesaPedido.value = mesa
  for (const key of Object.keys(cantidades)) delete cantidades[Number(key)]
  for (const key of Object.keys(observacionesPorItem)) delete observacionesPorItem[Number(key)]
  dialogoPedidoAbierto.value = true
}

const itemsSeleccionados = computed(() =>
  Object.entries(cantidades)
    .filter(([, cantidad]) => cantidad > 0)
    .map(([menu_item_id, cantidad]) => ({
      menu_item_id: Number(menu_item_id),
      cantidad,
      observaciones: observacionesPorItem[Number(menu_item_id)]?.trim() || undefined,
    })),
)

async function enviarPedidoMesero() {
  if (!mesaPedido.value || itemsSeleccionados.value.length === 0) return
  enviandoPedido.value = true
  try {
    await crearPedido(mesaPedido.value.id, itemsSeleccionados.value)
    ElMessage.success(`Pedido tomado para mesa ${mesaPedido.value.numero}`)
    dialogoPedidoAbierto.value = false
    await cargar()
  } catch {
    ElMessage.error('No se pudo tomar el pedido')
  } finally {
    enviandoPedido.value = false
  }
}

onMounted(() => {
  cargar()
  cargarMesas()
  intervalo = setInterval(() => {
    cargar()
    if (vista.value === 'mesas') cargarMesas()
  }, INTERVALO_POLLING_MS)
})
onUnmounted(() => clearInterval(intervalo))
</script>

<template>
  <div class="pagina">
    <AppTopNav subtitulo="Comanda" @salir="cerrarSesion">
      <template #nav>
        <button
          type="button"
          class="nav-item"
          :class="{ 'nav-item--activo': vista === 'pedidos' }"
          @click="vista = 'pedidos'"
        >
          <el-icon :size="16"><Tickets /></el-icon>
          <span>Pedidos</span>
        </button>
        <button
          type="button"
          class="nav-item"
          :class="{ 'nav-item--activo': vista === 'mesas' }"
          @click="vista = 'mesas'; cargarMesas()"
        >
          <el-icon :size="16"><Grid /></el-icon>
          <span>Mesas</span>
        </button>
      </template>
    </AppTopNav>

    <main class="contenido-principal">
      <div class="titulo-seccion">
        <h1>{{ vista === 'pedidos' ? 'Comanda' : 'Mesas' }}</h1>
        <p class="subtitulo">{{ auth.usuario?.nombre }}</p>
      </div>

      <div v-if="vista === 'pedidos'" class="contenido">
        <div v-if="mesasParaCerrar.length > 0" class="franja-cerrar">
          <span class="franja-etiqueta">Listas para cerrar</span>
          <div class="franja-botones">
            <button
              v-for="mesa in mesasParaCerrar"
              :key="mesa.mesa_id"
              type="button"
              class="chip-cerrar"
              @click="abrirDialogoFactura(mesa)"
            >
              Mesa {{ mesa.mesa_numero }}
            </button>
          </div>
        </div>

        <div v-if="cargando" class="grid-pedidos">
          <el-skeleton v-for="i in 3" :key="i" animated :rows="3" class="tarjeta-skeleton" />
        </div>

        <div v-else-if="pedidosActivos.length === 0" class="estado-vacio">
          <p class="estado-vacio-titulo">Sin pedidos por ahora</p>
          <p class="estado-vacio-texto">Los pedidos nuevos aparecen acá apenas entran.</p>
        </div>

        <div v-else class="grid-pedidos">
          <article
            v-for="pedido in pedidosActivos"
            :key="pedido.id"
            class="tarjeta-pedido"
            :class="`tarjeta-pedido--${pedido.estado}`"
          >
            <div class="cabecera-pedido">
              <span class="mesa">Mesa {{ pedido.mesa_numero }}</span>
              <span class="badge-estado" :class="`badge-estado--${pedido.estado}`">
                {{ etiquetaEstado[pedido.estado] }}
              </span>
            </div>
            <p v-if="pedido.nombre_invitado" class="nombre-invitado">
              Pidió: {{ pedido.nombre_invitado }} <span class="chip-invitado-pedido">invitado</span>
            </p>
            <ul class="items-pedido">
              <li v-for="item in pedido.items" :key="item.id">
                <span class="cantidad-item">{{ item.cantidad }}×</span> {{ item.menu_item_nombre }}
                <span v-if="item.observaciones" class="observaciones">{{ item.observaciones }}</span>
              </li>
            </ul>
            <div v-if="pedido.estado === 'pendiente'" class="acciones-pedido">
              <el-button
                plain
                size="large"
                :loading="procesando === pedido.id"
                class="boton-accion"
                @click="cancelar(pedido)"
              >
                Cancelar
              </el-button>
              <el-button
                type="primary"
                size="large"
                :loading="procesando === pedido.id"
                class="boton-accion"
                @click="confirmar(pedido)"
              >
                Confirmar
              </el-button>
            </div>
            <div v-else-if="pedido.estado === 'listo'" class="acciones-pedido">
              <el-button
                type="success"
                size="large"
                :loading="procesando === pedido.id"
                class="boton-accion"
                @click="entregar(pedido)"
              >
                Marcar entregado
              </el-button>
            </div>
          </article>
        </div>
      </div>

      <div v-else class="contenido">
        <div v-if="cargandoMesas" class="grid-mesas">
          <el-skeleton v-for="i in 3" :key="i" animated :rows="3" class="tarjeta-skeleton" />
        </div>
        <div v-else-if="mesas.length === 0" class="estado-vacio">
          <p class="estado-vacio-titulo">Sin mesas todavía</p>
          <p class="estado-vacio-texto">Las mesas las crea el admin del restaurante.</p>
        </div>
        <div v-else class="grid-mesas">
          <article v-for="mesa in mesas" :key="mesa.id" class="tarjeta-mesa">
            <div class="cabecera-pedido">
              <span class="mesa">Mesa {{ mesa.numero }}</span>
              <span class="badge-estado" :class="`badge-estado-mesa--${mesa.estado}`">
                {{ etiquetaEstadoMesa[mesa.estado] }}
              </span>
            </div>
            <p class="capacidad-mesa">{{ mesa.capacidad }} personas</p>
            <div class="acciones-pedido">
              <el-button
                v-if="mesa.estado === 'libre'"
                type="primary"
                size="large"
                class="boton-accion"
                :loading="procesandoMesa === mesa.id"
                @click="abrirDialogoOcupar(mesa)"
              >
                Ocupar
              </el-button>
              <template v-else-if="mesa.estado === 'ocupada'">
                <el-button
                  plain
                  size="large"
                  class="boton-accion"
                  :loading="procesandoMesa === mesa.id"
                  @click="liberar(mesa)"
                >
                  Liberar
                </el-button>
                <el-button
                  type="primary"
                  size="large"
                  class="boton-accion"
                  @click="abrirDialogoPedido(mesa)"
                >
                  Pedido
                </el-button>
              </template>
              <el-tag v-else type="info" round>Reservada</el-tag>
            </div>
          </article>
        </div>
      </div>
    </main>

    <el-dialog v-model="dialogoFacturaAbierto" title="Cerrar mesa" width="360px">
      <p v-if="mesaAFacturar" class="dialogo-mesa">Mesa {{ mesaAFacturar.mesa_numero }}</p>
      <div class="campo-propina">
        <span class="campo-label">¿Incluir propina?</span>
        <el-switch v-model="formFactura.incluirPropina" />
      </div>
      <div v-if="formFactura.incluirPropina" class="campo-propina">
        <span class="campo-label">Porcentaje</span>
        <el-input-number v-model="formFactura.porcentaje" :min="0" :max="100" />
      </div>
      <template #footer>
        <el-button @click="dialogoFacturaAbierto = false">Cancelar</el-button>
        <el-button type="primary" :loading="generandoFactura" @click="confirmarFactura">
          Generar factura
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="voucherAbierto" title="Factura" width="380px">
      <div v-if="voucher" class="voucher">
        <p class="voucher-mesa">Mesa {{ voucher.mesa_numero }}</p>
        <ul class="voucher-items">
          <li v-for="item in voucher.items" :key="item.id">
            <span>{{ item.cantidad }}× {{ item.menu_item_nombre }}</span>
            <span class="font-mono">${{ (Number(item.precio_unitario) * item.cantidad).toLocaleString('es-CO') }}</span>
          </li>
        </ul>
        <div class="voucher-linea">
          <span>Subtotal</span>
          <span class="font-mono">${{ Number(voucher.subtotal).toLocaleString('es-CO') }}</span>
        </div>
        <div v-if="voucher.incluye_propina" class="voucher-linea">
          <span>Propina</span>
          <span class="font-mono">${{ Number(voucher.propina).toLocaleString('es-CO') }}</span>
        </div>
        <div class="voucher-linea voucher-total">
          <span>Total</span>
          <span class="font-mono">${{ Number(voucher.total).toLocaleString('es-CO') }}</span>
        </div>
        <el-button disabled class="boton-factura-electronica">Factura electrónica</el-button>
      </div>
      <template #footer>
        <el-button @click="voucherAbierto = false">Cerrar</el-button>
        <el-button type="primary" @click="imprimir">Imprimir</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="dialogoOcuparAbierto" title="Ocupar mesa" width="360px">
      <p v-if="mesaAOcupar" class="dialogo-mesa">Mesa {{ mesaAOcupar.numero }}</p>
      <el-input
        v-model="nombreOcupar"
        placeholder="Nombre (opcional)"
        size="large"
        maxlength="80"
      />
      <template #footer>
        <el-button @click="dialogoOcuparAbierto = false">Cancelar</el-button>
        <el-button type="primary" :loading="procesandoMesa === mesaAOcupar?.id" @click="confirmarOcupar">
          Ocupar
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="dialogoPedidoAbierto" title="Tomar pedido" width="420px">
      <p v-if="mesaPedido" class="dialogo-mesa">Mesa {{ mesaPedido.numero }}</p>
      <el-empty v-if="menu.length === 0" description="Este restaurante no tiene menú cargado" />
      <ul v-else class="lista-menu-pedido">
        <li v-for="item in menu" :key="item.id" class="fila-menu-pedido">
          <div class="fila-menu-pedido-linea">
            <div>
              <p class="nombre-item-menu">{{ item.nombre }}</p>
              <p class="precio-item-menu font-mono">${{ Number(item.precio).toLocaleString('es-CO') }}</p>
            </div>
            <el-input-number v-model="cantidades[item.id]" :min="0" :max="20" size="small" />
          </div>
          <el-input
            v-if="(cantidades[item.id] ?? 0) > 0"
            v-model="observacionesPorItem[item.id]"
            placeholder="Observaciones (ej: sin lechuga)"
            size="small"
            class="input-observaciones-item"
            maxlength="200"
          />
        </li>
      </ul>
      <template #footer>
        <el-button @click="dialogoPedidoAbierto = false">Cancelar</el-button>
        <el-button
          type="primary"
          :loading="enviandoPedido"
          :disabled="itemsSeleccionados.length === 0"
          @click="enviarPedidoMesero"
        >
          Enviar pedido
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.pagina {
  min-height: 100dvh;
  background: var(--surface-sunken);
}

.contenido-principal {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--space-8) var(--space-6) var(--space-16);
}

.titulo-seccion {
  margin-bottom: var(--space-6);
}

.titulo-seccion h1 {
  font-size: 1.75rem;
  margin-bottom: var(--space-1);
}

.subtitulo {
  color: var(--text-tertiary);
  font-size: 0.875rem;
}

.contenido {
  width: 100%;
}

.franja-cerrar {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  flex-wrap: wrap;
  margin-bottom: var(--gutter);
  padding: var(--space-4) var(--space-5);
  background: var(--color-secondary-soft);
  border-radius: var(--radius-md);
}

.franja-etiqueta {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--color-secondary-hover);
}

.franja-botones {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.chip-cerrar {
  border: 1px solid var(--color-secondary);
  background: var(--surface-raised);
  color: var(--color-secondary);
  font-weight: 600;
  font-size: 0.85rem;
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-full);
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-standard);
}

.chip-cerrar:hover {
  background: var(--color-secondary-soft);
}

.grid-pedidos {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--space-4);
}

.tarjeta-skeleton {
  background: var(--surface-raised);
  border-radius: var(--radius-md);
  padding: var(--space-5);
}

.estado-vacio {
  text-align: center;
  padding: var(--space-16) var(--space-6);
  background: var(--surface-raised);
  border-radius: var(--radius-md);
  border: 1px dashed var(--border-default);
}

.estado-vacio-titulo {
  font-weight: 600;
  margin-bottom: var(--space-1);
}

.estado-vacio-texto {
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.tarjeta-pedido {
  background: var(--surface-raised);
  border: 1px solid var(--border-subtle);
  border-left: 4px solid var(--color-warning);
  border-radius: var(--radius-md);
  padding: var(--space-5);
  box-shadow: var(--shadow-soft), var(--highlight-inset);
  transition: box-shadow var(--duration-base) var(--ease-standard);
}

.tarjeta-pedido:hover {
  box-shadow: var(--shadow-soft-hover), var(--highlight-inset);
}

.tarjeta-pedido--confirmado,
.tarjeta-pedido--preparando {
  border-left-color: var(--color-secondary);
}

.tarjeta-pedido--listo {
  border-left-color: var(--color-success);
}

.cabecera-pedido {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-4);
}

.mesa {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 1.1rem;
}

.badge-estado {
  font-size: 0.75rem;
  font-weight: 700;
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-full);
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

.badge-estado--pendiente {
  background: var(--color-warning-bg);
  color: var(--color-warning-text);
}

.badge-estado--confirmado,
.badge-estado--preparando {
  background: var(--color-secondary-soft);
  color: var(--color-secondary-hover);
}

.badge-estado--listo {
  background: var(--color-success-bg);
  color: var(--color-success-text);
}

.nombre-invitado {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: 0.8rem;
  color: var(--text-secondary);
  margin-bottom: var(--space-3);
}

.chip-invitado-pedido {
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  color: var(--color-info);
  background: var(--color-info-bg);
  padding: 1px var(--space-2);
  border-radius: var(--radius-full);
}

.items-pedido {
  list-style: none;
  padding: 0;
  margin: 0 0 var(--space-4);
  font-size: 1rem;
}

.items-pedido li {
  padding: var(--space-2) 0;
  border-bottom: 1px solid var(--border-subtle);
}

.items-pedido li:last-child {
  border-bottom: none;
}

.cantidad-item {
  font-weight: 700;
  font-family: var(--font-mono);
  color: var(--color-secondary);
}

.observaciones {
  display: block;
  color: var(--color-warning-text);
  font-size: 0.825rem;
}

.acciones-pedido {
  display: flex;
  gap: var(--space-3);
}

.boton-accion {
  flex: 1;
  font-weight: 600;
}

.dialogo-mesa {
  font-weight: 600;
  margin-bottom: var(--space-4);
}

.campo-propina {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-3) 0;
}

.campo-label {
  font-size: 0.9rem;
}

.voucher-mesa {
  font-weight: 600;
  margin-bottom: var(--space-4);
}

.voucher-items {
  list-style: none;
  padding: 0;
  margin: 0 0 var(--space-3);
}

.voucher-items li {
  display: flex;
  justify-content: space-between;
  padding: var(--space-2) 0;
  font-size: 0.9rem;
}

.voucher-linea {
  display: flex;
  justify-content: space-between;
  padding: var(--space-2) 0;
  border-top: 1px solid var(--border-subtle);
}

.voucher-total {
  font-weight: 700;
  font-size: 1.05rem;
}

.boton-factura-electronica {
  width: 100%;
  margin-top: var(--space-4);
}

.grid-mesas {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: var(--space-4);
}

.tarjeta-mesa {
  background: var(--surface-raised);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: var(--space-5);
  box-shadow: var(--shadow-soft), var(--highlight-inset);
}

.capacidad-mesa {
  color: var(--text-secondary);
  font-size: 0.9rem;
  margin-bottom: var(--space-4);
}

.badge-estado-mesa--libre {
  background: var(--color-success-bg);
  color: var(--color-success-text);
}

.badge-estado-mesa--ocupada {
  background: var(--color-secondary-soft);
  color: var(--color-secondary-hover);
}

.badge-estado-mesa--reservada {
  background: var(--color-warning-bg);
  color: var(--color-warning-text);
}

.lista-menu-pedido {
  list-style: none;
  padding: 0;
  margin: var(--space-2) 0 0;
  max-height: 360px;
  overflow-y: auto;
}

.fila-menu-pedido {
  padding: var(--space-3) 0;
  border-bottom: 1px solid var(--border-subtle);
}

.fila-menu-pedido:last-child {
  border-bottom: none;
}

.fila-menu-pedido-linea {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
}

.input-observaciones-item {
  margin-top: var(--space-2);
}

.nombre-item-menu {
  font-weight: 600;
  font-size: 0.9rem;
}

.precio-item-menu {
  color: var(--text-secondary);
  font-size: 0.8rem;
}
</style>
