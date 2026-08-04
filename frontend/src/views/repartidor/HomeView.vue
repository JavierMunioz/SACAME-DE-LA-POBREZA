<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Bell, LocationFilled, Phone } from '@element-plus/icons-vue'
import {
  actualizarUbicacionRepartidor,
  listarPedidos,
  marcarEnCamino,
  marcarEntregado,
  type Pedido,
} from '../../api/pedidos'
import { obtenerUbicacion } from '../../api/mesas'
import { useAuthStore } from '../../stores/auth'
import AppTopNav from '../../components/AppTopNav.vue'

// Mismo enfoque de polling simple que mesero/cocina (ver Brain.md: sin
// WebSockets todavía).
const INTERVALO_POLLING_MS = 5000
// Cada cuánto se manda la posición del repartidor mientras hay una
// entrega en camino — suficiente para que el cliente vea avance real sin
// drenar la batería a lo bestia.
const INTERVALO_UBICACION_MS = 15000

const pedidos = ref<Pedido[]>([])
const cargando = ref(true)
const procesando = ref<number | null>(null)
// Mismo patrón táctil que las mesas del mesero: "listo" tiene una sola
// acción posible (salir), dispara directo al tocar la tarjeta. "en
// camino" solo tiene "entregado" — consecuente de verdad, así que va
// detrás de un mini-menú en vez de dispararse con un toque accidental.
const menuEntregaAbierta = ref<number | null>(null)
let intervaloPolling: ReturnType<typeof setInterval> | undefined
let intervaloUbicacion: ReturnType<typeof setInterval> | undefined

const router = useRouter()
const auth = useAuthStore()

async function cargar() {
  pedidos.value = await listarPedidos()
  cargando.value = false
}

async function enviarUbicacionActual() {
  const enCamino = pedidos.value.filter((p) => p.estado === 'en_camino')
  if (enCamino.length === 0) return
  const ubicacion = await obtenerUbicacion()
  if (!ubicacion) return
  await Promise.all(
    enCamino.map((p) => actualizarUbicacionRepartidor(p.id, ubicacion.lat, ubicacion.lng).catch(() => {})),
  )
}

async function empezarEntrega(pedido: Pedido) {
  procesando.value = pedido.id
  try {
    await marcarEnCamino(pedido.id)
    ElMessage.success('Entrega iniciada, mandando tu ubicación')
    await enviarUbicacionActual()
    await cargar()
  } catch {
    ElMessage.error('No se pudo iniciar la entrega')
  } finally {
    procesando.value = null
  }
}

async function completarEntrega(pedido: Pedido) {
  menuEntregaAbierta.value = null
  procesando.value = pedido.id
  try {
    await marcarEntregado(pedido.id)
    ElMessage.success('Entrega completada')
    await cargar()
  } catch {
    ElMessage.error('No se pudo marcar como entregado')
  } finally {
    procesando.value = null
  }
}

function onClickEntrega(pedido: Pedido) {
  if (pedido.estado === 'listo') {
    empezarEntrega(pedido)
  } else if (pedido.estado === 'en_camino') {
    menuEntregaAbierta.value = menuEntregaAbierta.value === pedido.id ? null : pedido.id
  }
}

function abrirEnMapa(pedido: Pedido) {
  if (!pedido.direccion_entrega) return
  const query = encodeURIComponent(pedido.direccion_entrega)
  window.open(`https://www.google.com/maps/search/?api=1&query=${query}`, '_blank')
}

function cerrarSesion() {
  auth.logout()
  router.push('/login')
}

onMounted(() => {
  cargar()
  intervaloPolling = setInterval(cargar, INTERVALO_POLLING_MS)
  intervaloUbicacion = setInterval(enviarUbicacionActual, INTERVALO_UBICACION_MS)
})
onUnmounted(() => {
  clearInterval(intervaloPolling)
  clearInterval(intervaloUbicacion)
})
</script>

<template>
  <div class="pagina">
    <AppTopNav subtitulo="Repartidor" @salir="cerrarSesion" />

    <main class="contenido">
      <div class="titulo-seccion">
        <h1>Mis entregas</h1>
        <p class="subtitulo">Hola, {{ auth.usuario?.nombre }}</p>
      </div>

      <div v-if="cargando" class="grid-entregas">
        <el-skeleton v-for="i in 2" :key="i" animated :rows="4" class="tarjeta-skeleton" />
      </div>

      <div v-else-if="pedidos.length === 0" class="estado-vacio">
        <p class="estado-vacio-titulo">Sin entregas asignadas</p>
        <p class="estado-vacio-texto">Cuando el mesero te asigne un domicilio, aparece acá.</p>
      </div>

      <div v-else class="grid-entregas">
        <article
          v-for="pedido in pedidos"
          :key="pedido.id"
          class="tarjeta-entrega tarjeta-entrega--tocable"
          :class="{ 'tarjeta-entrega--procesando': procesando === pedido.id }"
          @click="onClickEntrega(pedido)"
        >
          <div class="cabecera-entrega">
            <h2>Pedido #{{ pedido.id }}</h2>
            <el-tag :type="pedido.estado === 'en_camino' ? 'warning' : 'info'" round>
              {{ pedido.estado === 'en_camino' ? 'En camino' : 'Listo para salir' }}
            </el-tag>
          </div>

          <button
            type="button"
            class="fila-direccion"
            :disabled="!pedido.direccion_entrega"
            @click.stop="abrirEnMapa(pedido)"
          >
            <el-icon :size="16"><LocationFilled /></el-icon>
            <span>{{ pedido.direccion_entrega ?? 'Sin dirección' }}</span>
          </button>
          <a
            v-if="pedido.telefono_entrega"
            :href="`tel:${pedido.telefono_entrega}`"
            class="fila-telefono"
            @click.stop
          >
            <el-icon :size="16"><Phone /></el-icon>
            <span>{{ pedido.telefono_entrega }}</span>
          </a>

          <ul class="items-entrega">
            <li v-for="item in pedido.items" :key="item.id">
              <span class="cantidad-item">{{ item.cantidad }}×</span>
              <span>{{ item.menu_item_nombre }}</span>
            </li>
          </ul>

          <p v-if="pedido.factura_total" class="cobro-entrega">
            Cobrar contra entrega
            <span class="font-mono">${{ Number(pedido.factura_total).toLocaleString('es-CO') }}</span>
          </p>

          <p v-if="pedido.estado === 'listo'" class="pista-accion-entrega">
            <el-icon :size="14"><Bell /></el-icon>
            Tocá para marcar en camino
          </p>
          <p v-else class="pista-accion-entrega">Tocá para confirmar entrega y cobro</p>

          <div
            v-if="menuEntregaAbierta === pedido.id"
            class="menu-acciones-entrega"
            @click.stop="menuEntregaAbierta = null"
          >
            <button
              type="button"
              class="opcion-menu-entrega"
              :disabled="procesando === pedido.id"
              @click.stop="completarEntrega(pedido)"
            >
              {{
                pedido.factura_total
                  ? `Entregado y cobrado ($${Number(pedido.factura_total).toLocaleString('es-CO')})`
                  : 'Marcar entregado'
              }}
            </button>
            <p class="pista-cerrar-menu-entrega">Tocá afuera para cancelar</p>
          </div>
        </article>
      </div>
    </main>
  </div>
</template>

<style scoped>
.pagina {
  min-height: 100dvh;
  background: var(--surface-sunken);
}

.contenido {
  max-width: 720px;
  margin: 0 auto;
  padding: var(--space-6) var(--space-4) var(--space-16);
}

.titulo-seccion {
  margin-bottom: var(--space-6);
}

.subtitulo {
  color: var(--text-tertiary);
  font-size: 0.875rem;
}

.grid-entregas {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
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

.tarjeta-entrega {
  position: relative;
  background: var(--surface-raised);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  box-shadow: var(--shadow-soft), var(--highlight-inset);
}

.tarjeta-entrega--tocable {
  cursor: pointer;
}

.tarjeta-entrega--procesando {
  opacity: 0.7;
  pointer-events: none;
}

.cabecera-entrega {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-2);
}

.fila-direccion,
.fila-telefono {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background: var(--surface-muted);
  border-radius: var(--radius-sm);
  border: none;
  color: var(--text-primary);
  font-size: 0.875rem;
  text-align: left;
  text-decoration: none;
  cursor: pointer;
  width: 100%;
  min-width: 0;
}

.fila-direccion span,
.fila-telefono span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.fila-direccion:disabled {
  cursor: default;
  opacity: 0.6;
}

.items-entrega {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.cantidad-item {
  color: var(--text-tertiary);
  margin-right: var(--space-2);
}

.cobro-entrega {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-2) var(--space-3);
  background: var(--color-warning-bg);
  color: var(--color-warning-text);
  border-radius: var(--radius-sm);
  font-size: 0.875rem;
  font-weight: 600;
}

.pista-accion-entrega {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: 0.8rem;
  color: var(--text-tertiary);
}

.menu-acciones-entrega {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-5);
  background: var(--surface-raised);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  z-index: 5;
}

.opcion-menu-entrega {
  display: block;
  width: 100%;
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  background: var(--color-success-bg);
  color: var(--color-success-text);
  font-size: 0.9rem;
  font-weight: 700;
  text-align: center;
  cursor: pointer;
}

.opcion-menu-entrega:hover {
  background: var(--color-success);
  color: white;
}

.pista-cerrar-menu-entrega {
  text-align: center;
  font-size: 0.75rem;
  color: var(--text-tertiary);
  margin-top: var(--space-1);
}
</style>
