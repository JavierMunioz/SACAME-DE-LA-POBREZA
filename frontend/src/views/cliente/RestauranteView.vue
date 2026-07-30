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

const route = useRoute()
const router = useRouter()
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

onMounted(cargar)
</script>

<template>
  <div class="page" v-loading="cargando">
    <template v-if="restaurante">
      <el-button text @click="volver">&larr; Restaurantes</el-button>

      <header class="encabezado">
        <h1>{{ restaurante.nombre }}</h1>
        <p class="subtitulo">{{ restaurante.descripcion }}</p>
      </header>

      <section>
        <h2>Menú</h2>
        <ul class="lista-menu">
          <li v-for="item in restaurante.menu" :key="item.id">
            <span>{{ item.nombre }}</span>
            <span class="precio">${{ Number(item.precio).toLocaleString('es-CO') }}</span>
          </li>
        </ul>
      </section>

      <section>
        <h2>Reservar mesa</h2>
        <div class="buscador">
          <el-date-picker v-model="form.fecha" type="date" value-format="YYYY-MM-DD" />
          <el-time-select v-model="form.hora" start="11:00" end="23:00" step="00:30" />
          <el-button type="primary" :loading="buscando" @click="buscarDisponibilidad">
            Ver mesas disponibles
          </el-button>
        </div>

        <el-empty
          v-if="busquedaHecha && !buscando && mesas.length === 0"
          description="Este restaurante todavía no tiene mesas cargadas"
        />

        <div v-if="mesas.length > 0" class="grid-mesas">
          <el-card v-for="m in mesas" :key="m.mesa_id" class="tarjeta-mesa">
            <p class="numero-mesa">Mesa {{ m.numero }}</p>
            <p class="capacidad">{{ m.capacidad }} personas</p>
            <el-tag :type="m.disponible ? 'success' : 'info'">
              {{ m.disponible ? 'Disponible' : 'Ocupada' }}
            </el-tag>
            <el-button
              v-if="m.disponible"
              type="primary"
              size="small"
              :loading="reservando === m.mesa_id"
              style="margin-top: 0.75rem; width: 100%"
              @click="reservar(m)"
            >
              Reservar
            </el-button>
          </el-card>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.page {
  max-width: 900px;
  margin: 0 auto;
  padding: 2.5rem 1.5rem;
}

.encabezado {
  margin: 1rem 0 2rem;
}

.subtitulo {
  color: #909399;
}

section {
  margin-bottom: 2.5rem;
}

.lista-menu {
  list-style: none;
  padding: 0;
}

.lista-menu li {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0;
  border-bottom: 1px solid #ebeef5;
}

.precio {
  color: #606266;
}

.buscador {
  display: flex;
  gap: 0.75rem;
  align-items: center;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
}

.grid-mesas {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 1rem;
}

.tarjeta-mesa {
  text-align: center;
}

.numero-mesa {
  font-weight: 600;
}

.capacidad {
  color: #909399;
  font-size: 0.85rem;
  margin-bottom: 0.5rem;
}
</style>
