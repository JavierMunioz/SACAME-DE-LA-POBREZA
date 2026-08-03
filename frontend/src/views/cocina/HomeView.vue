<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Connection, KnifeFork, Loading, SwitchButton, Warning } from '@element-plus/icons-vue'
import { listarPedidos, marcarListo, marcarPreparando, type Pedido } from '../../api/pedidos'
import { useAuthStore } from '../../stores/auth'
import logoWordmark from '../../assets/brand/logo-wordmark.png'

// Mismo enfoque que la comanda del mesero: polling simple, sin
// WebSockets todavía (ver Brain.md).
const INTERVALO_POLLING_MS = 5000
// El reloj visible y el "tiempo en espera" se refrescan cada segundo: no
// dependen de la red, solo recalculan contra la hora actual.
const INTERVALO_RELOJ_MS = 1000

const pedidos = ref<Pedido[]>([])
const cargando = ref(true)
const procesando = ref<number | null>(null)
const ahora = ref(Date.now())
let intervaloPolling: ReturnType<typeof setInterval> | undefined
let intervaloReloj: ReturnType<typeof setInterval> | undefined

const router = useRouter()
const auth = useAuthStore()

async function cargar() {
  // Sin filtro de estado: el backend ya sabe que cocina ve por defecto
  // confirmado+preparando+listo, en orden FIFO por hora de confirmación.
  pedidos.value = await listarPedidos()
  cargando.value = false
}

const horaActual = computed(() =>
  new Date(ahora.value).toLocaleTimeString('es-CO', { hour12: false }),
)

function minutosEnEspera(pedido: Pedido): number {
  if (!pedido.confirmado_at) return 0
  return Math.max(0, Math.floor((ahora.value - new Date(pedido.confirmado_at).getTime()) / 60000))
}

function urgencia(pedido: Pedido): 'normal' | 'atencion' | 'urgente' {
  if (pedido.estado === 'listo') return 'normal'
  const min = minutosEnEspera(pedido)
  if (min >= 20) return 'urgente'
  if (min >= 10) return 'atencion'
  return 'normal'
}

const etiquetaCanal: Record<string, string> = {
  domicilio_interno: 'Domicilio',
  rappi: 'Rappi',
  didi: 'Didi',
}

const ordenesAtrasadas = computed(
  () => pedidos.value.filter((p) => p.estado !== 'listo' && minutosEnEspera(p) >= 20).length,
)
const enPreparacion = computed(() => pedidos.value.filter((p) => p.estado === 'preparando').length)
const listasParaServir = computed(() => pedidos.value.filter((p) => p.estado === 'listo').length)

async function empezarPreparacion(pedido: Pedido) {
  procesando.value = pedido.id
  try {
    await marcarPreparando(pedido.id)
    await cargar()
  } catch {
    ElMessage.error('No se pudo actualizar el pedido')
  } finally {
    procesando.value = null
  }
}

async function marcarComoListo(pedido: Pedido) {
  procesando.value = pedido.id
  try {
    await marcarListo(pedido.id)
    ElMessage.success(
      pedido.mesa_numero !== null ? `Mesa ${pedido.mesa_numero} lista para servir` : 'Domicilio listo para salir',
    )
    await cargar()
  } catch {
    ElMessage.error('No se pudo actualizar el pedido')
  } finally {
    procesando.value = null
  }
}

// Mismo patrón táctil que las mesas del mesero: acá cada estado tiene
// una única acción posible (nada que elegir), así que toda la tarjeta
// es el botón — no hace falta menú intermedio ni botón chico aparte.
function onClickComanda(pedido: Pedido) {
  if (procesando.value !== null) return
  if (pedido.estado === 'confirmado') empezarPreparacion(pedido)
  else if (pedido.estado === 'preparando') marcarComoListo(pedido)
}

function cerrarSesion() {
  auth.logout()
  router.push('/login')
}

onMounted(() => {
  cargar()
  intervaloPolling = setInterval(cargar, INTERVALO_POLLING_MS)
  intervaloReloj = setInterval(() => {
    ahora.value = Date.now()
  }, INTERVALO_RELOJ_MS)
})
onUnmounted(() => {
  clearInterval(intervaloPolling)
  clearInterval(intervaloReloj)
})
</script>

<template>
  <div class="pagina">
    <header class="encabezado">
      <div class="encabezado-izq">
        <div class="marca-icono">
          <el-icon :size="18"><KnifeFork /></el-icon>
        </div>
        <h1 class="titulo-marca">
          <img :src="logoWordmark" alt="LagoPos" class="marca-texto-completo" />
          <span class="marca-acento">Cocina</span>
        </h1>
        <div class="separador" />
        <div class="reloj">
          <span class="font-mono">{{ horaActual }}</span>
        </div>
      </div>
      <div class="encabezado-der">
        <span class="indicador-activo">
          <span class="punto-verde" />
          <span class="indicador-texto">Sistema Operativo</span>
        </span>
        <button type="button" class="boton-icono" @click="cerrarSesion">
          <el-icon :size="18"><SwitchButton /></el-icon>
        </button>
      </div>
    </header>

    <main class="contenido">
      <div v-if="cargando" class="grid-comandas">
        <el-skeleton v-for="i in 3" :key="i" animated :rows="4" class="tarjeta-skeleton" />
      </div>

      <div v-else-if="pedidos.length === 0" class="estado-vacio">
        <p class="estado-vacio-titulo">Sin pedidos en cocina</p>
        <p class="estado-vacio-texto">Los pedidos confirmados por el mesero aparecen acá.</p>
      </div>

      <div v-else class="grid-comandas">
        <article
          v-for="(pedido, i) in pedidos"
          :key="pedido.id"
          class="tarjeta-comanda"
          :class="[
            `tarjeta-comanda--${urgencia(pedido)}`,
            { 'tarjeta-comanda--tocable': pedido.estado !== 'listo', 'tarjeta-comanda--procesando': procesando === pedido.id },
          ]"
          @click="onClickComanda(pedido)"
        >
          <div class="cabecera-comanda">
            <div>
              <h2 class="orden">Orden #{{ pedido.id }}</h2>
              <p class="mesa">
                {{ pedido.mesa_numero !== null ? `Mesa ${pedido.mesa_numero}` : 'Domicilio' }}
                <span v-if="pedido.canal !== 'mesa'" class="badge-canal-cocina">
                  {{ etiquetaCanal[pedido.canal] }}
                </span>
              </p>
            </div>
            <div class="tiempo" :class="`tiempo--${urgencia(pedido)}`">
              <el-icon v-if="urgencia(pedido) === 'urgente'" :size="16"><Warning /></el-icon>
              <span class="font-mono">{{ minutosEnEspera(pedido) }}:00</span>
            </div>
          </div>
          <ul class="items-comanda">
            <li v-for="item in pedido.items" :key="item.id">
              <span class="cantidad-item">{{ item.cantidad }}×</span>
              <span class="nombre-item">{{ item.menu_item_nombre }}</span>
            </li>
          </ul>
          <div v-if="pedido.items.some((i) => i.observaciones)" class="observaciones-caja">
            <span class="observaciones-etiqueta">Observaciones</span>
            <p v-for="item in pedido.items.filter((i) => i.observaciones)" :key="item.id">
              "{{ item.observaciones }}"
            </p>
          </div>

          <div class="acciones-comanda">
            <div v-if="pedido.estado === 'confirmado'" class="pista-accion-comanda pista-accion-comanda--preparando">
              <el-icon v-if="procesando === pedido.id"><Loading /></el-icon>
              Tocá para pasar a preparando
            </div>
            <div v-else-if="pedido.estado === 'preparando'" class="pista-accion-comanda pista-accion-comanda--listo">
              <el-icon v-if="procesando === pedido.id"><Loading /></el-icon>
              Tocá para marcar listo
            </div>
            <div v-else class="aviso-listo">Esperando al mesero</div>
          </div>
        </article>
      </div>
    </main>

    <footer class="pie">
      <div class="pie-contadores">
        <span class="pie-item">
          <span class="punto punto-rojo" /> {{ ordenesAtrasadas }} Orden{{ ordenesAtrasadas === 1 ? '' : 'es' }} Atrasada{{ ordenesAtrasadas === 1 ? '' : 's' }}
        </span>
        <span class="pie-item">
          <span class="punto punto-naranja" /> {{ enPreparacion }} En Preparación
        </span>
        <span class="pie-item">
          <span class="punto punto-verde-pie" /> {{ listasParaServir }} Listas para servir
        </span>
      </div>
      <div class="pie-item">
        <el-icon :size="14"><Connection /></el-icon>
        Conectado a Servidor Central
      </div>
    </footer>
  </div>
</template>

<style scoped>
.pagina {
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
}

.encabezado {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  min-height: 64px;
  background: var(--surface-raised);
  border-bottom: 1px solid var(--border-subtle);
  box-shadow: var(--shadow-sm);
  flex-shrink: 0;
}

@media (min-width: 640px) {
  .encabezado {
    padding: 0 var(--gutter);
  }
}

.encabezado-izq {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-width: 0;
}

@media (min-width: 640px) {
  .encabezado-izq {
    gap: var(--space-4);
  }
}

.titulo-marca {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.marca-texto-completo {
  height: 17px;
  width: auto;
  display: none;
}

@media (min-width: 640px) {
  .marca-texto-completo {
    display: block;
  }
}

.marca-icono {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  background: var(--color-primary);
  color: white;
}

.encabezado h1 {
  font-size: 1.25rem;
  letter-spacing: -0.02em;
}

.marca-acento {
  color: var(--color-secondary);
  font-weight: 700;
}

.separador {
  width: 1px;
  height: 24px;
  background: var(--border-subtle);
  flex-shrink: 0;
  display: none;
}

@media (min-width: 640px) {
  .separador {
    display: block;
  }
}

.reloj {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background: var(--surface-muted);
  border-radius: var(--radius-sm);
  font-weight: 700;
  flex-shrink: 0;
}

.encabezado-der {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-shrink: 0;
}

@media (min-width: 640px) {
  .encabezado-der {
    gap: var(--space-4);
  }
}

.indicador-activo {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: 0.875rem;
  font-weight: 500;
}

.indicador-texto {
  display: none;
}

@media (min-width: 640px) {
  .indicador-texto {
    display: inline;
  }
}

.punto-verde {
  width: 8px;
  height: 8px;
  border-radius: var(--radius-full);
  background: var(--color-success);
}

.boton-icono {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  border-radius: var(--radius-full);
  border: none;
  background: none;
  color: var(--text-secondary);
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-standard);
}

.boton-icono:hover {
  background: var(--surface-muted);
}

.contenido {
  flex: 1;
  overflow-y: auto;
  padding: var(--gutter);
}

.grid-comandas {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--space-5);
}

@media (min-width: 480px) {
  .grid-comandas {
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  }
}

.tarjeta-skeleton {
  background: var(--surface-raised);
  border-radius: var(--radius-md);
  padding: var(--space-6);
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

/* Tarjetas grandes, pensadas para pantalla táctil vista desde lejos. */
.tarjeta-comanda {
  display: flex;
  flex-direction: column;
  background: var(--surface-raised);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-soft), var(--highlight-inset);
  transition: box-shadow var(--duration-base) var(--ease-standard);
}

.tarjeta-comanda--tocable {
  cursor: pointer;
}

.tarjeta-comanda--procesando {
  opacity: 0.7;
  pointer-events: none;
}

.tarjeta-comanda:hover {
  box-shadow: var(--shadow-soft-hover), var(--highlight-inset);
}

.tarjeta-comanda--urgente {
  border: 2px solid var(--color-danger);
  background: var(--color-danger-bg);
}

.cabecera-comanda {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-4);
  border-bottom: 1px solid var(--border-subtle);
  background: var(--surface-muted);
}

.tarjeta-comanda--urgente .cabecera-comanda {
  background: transparent;
  border-bottom-color: rgba(186, 26, 26, 0.2);
}

.orden {
  font-size: 1.1rem;
}

.mesa {
  color: var(--text-secondary);
  font-size: 0.875rem;
  font-weight: 500;
}

.badge-canal-cocina {
  font-size: 0.65rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.02em;
  color: var(--color-secondary);
  background: var(--color-secondary-soft);
  padding: 1px var(--space-2);
  border-radius: var(--radius-full);
  margin-left: var(--space-2);
}

.tiempo {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-size: 0.9rem;
  font-weight: 700;
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-sm);
  background: var(--surface-muted);
  color: var(--text-primary);
}

.tiempo--atencion {
  background: var(--color-warning-bg);
  color: var(--color-warning-text);
}

.tiempo--urgente {
  background: var(--color-danger);
  color: white;
  animation: pulso 1.6s ease-in-out infinite;
}

@keyframes pulso {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

.items-comanda {
  list-style: none;
  padding: var(--space-4);
  margin: 0;
  flex: 1;
}

.items-comanda li {
  display: flex;
  gap: var(--space-2);
  font-size: 1.15rem;
  font-weight: 600;
  padding: var(--space-2) 0;
}

.cantidad-item {
  color: var(--text-tertiary);
}

.observaciones-caja {
  margin: 0 var(--space-4) var(--space-4);
  padding: var(--space-3);
  background: var(--surface-muted);
  border-radius: var(--radius-sm);
}

.tarjeta-comanda--urgente .observaciones-caja {
  background: rgba(255, 255, 255, 0.5);
}

.observaciones-etiqueta {
  display: block;
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-tertiary);
  margin-bottom: var(--space-1);
}

.observaciones-caja p {
  font-style: italic;
  font-size: 0.9rem;
}

.acciones-comanda {
  padding: var(--space-4);
  background: var(--surface-muted);
}

.tarjeta-comanda--urgente .acciones-comanda {
  background: transparent;
}

.pista-accion-comanda {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  width: 100%;
  height: 52px;
  font-size: 1rem;
  font-weight: 700;
  border-radius: var(--radius-sm);
  color: white;
}

.pista-accion-comanda--preparando {
  background: var(--color-warning);
}

.pista-accion-comanda--listo {
  background: var(--color-success);
}

.aviso-listo {
  text-align: center;
  padding: var(--space-3);
  font-weight: 600;
  color: var(--color-success-text);
  background: var(--color-success-bg);
  border-radius: var(--radius-sm);
}

.pie {
  min-height: 48px;
  flex-shrink: 0;
  background: var(--color-primary);
  color: white;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  font-size: 0.8125rem;
}

@media (min-width: 640px) {
  .pie {
    padding: 0 var(--gutter);
    font-size: 0.875rem;
  }
}

.pie-contadores {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
}

@media (min-width: 640px) {
  .pie-contadores {
    gap: var(--space-6);
  }
}

.pie-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.punto {
  width: 8px;
  height: 8px;
  border-radius: var(--radius-full);
}

.punto-rojo {
  background: #ef4444;
}

.punto-naranja {
  background: var(--color-warning);
}

.punto-verde-pie {
  background: var(--color-success);
}
</style>
