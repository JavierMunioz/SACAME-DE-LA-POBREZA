<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { canjearQr, ocuparMesa, unirseAMesa, type MesaQrInfo, type SesionMesa } from '../api/mesas'
import { crearPedido } from '../api/pedidos'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const info = ref<MesaQrInfo | null>(null)
const cargando = ref(true)
const errorToken = ref(false)
const enviandoPedido = ref(false)

const sesion = ref<SesionMesa | null>(null)
const reclamando = ref(false)
const nombreInput = ref('')
const codigoInput = ref('')
const errorReclamo = ref('')

// carrito: menu_item_id -> cantidad
const carrito = reactive<Record<number, number>>({})
const observaciones = reactive<Record<number, string>>({})

function claveSesion(mesaId: number) {
  return `sesion-mesa-${mesaId}`
}

function leerSesionGuardada(mesaId: number): SesionMesa | null {
  const raw = localStorage.getItem(claveSesion(mesaId))
  if (!raw) return null
  try {
    return JSON.parse(raw) as SesionMesa
  } catch {
    return null
  }
}

function guardarSesion(s: SesionMesa) {
  localStorage.setItem(claveSesion(s.mesa_id), JSON.stringify(s))
}

function borrarSesion(mesaId: number) {
  localStorage.removeItem(claveSesion(mesaId))
}

async function cargar() {
  if (auth.token && !auth.usuario) {
    try {
      await auth.cargarUsuario()
    } catch {
      auth.logout()
    }
  }

  const token = route.query.token as string | undefined
  if (!token) {
    errorToken.value = true
    cargando.value = false
    return
  }
  try {
    info.value = await canjearQr(token)
    const guardada = leerSesionGuardada(info.value.mesa_id)
    // Si la mesa no tiene ninguna sesión activa pero teníamos una guardada,
    // es de una visita anterior ya cerrada — no sirve, se descarta.
    sesion.value = info.value.requiere_codigo || guardada ? guardada : null
    if (!info.value.requiere_codigo && guardada) borrarSesion(info.value.mesa_id)
  } catch {
    errorToken.value = true
  } finally {
    cargando.value = false
  }
}

async function reclamarComoInvitado() {
  if (!info.value) return
  if (!nombreInput.value.trim()) {
    errorReclamo.value = 'Necesitamos tu nombre para abrir la mesa'
    return
  }
  await reclamar(() =>
    ocuparMesa(info.value!.mesa_id, route.query.token as string, {
      nombreInvitado: nombreInput.value,
    }),
  )
}

async function reclamarComoClienteLogueado() {
  if (!info.value) return
  await reclamar(() => ocuparMesa(info.value!.mesa_id, route.query.token as string, {}))
}

async function confirmarLlegada() {
  if (!info.value?.reserva_propia) return
  await reclamar(() =>
    ocuparMesa(info.value!.mesa_id, route.query.token as string, {
      reservaId: info.value!.reserva_propia!.id,
    }),
  )
}

async function unirseConCodigo() {
  if (!info.value) return
  if (codigoInput.value.trim().length !== 4) {
    errorReclamo.value = 'El código tiene 4 dígitos'
    return
  }
  await reclamar(() =>
    unirseAMesa(info.value!.mesa_id, route.query.token as string, codigoInput.value.trim()),
  )
}

async function reclamar(accion: () => Promise<SesionMesa>) {
  errorReclamo.value = ''
  reclamando.value = true
  try {
    const s = await accion()
    sesion.value = s
    guardarSesion(s)
  } catch {
    errorReclamo.value = 'No se pudo completar la acción. Puede que alguien se te haya adelantado — recargá la página.'
  } finally {
    reclamando.value = false
  }
}

function sumar(menuItemId: number) {
  carrito[menuItemId] = (carrito[menuItemId] ?? 0) + 1
}

function restar(menuItemId: number) {
  if (!carrito[menuItemId]) return
  carrito[menuItemId] -= 1
  if (carrito[menuItemId] <= 0) delete carrito[menuItemId]
}

const totalItems = computed(() => Object.values(carrito).reduce((a, b) => a + b, 0))

const totalPrecio = computed(() => {
  if (!info.value) return 0
  return Object.entries(carrito).reduce((suma, [menuItemId, cantidad]) => {
    const item = info.value!.menu.find((m) => m.id === Number(menuItemId))
    return suma + (item ? Number(item.precio) * cantidad : 0)
  }, 0)
})

async function enviarPedido() {
  if (!info.value || !sesion.value) return
  enviandoPedido.value = true
  try {
    const items = Object.entries(carrito).map(([menuItemId, cantidad]) => ({
      menu_item_id: Number(menuItemId),
      cantidad,
      observaciones: observaciones[Number(menuItemId)] || undefined,
    }))
    await crearPedido(info.value.mesa_id, items, sesion.value.token)
    ElMessage.success('Pedido enviado a la cocina')
    Object.keys(carrito).forEach((k) => delete carrito[Number(k)])
    router.push('/cliente')
  } catch (e: unknown) {
    const status = (e as { response?: { status?: number } })?.response?.status
    if (status === 401 && info.value) {
      borrarSesion(info.value.mesa_id)
      sesion.value = null
      ElMessage.error('Tu sesión de mesa venció. Volvé a abrir o unirte a la mesa.')
    } else {
      ElMessage.error('No se pudo enviar el pedido')
    }
  } finally {
    enviandoPedido.value = false
  }
}

onMounted(cargar)
</script>

<template>
  <div class="pagina">
    <div v-if="cargando" class="contenido-centrado">
      <el-skeleton animated :rows="5" style="width: 100%; max-width: 480px" />
    </div>

    <div v-else-if="errorToken" class="contenido-centrado">
      <div class="estado-mensaje">
        <p class="estado-titulo">Código QR inválido</p>
        <p class="estado-texto">Pedile al mesero un código nuevo.</p>
      </div>
    </div>

    <template v-else-if="info">
      <header class="encabezado">
        <h1>{{ info.restaurante_nombre }}</h1>
        <p class="subtitulo">Mesa {{ info.numero }}</p>
      </header>

      <div class="contenido" :class="{ 'con-carrito': totalItems > 0 && sesion }">
        <template v-if="sesion">
          <div class="banner banner-exito">
            <span class="banner-icono">✓</span>
            <span>Pidiendo como <strong>{{ sesion.nombre }}</strong></span>
            <span class="chip-codigo">Código de tu mesa: <strong>{{ sesion.codigo_acceso }}</strong></span>
          </div>

          <section class="menu">
            <h2>Menú</h2>
            <div v-for="item in info.menu" :key="item.id" class="fila-menu">
              <div class="info-plato">
                <p class="nombre-plato">{{ item.nombre }}</p>
                <p v-if="item.descripcion" class="descripcion-plato">{{ item.descripcion }}</p>
                <p class="precio-plato">${{ Number(item.precio).toLocaleString('es-CO') }}</p>
              </div>
              <div class="controles-cantidad">
                <button
                  type="button"
                  class="boton-stepper"
                  :disabled="!carrito[item.id]"
                  @click="restar(item.id)"
                >
                  −
                </button>
                <span class="cantidad">{{ carrito[item.id] ?? 0 }}</span>
                <button type="button" class="boton-stepper boton-stepper-primario" @click="sumar(item.id)">
                  +
                </button>
              </div>
            </div>
          </section>
        </template>

        <div v-else-if="info.estado === 'ocupada'" class="contenido-centrado sin-padding-top">
          <div class="estado-mensaje">
            <p class="estado-titulo">Esta mesa está ocupada</p>
            <p class="estado-texto">Pedile el código de 4 dígitos a quien la abrió.</p>
            <el-input
              v-model="codigoInput"
              maxlength="4"
              placeholder="0000"
              size="large"
              class="input-reclamo"
            />
            <el-alert v-if="errorReclamo" :title="errorReclamo" type="error" :closable="false" class="alerta-reclamo" />
            <el-button type="primary" size="large" :loading="reclamando" class="boton-usar" @click="unirseConCodigo">
              Unirme a la mesa
            </el-button>
          </div>
        </div>

        <div v-else-if="info.reserva_propia" class="contenido-centrado sin-padding-top">
          <div class="estado-mensaje">
            <p class="estado-titulo">Hola {{ auth.usuario?.nombre ?? '' }}, tu reserva está confirmada</p>
            <p class="estado-texto">Confirmá tu llegada para abrir la mesa.</p>
            <el-alert v-if="errorReclamo" :title="errorReclamo" type="error" :closable="false" class="alerta-reclamo" />
            <el-button type="primary" size="large" :loading="reclamando" class="boton-usar" @click="confirmarLlegada">
              Confirmar llegada
            </el-button>
          </div>
        </div>

        <div v-else-if="info.estado === 'reservada'" class="contenido-centrado sin-padding-top">
          <div class="estado-mensaje">
            <p class="estado-titulo">Esta mesa está reservada</p>
            <p class="estado-texto">Buscá al mesero si creés que es un error.</p>
          </div>
        </div>

        <div v-else-if="auth.usuario" class="contenido-centrado sin-padding-top">
          <div class="estado-mensaje">
            <p class="estado-titulo">Esta mesa está libre</p>
            <p class="estado-texto">Podés usarla sin reserva previa.</p>
            <el-alert v-if="errorReclamo" :title="errorReclamo" type="error" :closable="false" class="alerta-reclamo" />
            <el-button type="primary" size="large" :loading="reclamando" class="boton-usar" @click="reclamarComoClienteLogueado">
              Usar esta mesa
            </el-button>
          </div>
        </div>

        <div v-else class="contenido-centrado sin-padding-top">
          <div class="estado-mensaje">
            <p class="estado-titulo">Esta mesa está libre</p>
            <p class="estado-texto">Dejanos tu nombre para abrir la mesa.</p>
            <el-input v-model="nombreInput" placeholder="Tu nombre" size="large" class="input-reclamo" />
            <el-alert v-if="errorReclamo" :title="errorReclamo" type="error" :closable="false" class="alerta-reclamo" />
            <el-button type="primary" size="large" :loading="reclamando" class="boton-usar" @click="reclamarComoInvitado">
              Usar esta mesa
            </el-button>
          </div>
        </div>
      </div>

      <div v-if="sesion && totalItems > 0" class="barra-carrito">
        <div class="barra-carrito-info">
          <span class="barra-carrito-items">{{ totalItems }} {{ totalItems === 1 ? 'ítem' : 'ítems' }}</span>
          <span class="barra-carrito-total">${{ totalPrecio.toLocaleString('es-CO') }}</span>
        </div>
        <el-button
          type="primary"
          size="large"
          :loading="enviandoPedido"
          class="boton-enviar"
          @click="enviarPedido"
        >
          Enviar pedido
        </el-button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.pagina {
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
}

.contenido-centrado {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-8) var(--space-6);
}

.sin-padding-top {
  padding-top: 0;
}

.estado-mensaje {
  text-align: center;
  max-width: 320px;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.estado-titulo {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 1.25rem;
}

.estado-texto {
  color: var(--text-secondary);
  font-size: 0.9rem;
  margin-bottom: var(--space-2);
}

.input-reclamo {
  text-align: center;
}

.alerta-reclamo {
  border-radius: var(--radius-sm);
  text-align: left;
}

.boton-usar {
  font-weight: 600;
}

.encabezado {
  padding: var(--space-5) var(--space-6);
  background: var(--surface-raised);
  border-bottom: 1px solid var(--border-subtle);
}

.encabezado h1 {
  font-size: 1.25rem;
}

.subtitulo {
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.contenido {
  max-width: 560px;
  margin: 0 auto;
  padding: var(--space-6);
  width: 100%;
  flex: 1;
}

.contenido.con-carrito {
  padding-bottom: calc(var(--space-6) + 88px);
}

.banner {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-5);
  border-radius: var(--radius-md);
  font-size: 0.9rem;
  font-weight: 500;
  margin-bottom: var(--space-6);
}

.banner-exito {
  background: var(--color-success-bg);
  color: var(--color-success-text);
}

.banner-icono {
  display: grid;
  place-items: center;
  width: 24px;
  height: 24px;
  border-radius: var(--radius-full);
  background: var(--color-success);
  color: white;
  font-size: 0.8rem;
  flex-shrink: 0;
}

.chip-codigo {
  margin-left: auto;
  font-size: 0.8rem;
  background: var(--surface-raised);
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-full);
  font-variant-numeric: tabular-nums;
}

.menu {
  margin-top: var(--space-2);
}

.menu h2 {
  margin-bottom: var(--space-4);
}

.fila-menu {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-4) 0;
}

.fila-menu + .fila-menu {
  border-top: 1px solid var(--border-subtle);
}

.nombre-plato {
  font-weight: 500;
}

.descripcion-plato {
  color: var(--text-tertiary);
  font-size: 0.825rem;
  margin-top: var(--space-1);
}

.precio-plato {
  color: var(--text-secondary);
  font-size: 0.875rem;
  margin-top: var(--space-1);
}

.controles-cantidad {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-shrink: 0;
}

.boton-stepper {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-full);
  border: 1px solid var(--border-default);
  background: var(--surface-raised);
  font-size: 1.1rem;
  line-height: 1;
  cursor: pointer;
  color: var(--text-primary);
  transition: all var(--duration-fast) var(--ease-standard);
}

.boton-stepper:disabled {
  opacity: 0.35;
  cursor: default;
}

.boton-stepper:not(:disabled):hover {
  border-color: var(--color-secondary);
}

.boton-stepper-primario {
  background: var(--color-secondary);
  border-color: var(--color-secondary);
  color: white;
}

.boton-stepper-primario:hover {
  background: var(--color-secondary-hover);
}

.cantidad {
  min-width: 1.25rem;
  text-align: center;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.barra-carrito {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: var(--surface-raised);
  border-top: 1px solid var(--border-subtle);
  box-shadow: var(--shadow-lg);
  padding: var(--space-4) var(--space-6);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  z-index: 20;
  padding-bottom: max(var(--space-4), env(safe-area-inset-bottom));
}

.barra-carrito-info {
  display: flex;
  flex-direction: column;
}

.barra-carrito-items {
  font-size: 0.75rem;
  color: var(--text-tertiary);
}

.barra-carrito-total {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 1.15rem;
}

.boton-enviar {
  font-weight: 600;
  padding-inline: var(--space-8);
}
</style>
