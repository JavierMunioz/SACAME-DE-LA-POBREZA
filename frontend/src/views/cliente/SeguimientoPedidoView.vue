<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { CircleCheck, Van } from '@element-plus/icons-vue'
import { obtenerPedido, type Pedido } from '../../api/pedidos'
import { obtenerRestaurante } from '../../api/restaurantes'

// Mismo enfoque de polling que el resto de la app (ver Brain.md): sin
// WebSockets todavía, 5s es suficientemente fresco para que el cliente
// vea avanzar su pedido sin sentirlo trabado.
const INTERVALO_POLLING_MS = 5000

const route = useRoute()
const router = useRouter()
const pedidoId = Number(route.params.id)

const pedido = ref<Pedido | null>(null)
const cargando = ref(true)
const restauranteCoords = ref<{ lat: number; lng: number } | null>(null)
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

const haceCuanto = computed(() => {
  if (!pedido.value?.repartidor_actualizado_at) return null
  const segundos = Math.max(
    0,
    Math.floor((Date.now() - new Date(pedido.value.repartidor_actualizado_at).getTime()) / 1000),
  )
  if (segundos < 60) return `hace ${segundos}s`
  return `hace ${Math.floor(segundos / 60)} min`
})

// --- Mapa en vivo del repartidor ---
// Leaflet + OpenStreetMap (sin API key, a diferencia de Google Maps) —
// el marcador del repartidor se saca y se vuelve a poner en cada
// actualización de ubicación (no solo se mueve): así el punto "parpadea"
// visualmente cada vez que llega una posición nueva, mismo pedido del
// usuario ("pintamos y despintamos el marcador").
const mapaEl = ref<HTMLElement | null>(null)
let mapa: L.Map | null = null
let marcadorRepartidor: L.Marker | null = null
let marcadorRestaurante: L.Marker | null = null

function iconoPulso(claseColor: string) {
  return L.divIcon({
    className: 'marcador-vacio',
    html: `<span class="marcador-pulso ${claseColor}"><span class="marcador-pulso-anillo"></span><span class="marcador-pulso-punto"></span></span>`,
    iconSize: [22, 22],
    iconAnchor: [11, 11],
  })
}

function inicializarMapa() {
  if (mapa || !mapaEl.value) return
  mapa = L.map(mapaEl.value, { zoomControl: false, attributionControl: false })
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
  }).addTo(mapa)
  L.control.attribution({ prefix: false }).addAttribution('© OpenStreetMap').addTo(mapa)
  actualizarMapa()
}

function actualizarMapa() {
  if (!mapa) return
  const lat = pedido.value?.repartidor_lat
  const lng = pedido.value?.repartidor_lng
  const puntos: [number, number][] = []

  if (restauranteCoords.value && !marcadorRestaurante) {
    marcadorRestaurante = L.marker(
      [restauranteCoords.value.lat, restauranteCoords.value.lng],
      { icon: iconoPulso('marcador-pulso--restaurante') },
    ).addTo(mapa)
  }
  if (restauranteCoords.value) puntos.push([restauranteCoords.value.lat, restauranteCoords.value.lng])

  if (lat != null && lng != null) {
    // Se saca el marcador viejo y se pone uno nuevo — no `setLatLng` —
    // para que el CSS de pulso se reinicie en cada refresco real.
    if (marcadorRepartidor) mapa.removeLayer(marcadorRepartidor)
    marcadorRepartidor = L.marker([lat, lng], { icon: iconoPulso('marcador-pulso--repartidor') }).addTo(mapa)
    puntos.push([lat, lng])
  }

  const primerPunto = puntos[0]
  if (puntos.length === 2) {
    mapa.fitBounds(puntos, { padding: [32, 32], maxZoom: 16 })
  } else if (primerPunto) {
    mapa.setView(primerPunto, 15)
  }
}

async function cargar() {
  try {
    pedido.value = await obtenerPedido(pedidoId)
    if (!restauranteCoords.value && pedido.value.restaurante_id) {
      const restaurante = await obtenerRestaurante(pedido.value.restaurante_id)
      if (restaurante.latitud != null && restaurante.longitud != null) {
        restauranteCoords.value = { lat: restaurante.latitud, lng: restaurante.longitud }
      }
    }
  } finally {
    cargando.value = false
  }
  // No alcanza con un watch sobre el estado: dispara apenas se asigna
  // `pedido.value` (mismo tick que el fetch de restaurante, todavía con
  // `cargando` en true), antes de que el `v-else-if="pedido"` del
  // template exista en el DOM — `mapaEl` sale null y el mapa nunca se
  // crea. Acá ya sabemos que `cargando` es false y el DOM está listo,
  // solo falta esperar el siguiente tick de render.
  if (pedido.value?.estado === 'en_camino') {
    await nextTick()
    inicializarMapa()
  }
}

function volver() {
  router.push('/cliente')
}

watch(
  [() => pedido.value?.repartidor_lat, () => pedido.value?.repartidor_lng, restauranteCoords],
  () => actualizarMapa(),
)

onMounted(() => {
  cargar()
  intervalo = setInterval(cargar, INTERVALO_POLLING_MS)
})
onUnmounted(() => {
  clearInterval(intervalo)
  mapa?.remove()
  mapa = null
})
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

          <div ref="mapaEl" class="mapa-repartidor" />
          <p v-if="!pedido.repartidor_lat" class="repartidor-actualizado">
            Esperando la primera señal de ubicación...
          </p>
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

.mapa-repartidor {
  width: 100%;
  height: 220px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  margin-bottom: var(--space-2);
  background: var(--surface-muted);
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

<style>
/* Sin scope a propósito: Leaflet arma los marcadores con HTML crudo
   (divIcon), no pasan por el compilador de Vue, así que el atributo
   data-v-* del scoping normal no les llega. */
.marcador-pulso {
  position: relative;
  display: block;
  width: 22px;
  height: 22px;
}

.marcador-pulso-punto {
  position: absolute;
  inset: 5px;
  border-radius: 50%;
  border: 2px solid white;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.35);
}

.marcador-pulso-anillo {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  opacity: 0.6;
  animation: marcador-pulso-anim 1.4s ease-out;
}

.marcador-pulso--repartidor .marcador-pulso-punto {
  background: #4f46e5;
}

.marcador-pulso--repartidor .marcador-pulso-anillo {
  background: #4f46e5;
}

.marcador-pulso--restaurante .marcador-pulso-punto {
  background: #18181b;
}

.marcador-pulso--restaurante .marcador-pulso-anillo {
  background: #18181b;
  animation: none;
}

@keyframes marcador-pulso-anim {
  0% {
    transform: scale(0.4);
    opacity: 0.7;
  }
  100% {
    transform: scale(2.2);
    opacity: 0;
  }
}
</style>
