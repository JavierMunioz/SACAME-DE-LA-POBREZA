<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { obtenerRestaurante, type RestauranteConMenu } from '../../api/restaurantes'
import {
  consultarDisponibilidad,
  crearReserva,
  type MesaDisponibilidad,
} from '../../api/reservas'
import { useAuthStore } from '../../stores/auth'

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
})

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

async function reservar(mesa: MesaDisponibilidad) {
  // Reservar necesita identidad (para saludar por nombre al escanear el
  // QR); pedir sin reserva no la necesita. Frenamos acá, no antes.
  if (!auth.token) {
    router.push(`/login?redirect=${encodeURIComponent(route.fullPath)}`)
    return
  }
  reservando.value = mesa.mesa_id
  try {
    const inicio = new Date(`${form.fecha}T${form.hora}:00`).toISOString()
    await crearReserva({ mesa_id: mesa.mesa_id, inicio })
    ElMessage.success(`Mesa ${mesa.numero} reservada. Llegá 15 min antes.`)
    await buscarDisponibilidad()
  } catch (e: unknown) {
    const status = (e as { response?: { status?: number } })?.response?.status
    ElMessage.error(status === 409 ? 'Esa mesa ya se reservó, elegí otra' : 'No se pudo reservar')
  } finally {
    reservando.value = null
  }
}

function volver() {
  router.push('/cliente')
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
      <button type="button" class="volver" @click="volver">← Restaurantes</button>
    </header>

    <div v-if="cargando" class="contenido">
      <el-skeleton animated :rows="6" />
    </div>

    <main v-else-if="restaurante" class="contenido">
      <div class="hero-restaurante">
        <h1>{{ restaurante.nombre }}</h1>
        <p v-if="restaurante.descripcion" class="descripcion">{{ restaurante.descripcion }}</p>
      </div>

      <section class="seccion">
        <h2>Menú</h2>
        <el-empty v-if="restaurante.menu.length === 0" description="Sin platos todavía" />
        <ul v-else class="lista-menu">
          <li v-for="item in restaurante.menu" :key="item.id">
            <div>
              <p class="nombre-plato">{{ item.nombre }}</p>
              <p v-if="item.descripcion" class="descripcion-plato">{{ item.descripcion }}</p>
            </div>
            <span class="precio">${{ Number(item.precio).toLocaleString('es-CO') }}</span>
          </li>
        </ul>
      </section>

      <section class="seccion">
        <h2>Reservar mesa</h2>
        <div class="buscador">
          <el-date-picker v-model="form.fecha" type="date" value-format="YYYY-MM-DD" size="large" />
          <el-time-select
            v-model="form.hora"
            start="11:00"
            end="23:00"
            step="00:30"
            size="large"
            style="max-width: 140px"
          />
          <el-button type="primary" size="large" :loading="buscando" @click="buscarDisponibilidad">
            Ver disponibilidad
          </el-button>
        </div>

        <el-empty
          v-if="busquedaHecha && !buscando && mesas.length === 0"
          description="Este restaurante todavía no tiene mesas cargadas"
        />

        <div v-if="mesas.length > 0" class="grid-mesas">
          <div v-for="m in mesas" :key="m.mesa_id" class="tarjeta-mesa">
            <div class="tarjeta-mesa-info">
              <p class="numero-mesa">Mesa {{ m.numero }}</p>
              <p class="capacidad">{{ m.capacidad }} personas</p>
            </div>
            <el-tag :type="m.disponible ? 'success' : 'info'" round>
              {{ m.disponible ? 'Disponible' : 'Ocupada' }}
            </el-tag>
            <el-button
              v-if="m.disponible"
              type="primary"
              :loading="reservando === m.mesa_id"
              class="boton-reservar"
              @click="reservar(m)"
            >
              Reservar
            </el-button>
          </div>
        </div>
      </section>
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
  max-width: 720px;
  margin: 0 auto;
  padding: var(--space-8) var(--space-6) var(--space-16);
}

.hero-restaurante {
  margin-bottom: var(--space-8);
}

.hero-restaurante h1 {
  font-size: 1.75rem;
  margin-bottom: var(--space-2);
}

.descripcion {
  color: var(--text-secondary);
}

.seccion {
  margin-bottom: var(--space-10);
}

.seccion h2 {
  margin-bottom: var(--space-4);
}

.lista-menu {
  list-style: none;
  padding: 0;
  background: var(--surface-raised);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.lista-menu li {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-4);
  padding: var(--space-4) var(--space-5);
}

.lista-menu li + li {
  border-top: 1px solid var(--border-subtle);
}

.nombre-plato {
  font-weight: 500;
}

.descripcion-plato {
  color: var(--text-tertiary);
  font-size: 0.85rem;
  margin-top: var(--space-1);
}

.precio {
  color: var(--text-secondary);
  font-weight: 500;
  white-space: nowrap;
}

.buscador {
  display: flex;
  gap: var(--space-3);
  align-items: center;
  margin-bottom: var(--space-5);
  flex-wrap: wrap;
}

.grid-mesas {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: var(--space-4);
}

.tarjeta-mesa {
  background: var(--surface-raised);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: var(--space-5);
  text-align: center;
  box-shadow: var(--shadow-sm);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
}

.tarjeta-mesa-info {
  margin-bottom: var(--space-1);
}

.numero-mesa {
  font-weight: 600;
}

.capacidad {
  color: var(--text-tertiary);
  font-size: 0.85rem;
}

.boton-reservar {
  width: 100%;
  margin-top: var(--space-2);
  font-weight: 600;
}
</style>
