<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { listarPedidos, type Pedido } from '../../api/pedidos'
import { useAuthStore } from '../../stores/auth'

// Mismo enfoque que la comanda del mesero: polling simple, sin
// WebSockets todavía (ver Brain.md).
const INTERVALO_POLLING_MS = 5000
// El reloj de "tiempo en espera" se refresca aparte y más seguido: no
// depende de la red, solo recalcula contra la hora actual.
const INTERVALO_RELOJ_MS = 15000

const pedidos = ref<Pedido[]>([])
const cargando = ref(true)
const ahora = ref(Date.now())
let intervaloPolling: ReturnType<typeof setInterval> | undefined
let intervaloReloj: ReturnType<typeof setInterval> | undefined

const router = useRouter()
const auth = useAuthStore()

async function cargar() {
  // El backend ya devuelve orden FIFO por hora de confirmación cuando se
  // filtra por estado=confirmado.
  pedidos.value = await listarPedidos('confirmado')
  cargando.value = false
}

function minutosEnEspera(pedido: Pedido): number {
  if (!pedido.confirmado_at) return 0
  return Math.max(0, Math.floor((ahora.value - new Date(pedido.confirmado_at).getTime()) / 60000))
}

function urgencia(pedido: Pedido): 'normal' | 'atencion' | 'urgente' {
  const min = minutosEnEspera(pedido)
  if (min >= 20) return 'urgente'
  if (min >= 10) return 'atencion'
  return 'normal'
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
      <div class="marca">
        <span class="marca-icono">S</span>
        <div>
          <h1>Cocina</h1>
          <p class="rol">{{ auth.usuario?.nombre }} · {{ pedidos.length }} en espera</p>
        </div>
      </div>
      <el-button @click="cerrarSesion">Salir</el-button>
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
          :class="`tarjeta-comanda--${urgencia(pedido)}`"
        >
          <div class="cabecera-comanda">
            <span class="orden">#{{ i + 1 }}</span>
            <span class="mesa">Mesa {{ pedido.mesa_numero }}</span>
            <span class="tiempo" :class="`tiempo--${urgencia(pedido)}`">
              {{ minutosEnEspera(pedido) }} min
            </span>
          </div>
          <ul class="items-comanda">
            <li v-for="item in pedido.items" :key="item.id">
              <div class="fila-item">
                <span class="cantidad-item">{{ item.cantidad }}×</span>
                <span class="nombre-item">{{ item.menu_item_nombre }}</span>
              </div>
              <p v-if="item.observaciones" class="observaciones">{{ item.observaciones }}</p>
            </li>
          </ul>
        </article>
      </div>
    </main>
  </div>
</template>

<style scoped>
.pagina {
  min-height: 100dvh;
}

.encabezado {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-4) var(--space-6);
  background: var(--surface-raised);
  border-bottom: 1px solid var(--border-subtle);
}

.marca {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.marca-icono {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  background: var(--color-primary-500);
  color: white;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 0.95rem;
}

.marca h1 {
  font-size: 1.1rem;
}

.rol {
  font-size: 0.8rem;
  color: var(--text-tertiary);
}

.contenido {
  max-width: 1400px;
  margin: 0 auto;
  padding: var(--space-6);
}

.grid-comandas {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: var(--space-5);
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
  background: var(--surface-raised);
  border: 1px solid var(--border-subtle);
  border-top: 4px solid var(--color-neutral-300);
  border-radius: var(--radius-md);
  padding: var(--space-6);
  box-shadow: var(--shadow-md);
}

.tarjeta-comanda--atencion {
  border-top-color: var(--color-warning);
}

.tarjeta-comanda--urgente {
  border-top-color: var(--color-danger);
}

.cabecera-comanda {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-5);
}

.orden {
  color: var(--text-tertiary);
  font-size: 0.9rem;
  font-weight: 600;
}

.mesa {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 1.35rem;
  flex: 1;
}

.tiempo {
  font-size: 0.85rem;
  font-weight: 700;
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-full);
  font-variant-numeric: tabular-nums;
  background: var(--color-neutral-100);
  color: var(--text-secondary);
}

.tiempo--atencion {
  background: var(--color-warning-bg);
  color: var(--color-warning);
}

.tiempo--urgente {
  background: var(--color-danger-bg);
  color: var(--color-danger);
}

.items-comanda {
  list-style: none;
  padding: 0;
  margin: 0;
}

.items-comanda li {
  padding: var(--space-3) 0;
}

.items-comanda li + li {
  border-top: 1px solid var(--border-subtle);
}

.fila-item {
  display: flex;
  gap: var(--space-2);
  font-size: 1.05rem;
}

.cantidad-item {
  font-weight: 700;
  color: var(--color-primary-600);
  min-width: 1.75rem;
}

.nombre-item {
  font-weight: 500;
}

.observaciones {
  margin-top: var(--space-1);
  margin-left: calc(1.75rem + var(--space-2));
  color: var(--color-warning);
  font-size: 0.9rem;
  font-weight: 500;
}
</style>
