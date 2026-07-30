<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { obtenerRestaurante, type RestauranteConMenu } from '../../api/restaurantes'
import {
  consultarDisponibilidad,
  crearReserva,
  type MesaDisponibilidad,
} from '../../api/reservas'
import { useAuthStore } from '../../stores/auth'
import { imagenComida } from '../../utils/imagenesComida'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const restauranteId = Number(route.params.id)

const restaurante = ref<RestauranteConMenu | null>(null)
const mesas = ref<MesaDisponibilidad[]>([])
const cargando = ref(true)
const buscando = ref(false)
const reservando = ref<number | null>(null)
const busquedaHecha = ref(false)

const hoy = new Date()
hoy.setMinutes(hoy.getMinutes() - hoy.getTimezoneOffset())
const form = reactive({
  fecha: hoy.toISOString().slice(0, 10),
  hora: '20:00',
  personas: 2,
})

const mesasFiltradas = computed(() =>
  mesas.value.filter((m) => m.capacidad >= form.personas),
)

async function cargar() {
  cargando.value = true
  restaurante.value = await obtenerRestaurante(restauranteId)
  cargando.value = false
}

async function buscarDisponibilidad() {
  buscando.value = true
  busquedaHecha.value = true
  try {
    const inicio = new Date(`${form.fecha}T${form.hora}:00`).toISOString()
    mesas.value = await consultarDisponibilidad(restauranteId, inicio)
  } finally {
    buscando.value = false
  }
}

// Ninguna reserva de último minuto: cocina/mesero necesitan margen real
// para prepararse (regla real del negocio, no un límite técnico).
const HORAS_MINIMAS_ANTICIPACION = 2

async function reservar(mesa: MesaDisponibilidad) {
  // Reservar necesita identidad (para saludar por nombre al escanear el
  // QR); pedir sin reserva no la necesita. Frenamos acá, no antes.
  if (!auth.token) {
    router.push(`/login?redirect=${encodeURIComponent(route.fullPath)}`)
    return
  }
  const inicioDate = new Date(`${form.fecha}T${form.hora}:00`)
  const limite = new Date(Date.now() + HORAS_MINIMAS_ANTICIPACION * 60 * 60 * 1000)
  if (inicioDate < limite) {
    ElMessage.error(`Las reservas deben hacerse con al menos ${HORAS_MINIMAS_ANTICIPACION} horas de anticipación`)
    return
  }
  reservando.value = mesa.mesa_id
  try {
    await crearReserva({ mesa_id: mesa.mesa_id, inicio: inicioDate.toISOString() })
    ElMessage.success(`Mesa ${mesa.numero} reservada. Llegá 15 min antes.`)
    await buscarDisponibilidad()
  } catch (e: unknown) {
    const status = (e as { response?: { status?: number } })?.response?.status
    if (status === 409) ElMessage.error('Esa mesa ya se reservó, elegí otra')
    else if (status === 422)
      ElMessage.error(`Las reservas deben hacerse con al menos ${HORAS_MINIMAS_ANTICIPACION} horas de anticipación`)
    else ElMessage.error('No se pudo reservar')
  } finally {
    reservando.value = null
  }
}

function volver() {
  router.push('/cliente')
}

function irAMenu() {
  document.getElementById('menu')?.scrollIntoView({ behavior: 'smooth' })
}

function irAReservar() {
  document.getElementById('reservar')?.scrollIntoView({ behavior: 'smooth' })
}

onMounted(async () => {
  if (auth.token && !auth.usuario) {
    try {
      await auth.cargarUsuario()
    } catch {
      auth.logout()
    }
  }
  cargar()
})
</script>

<template>
  <div class="pagina">
    <header class="encabezado-pagina">
      <button type="button" class="volver" @click="volver">← Volver a restaurantes</button>
    </header>

    <div v-if="cargando" class="contenido">
      <el-skeleton animated :rows="6" />
    </div>

    <main v-else-if="restaurante" class="contenido">
      <div class="hero-restaurante">
        <img
          :src="imagenComida(restauranteId, 1400, 420)"
          :alt="restaurante.nombre"
          class="hero-restaurante-imagen"
        />
        <div class="hero-restaurante-overlay">
          <h1>{{ restaurante.nombre }}</h1>
          <p v-if="restaurante.descripcion" class="descripcion">{{ restaurante.descripcion }}</p>
          <div class="hero-restaurante-acciones">
            <el-button type="primary" size="large" @click="irAReservar">Reservar mesa</el-button>
            <el-button size="large" class="boton-outline-claro" @click="irAMenu">Ver menú</el-button>
          </div>
        </div>
      </div>

      <div class="layout-detalle">
        <section id="menu" class="columna-menu">
          <h2>Menú</h2>
          <el-empty v-if="restaurante.menu.length === 0" description="Sin platos todavía" />
          <ul v-else class="lista-menu">
            <li v-for="item in restaurante.menu" :key="item.id">
              <img :src="imagenComida(item.id, 200, 200)" :alt="item.nombre" class="imagen-plato" />
              <div class="info-plato">
                <p class="nombre-plato">{{ item.nombre }}</p>
                <p v-if="item.descripcion" class="descripcion-plato">{{ item.descripcion }}</p>
                <span class="precio">${{ Number(item.precio).toLocaleString('es-CO') }}</span>
              </div>
            </li>
          </ul>
        </section>

        <aside id="reservar" class="columna-reserva">
          <div class="tarjeta-reserva card-soft">
            <h3>Reservar mesa</h3>
            <label class="campo-reserva">
              <span class="label-mono">Fecha</span>
              <el-date-picker
                v-model="form.fecha"
                type="date"
                value-format="YYYY-MM-DD"
                size="large"
                style="width: 100%"
              />
            </label>
            <label class="campo-reserva">
              <span class="label-mono">Hora</span>
              <el-time-select
                v-model="form.hora"
                start="11:00"
                end="23:00"
                step="00:30"
                size="large"
                style="width: 100%"
              />
            </label>
            <label class="campo-reserva">
              <span class="label-mono">Personas</span>
              <el-input-number v-model="form.personas" :min="1" :max="20" size="large" style="width: 100%" />
            </label>
            <el-button
              type="primary"
              size="large"
              class="boton-disponibilidad"
              :loading="buscando"
              @click="buscarDisponibilidad"
            >
              Ver disponibilidad
            </el-button>

            <el-empty
              v-if="busquedaHecha && !buscando && mesasFiltradas.length === 0"
              description="No hay mesas para ese horario y cantidad de personas"
              :image-size="48"
            />

            <div v-if="mesasFiltradas.length > 0" class="lista-mesas">
              <div v-for="m in mesasFiltradas" :key="m.mesa_id" class="fila-mesa">
                <div>
                  <p class="numero-mesa">Mesa {{ m.numero }}</p>
                  <p class="capacidad">{{ m.capacidad }} personas</p>
                </div>
                <el-button
                  v-if="m.disponible"
                  type="primary"
                  size="small"
                  :loading="reservando === m.mesa_id"
                  @click="reservar(m)"
                >
                  Reservar
                </el-button>
                <el-tag v-else type="info" round>Ocupada</el-tag>
              </div>
            </div>
          </div>
        </aside>
      </div>
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
  max-width: 1080px;
  margin: 0 auto;
  padding: var(--space-6) var(--space-6) var(--space-16);
}

.hero-restaurante {
  position: relative;
  border-radius: var(--radius-lg);
  overflow: hidden;
  margin-bottom: var(--space-8);
  min-height: 320px;
  display: flex;
  align-items: flex-end;
}

.hero-restaurante-imagen {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.hero-restaurante-overlay {
  position: relative;
  width: 100%;
  padding: var(--space-8);
  background: linear-gradient(180deg, transparent 0%, rgba(0, 0, 0, 0.75) 70%);
  color: white;
}

.hero-restaurante-overlay h1 {
  color: white;
  font-size: 2rem;
  margin-bottom: var(--space-2);
}

.hero-restaurante-overlay .descripcion {
  color: rgba(255, 255, 255, 0.85);
  max-width: 60ch;
  margin-bottom: var(--space-5);
}

.hero-restaurante-acciones {
  display: flex;
  gap: var(--space-3);
}

.boton-outline-claro {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.4);
  color: white;
}

.boton-outline-claro:hover {
  background: rgba(255, 255, 255, 0.18);
  border-color: white;
  color: white;
}

.layout-detalle {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--space-8);
  align-items: start;
}

@media (min-width: 860px) {
  .layout-detalle {
    grid-template-columns: 1.6fr 1fr;
  }
}

.columna-menu h2 {
  margin-bottom: var(--space-4);
}

.lista-menu {
  list-style: none;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.lista-menu li {
  display: flex;
  gap: var(--space-4);
  padding: var(--space-3);
  background: var(--surface-raised);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-soft), var(--highlight-inset);
}

.imagen-plato {
  width: 72px;
  height: 72px;
  border-radius: var(--radius-sm);
  object-fit: cover;
  flex-shrink: 0;
}

.info-plato {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  flex: 1;
}

.nombre-plato {
  font-weight: 500;
}

.descripcion-plato {
  color: var(--text-tertiary);
  font-size: 0.85rem;
}

.precio {
  color: var(--color-secondary);
  font-weight: 600;
  font-size: 0.9rem;
}

.columna-reserva {
  position: sticky;
  top: calc(64px + var(--space-6));
}

.tarjeta-reserva {
  padding: var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.tarjeta-reserva h3 {
  margin-bottom: var(--space-1);
}

.campo-reserva {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.boton-disponibilidad {
  width: 100%;
  margin-top: var(--space-2);
  font-weight: 600;
}

.lista-mesas {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin-top: var(--space-2);
}

.fila-mesa {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3);
  background: var(--surface-muted);
  border-radius: var(--radius-sm);
}

.numero-mesa {
  font-weight: 600;
  font-size: 0.9rem;
}

.capacidad {
  color: var(--text-tertiary);
  font-size: 0.8rem;
}
</style>
