<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { CircleCheck, LocationFilled, Van } from '@element-plus/icons-vue'
import { obtenerPedido, type Pedido } from '../../api/pedidos'

// Mismo enfoque de polling que el resto de la app (ver Brain.md): sin
// WebSockets todavía, 5s es suficientemente fresco para que el cliente
// vea avanzar su pedido sin sentirlo trabado.
const INTERVALO_POLLING_MS = 5000

const route = useRoute()
const router = useRouter()
const pedidoId = Number(route.params.id)

const pedido = ref<Pedido | null>(null)
const cargando = ref(true)
let intervalo: ReturnType<typeof setInterval> | undefined

const PASOS = [
  { estado: 'pendiente', etiqueta: 'Pedido recibido' },
  { estado: 'confirmado', etiqueta: 'Confirmado' },
  { estado: 'preparando', etiqueta: 'En preparación' },
  { estado: 'listo', etiqueta: 'Listo para salir' },
  { estado: 'en_camino', etiqueta: 'En camino' },
  { estado: 'entregado', etiqueta: 'Entregado' },
] as const

const pasoActual = computed(() => {
  if (!pedido.value) return -1
  return PASOS.findIndex((p) => p.estado === pedido.value?.estado)
})

const ubicacionRepartidorUrl = computed(() => {
  if (!pedido.value?.repartidor_lat || !pedido.value?.repartidor_lng) return null
  return `https://www.google.com/maps/search/?api=1&query=${pedido.value.repartidor_lat},${pedido.value.repartidor_lng}`
})

const haceCuanto = computed(() => {
  if (!pedido.value?.repartidor_actualizado_at) return null
  const segundos = Math.max(
    0,
    Math.floor((Date.now() - new Date(pedido.value.repartidor_actualizado_at).getTime()) / 1000),
  )
  if (segundos < 60) return `hace ${segundos}s`
  return `hace ${Math.floor(segundos / 60)} min`
})

async function cargar() {
  try {
    pedido.value = await obtenerPedido(pedidoId)
  } finally {
    cargando.value = false
  }
}

function volver() {
  router.push('/cliente')
}

onMounted(() => {
  cargar()
  intervalo = setInterval(cargar, INTERVALO_POLLING_MS)
})
onUnmounted(() => clearInterval(intervalo))
</script>

<template>
  <div class="pagina">
    <header class="encabezado-pagina">
      <button type="button" class="volver" @click="volver">← Volver</button>
    </header>

    <main class="contenido">
      <el-skeleton v-if="cargando" animated :rows="6" />

      <template v-else-if="pedido">
        <h1 class="titulo">Pedido #{{ pedido.id }}</h1>

        <div v-if="pedido.estado === 'cancelado'" class="aviso-cancelado">
          Este pedido fue cancelado.
        </div>

        <ol v-else class="pasos">
          <li
            v-for="(paso, i) in PASOS"
            :key="paso.estado"
            class="paso"
            :class="{ 'paso--hecho': i <= pasoActual, 'paso--actual': i === pasoActual }"
          >
            <span class="paso-punto">
              <el-icon v-if="i < pasoActual"><CircleCheck /></el-icon>
              <span v-else class="paso-punto-numero">{{ i + 1 }}</span>
            </span>
            <span class="paso-etiqueta">{{ paso.etiqueta }}</span>
          </li>
        </ol>

        <div
          v-if="pedido.estado === 'en_camino'"
          class="tarjeta-repartidor card-soft"
        >
          <div class="repartidor-cabecera">
            <el-icon :size="20"><Van /></el-icon>
            <div>
              <p class="repartidor-nombre">{{ pedido.repartidor_nombre ?? 'Tu repartidor' }} va en camino</p>
              <p v-if="haceCuanto" class="repartidor-actualizado">Última ubicación {{ haceCuanto }}</p>
            </div>
          </div>
          <a
            v-if="ubicacionRepartidorUrl"
            :href="ubicacionRepartidorUrl"
            target="_blank"
            rel="noopener"
            class="boton-ver-mapa"
          >
            <el-icon :size="16"><LocationFilled /></el-icon>
            Ver ubicación en el mapa
          </a>
          <p v-else class="repartidor-actualizado">Esperando la primera señal de ubicación...</p>
        </div>

        <div class="tarjeta-detalle card-soft">
          <p v-if="pedido.direccion_entrega" class="fila-detalle">
            <span class="label-mono">Entrega en</span>
            {{ pedido.direccion_entrega }}
          </p>
          <ul class="items-pedido">
            <li v-for="item in pedido.items" :key="item.id">
              <span class="cantidad-item">{{ item.cantidad }}×</span> {{ item.menu_item_nombre }}
            </li>
          </ul>
        </div>
      </template>
    </main>
  </div>
</template>

<style scoped>
.pagina {
  min-height: 100dvh;
}

.encabezado-pagina {
  padding: var(--space-4) var(--space-6);
  background: var(--surface-raised);
  border-bottom: 1px solid var(--border-subtle);
  position: sticky;
  top: 0;
  z-index: 10;
}

.volver {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 0.875rem;
  color: var(--text-secondary);
  font-weight: 500;
  padding: 0;
}

.volver:hover {
  color: var(--text-primary);
}

.contenido {
  max-width: 560px;
  margin: 0 auto;
  padding: var(--space-6) var(--space-4) var(--space-16);
}

.titulo {
  margin-bottom: var(--space-6);
}

.aviso-cancelado {
  padding: var(--space-4);
  background: var(--color-danger-bg);
  color: var(--color-danger-text);
  border-radius: var(--radius-md);
  font-weight: 500;
  margin-bottom: var(--space-6);
}

.pasos {
  list-style: none;
  padding: 0;
  margin: 0 0 var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.paso {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) 0;
  color: var(--text-tertiary);
}

.paso-punto {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border-radius: var(--radius-full);
  background: var(--surface-muted);
  color: var(--text-tertiary);
  flex-shrink: 0;
  font-size: 0.8rem;
  font-weight: 700;
}

.paso--hecho .paso-punto {
  background: var(--color-success-bg);
  color: var(--color-success-text);
}

.paso--hecho {
  color: var(--text-primary);
}

.paso--actual .paso-punto {
  background: var(--color-secondary);
  color: white;
}

.paso--actual {
  color: var(--text-primary);
  font-weight: 600;
}

.tarjeta-repartidor,
.tarjeta-detalle {
  padding: var(--space-5);
  margin-bottom: var(--space-4);
}

.repartidor-cabecera {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
}

.repartidor-nombre {
  font-weight: 600;
}

.repartidor-actualizado {
  color: var(--text-tertiary);
  font-size: 0.8rem;
}

.boton-ver-mapa {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-3);
  background: var(--color-secondary-soft);
  color: var(--color-secondary);
  border-radius: var(--radius-sm);
  font-weight: 600;
  font-size: 0.875rem;
  text-decoration: none;
}

.fila-detalle {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  margin-bottom: var(--space-3);
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--border-subtle);
}

.items-pedido {
  list-style: none;
  padding: 0;
  margin: 0;
  font-size: 0.9rem;
  color: var(--text-secondary);
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.cantidad-item {
  font-weight: 700;
  font-family: var(--font-mono);
  color: var(--color-secondary);
}
</style>
