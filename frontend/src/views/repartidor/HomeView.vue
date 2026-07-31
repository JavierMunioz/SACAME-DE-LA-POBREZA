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
        <article v-for="pedido in pedidos" :key="pedido.id" class="tarjeta-entrega">
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
            @click="abrirEnMapa(pedido)"
          >
            <el-icon :size="16"><LocationFilled /></el-icon>
            <span>{{ pedido.direccion_entrega ?? 'Sin dirección' }}</span>
          </button>
          <a v-if="pedido.telefono_entrega" :href="`tel:${pedido.telefono_entrega}`" class="fila-telefono">
            <el-icon :size="16"><Phone /></el-icon>
            <span>{{ pedido.telefono_entrega }}</span>
          </a>

          <ul class="items-entrega">
            <li v-for="item in pedido.items" :key="item.id">
              <span class="cantidad-item">{{ item.cantidad }}×</span>
              <span>{{ item.menu_item_nombre }}</span>
            </li>
          </ul>

          <el-button
            v-if="pedido.estado === 'listo'"
            type="primary"
            class="boton-accion"
            :loading="procesando === pedido.id"
            @click="empezarEntrega(pedido)"
          >
            <el-icon :size="16" style="margin-right: 6px"><Bell /></el-icon>
            Marcar en camino
          </el-button>
          <el-button
            v-else
            type="success"
            class="boton-accion"
            :loading="procesando === pedido.id"
            @click="completarEntrega(pedido)"
          >
            Marcar entregado
          </el-button>
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
  background: var(--surface-raised);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  box-shadow: var(--shadow-soft), var(--highlight-inset);
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

.boton-accion {
  width: 100%;
  height: 44px;
  font-weight: 600;
}
</style>
