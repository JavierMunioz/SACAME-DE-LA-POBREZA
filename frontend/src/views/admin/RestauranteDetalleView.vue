<script setup lang="ts">
import { onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../../api/client'
import {
  crearMesa,
  crearPersonal,
  listarMesas,
  listarPersonal,
  obtenerRestaurante,
  regenerarQr,
  type Mesa,
  type Personal,
  type RestauranteConMenu,
  type RolPersonal,
} from '../../api/restaurantes'

const route = useRoute()
const router = useRouter()
const restauranteId = Number(route.params.id)

const restaurante = ref<RestauranteConMenu | null>(null)
const mesas = ref<Mesa[]>([])
const personal = ref<Personal[]>([])
const cargando = ref(true)
const dialogoAbierto = ref(false)
const guardando = ref(false)
const form = reactive({ numero: 1, capacidad: 4 })

const dialogoPersonalAbierto = ref(false)
const guardandoPersonal = ref(false)
const formPersonal = reactive({
  nombre: '',
  email: '',
  password: '',
  rol: 'mesero' as RolPersonal,
})

// blob URLs de los QR autenticados: mesa_id -> object URL
const qrUrls = reactive<Record<number, string>>({})

async function cargarQr(mesa: Mesa) {
  const { data } = await api.get(`/mesas/${mesa.id}/qr.png`, { responseType: 'blob' })
  qrUrls[mesa.id] = URL.createObjectURL(data)
}

async function cargar() {
  cargando.value = true
  const [r, m, p] = await Promise.all([
    obtenerRestaurante(restauranteId),
    listarMesas(restauranteId),
    listarPersonal(restauranteId),
  ])
  restaurante.value = r
  mesas.value = m
  personal.value = p
  cargando.value = false
  await Promise.all(m.map(cargarQr))
}

function abrirDialogoPersonal() {
  formPersonal.nombre = ''
  formPersonal.email = ''
  formPersonal.password = ''
  formPersonal.rol = 'mesero'
  dialogoPersonalAbierto.value = true
}

async function guardarPersonal() {
  guardandoPersonal.value = true
  try {
    const nuevo = await crearPersonal(restauranteId, { ...formPersonal })
    personal.value.push(nuevo)
    dialogoPersonalAbierto.value = false
    ElMessage.success('Cuenta creada')
  } catch (e: unknown) {
    const status = (e as { response?: { status?: number } })?.response?.status
    ElMessage.error(status === 409 ? 'Ese email ya está registrado' : 'No se pudo crear la cuenta')
  } finally {
    guardandoPersonal.value = false
  }
}

const etiquetaRol: Record<RolPersonal, string> = {
  mesero: 'Mesero',
  cocina: 'Cocina',
  admin_restaurante: 'Admin de restaurante',
}

async function guardarMesa() {
  guardando.value = true
  try {
    const mesa = await crearMesa(restauranteId, { ...form })
    mesas.value.push(mesa)
    await cargarQr(mesa)
    dialogoAbierto.value = false
    ElMessage.success('Mesa creada')
  } catch (e: unknown) {
    const status = (e as { response?: { status?: number } })?.response?.status
    ElMessage.error(status === 409 ? 'Ya existe esa mesa' : 'No se pudo crear la mesa')
  } finally {
    guardando.value = false
  }
}

async function regenerar(mesa: Mesa) {
  await ElMessageBox.confirm(
    `El QR impreso de la mesa ${mesa.numero} dejará de funcionar. ¿Continuar?`,
    'Regenerar QR',
    { type: 'warning' },
  )
  const actualizada = await regenerarQr(mesa.id)
  const idx = mesas.value.findIndex((m) => m.id === mesa.id)
  mesas.value[idx] = actualizada
  URL.revokeObjectURL(qrUrls[mesa.id])
  await cargarQr(actualizada)
  ElMessage.success('QR regenerado')
}

function abrirDialogo() {
  form.numero = mesas.value.length + 1
  form.capacidad = 4
  dialogoAbierto.value = true
}

function volver() {
  router.push('/admin')
}

onMounted(cargar)
onUnmounted(() => {
  Object.values(qrUrls).forEach((u) => URL.revokeObjectURL(u))
})
</script>

<template>
  <div class="page" v-loading="cargando">
    <template v-if="restaurante">
      <el-button text @click="volver">&larr; Restaurantes</el-button>

      <header class="encabezado">
        <div>
          <h1>{{ restaurante.nombre }}</h1>
          <p class="subtitulo">{{ restaurante.descripcion }}</p>
        </div>
        <el-button type="primary" @click="abrirDialogo">Nueva mesa</el-button>
      </header>

      <section>
        <h2>Menú</h2>
        <el-empty v-if="restaurante.menu.length === 0" description="Sin platos todavía" />
        <ul v-else class="lista-menu">
          <li v-for="item in restaurante.menu" :key="item.id">
            <span>{{ item.nombre }}</span>
            <span class="precio">${{ Number(item.precio).toLocaleString('es-CO') }}</span>
          </li>
        </ul>
      </section>

      <section>
        <h2>Mesas y códigos QR</h2>
        <el-empty v-if="mesas.length === 0" description="Sin mesas todavía" />
        <div v-else class="grid-qr">
          <el-card v-for="mesa in mesas" :key="mesa.id" class="tarjeta-qr">
            <p class="numero-mesa">Mesa {{ mesa.numero }}</p>
            <p class="capacidad">{{ mesa.capacidad }} personas</p>
            <img v-if="qrUrls[mesa.id]" :src="qrUrls[mesa.id]" :alt="`QR mesa ${mesa.numero}`" />
            <div class="acciones-qr">
              <a v-if="qrUrls[mesa.id]" :href="qrUrls[mesa.id]" :download="`mesa-${mesa.numero}-qr.png`">
                <el-button size="small">Descargar</el-button>
              </a>
              <el-button size="small" @click="regenerar(mesa)">Regenerar</el-button>
            </div>
          </el-card>
        </div>
      </section>

      <section>
        <div class="encabezado-seccion">
          <h2>Personal</h2>
          <el-button size="small" @click="abrirDialogoPersonal">Nueva cuenta</el-button>
        </div>
        <el-empty v-if="personal.length === 0" description="Sin mesero ni cocina todavía" />
        <el-table v-else :data="personal">
          <el-table-column prop="nombre" label="Nombre" />
          <el-table-column prop="email" label="Email" />
          <el-table-column label="Rol">
            <template #default="{ row }">{{ etiquetaRol[row.rol as RolPersonal] }}</template>
          </el-table-column>
        </el-table>
      </section>
    </template>

    <el-dialog v-model="dialogoAbierto" title="Nueva mesa" width="360px">
      <el-form :model="form" label-position="top">
        <el-form-item label="Número">
          <el-input-number v-model="form.numero" :min="1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="Capacidad">
          <el-input-number v-model="form.capacidad" :min="1" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogoAbierto = false">Cancelar</el-button>
        <el-button type="primary" :loading="guardando" @click="guardarMesa">Crear</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="dialogoPersonalAbierto" title="Nueva cuenta de personal" width="380px">
      <el-form :model="formPersonal" label-position="top">
        <el-form-item label="Nombre">
          <el-input v-model="formPersonal.nombre" />
        </el-form-item>
        <el-form-item label="Email">
          <el-input v-model="formPersonal.email" type="email" />
        </el-form-item>
        <el-form-item label="Contraseña">
          <el-input v-model="formPersonal.password" type="password" show-password />
        </el-form-item>
        <el-form-item label="Rol">
          <el-select v-model="formPersonal.rol" style="width: 100%">
            <el-option label="Mesero" value="mesero" />
            <el-option label="Cocina" value="cocina" />
            <el-option label="Admin de restaurante" value="admin_restaurante" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogoPersonalAbierto = false">Cancelar</el-button>
        <el-button type="primary" :loading="guardandoPersonal" @click="guardarPersonal">
          Crear
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page {
  max-width: 960px;
  margin: 0 auto;
  padding: 2.5rem 1.5rem;
}

.encabezado {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin: 1rem 0 2rem;
}

.subtitulo {
  color: #909399;
}

section {
  margin-bottom: 2.5rem;
}

.encabezado-seccion {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.encabezado-seccion h2 {
  margin: 0;
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

.grid-qr {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 1rem;
}

.tarjeta-qr {
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

.tarjeta-qr img {
  width: 100%;
  height: auto;
}

.acciones-qr {
  display: flex;
  gap: 0.5rem;
  justify-content: center;
  margin-top: 0.75rem;
}

@media print {
  .encabezado,
  .lista-menu,
  section h2,
  .acciones-qr,
  header,
  .el-button {
    display: none;
  }
}
</style>
