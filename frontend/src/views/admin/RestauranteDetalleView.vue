<script setup lang="ts">
import { onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Grid } from '@element-plus/icons-vue'
import { api } from '../../api/client'
import {
  crearMesa,
  crearPersonal,
  listarMesas,
  listarPersonal,
  obtenerEstadisticas,
  obtenerRestaurante,
  regenerarQr,
  type Estadisticas,
  type Mesa,
  type Personal,
  type RestauranteConMenu,
  type RolPersonal,
} from '../../api/restaurantes'
import { useAuthStore } from '../../stores/auth'
import AppSidebar from '../../components/AppSidebar.vue'

const auth = useAuthStore()

const route = useRoute()
const router = useRouter()
const restauranteId = Number(route.params.id)

const restaurante = ref<RestauranteConMenu | null>(null)
const mesas = ref<Mesa[]>([])
const personal = ref<Personal[]>([])
const estadisticas = ref<Estadisticas | null>(null)
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
  const [r, m, p, e] = await Promise.all([
    obtenerRestaurante(restauranteId),
    listarMesas(restauranteId),
    listarPersonal(restauranteId),
    obtenerEstadisticas(restauranteId),
  ])
  restaurante.value = r
  mesas.value = m
  personal.value = p
  estadisticas.value = e
  cargando.value = false
  await Promise.all(m.map(cargarQr))
}

function formatoMoneda(valor: string): string {
  return `$${Number(valor).toLocaleString('es-CO')}`
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

const etiquetaEstadoMesa: Record<Mesa['estado'], string> = {
  libre: 'Libre',
  reservada: 'Reservada',
  ocupada: 'Ocupada',
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
  const urlAnterior = qrUrls[mesa.id]
  if (urlAnterior) URL.revokeObjectURL(urlAnterior)
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

function cerrarSesion() {
  auth.logout()
  router.push('/login')
}

onMounted(cargar)
onUnmounted(() => {
  Object.values(qrUrls).forEach((u) => URL.revokeObjectURL(u))
})
</script>

<template>
  <div class="layout">
    <AppSidebar subtitulo="Admin General" @salir="cerrarSesion">
      <template #nav>
        <button type="button" class="nav-item" @click="volver">
          <el-icon :size="18"><Grid /></el-icon>
          <span>Restaurantes</span>
        </button>
      </template>
    </AppSidebar>

    <main class="contenido-principal">
    <div v-if="cargando" class="contenido">
      <el-skeleton animated :rows="8" />
    </div>

    <div v-else-if="restaurante" class="contenido">
      <div class="hero-restaurante">
        <div>
          <h1>{{ restaurante.nombre }}</h1>
          <p v-if="restaurante.descripcion" class="descripcion">{{ restaurante.descripcion }}</p>
        </div>
        <el-button type="primary" size="large" @click="abrirDialogo">Nueva mesa</el-button>
      </div>

      <div v-if="estadisticas" class="grid-dashboard">
        <div class="tarjeta-metrica celda-capacidad">
          <span class="label-mono">Capacidad actual</span>
          <div class="metrica-capacidad">
            <span class="metrica-numero">
              {{ estadisticas.mesas_total ? Math.round((estadisticas.mesas_ocupadas / estadisticas.mesas_total) * 100) : 0 }}%
            </span>
            <span class="metrica-subtexto">Ocupado</span>
          </div>
          <div class="barra-capacidad">
            <div
              class="barra-capacidad-relleno"
              :style="{ width: `${estadisticas.mesas_total ? (estadisticas.mesas_ocupadas / estadisticas.mesas_total) * 100 : 0}%` }"
            ></div>
          </div>
          <span class="metrica-detalle font-mono">{{ estadisticas.mesas_ocupadas }} / {{ estadisticas.mesas_total }} mesas</span>
        </div>

        <div class="tarjeta-metrica celda-revenue">
          <span class="label-mono">Ingresos de hoy</span>
          <span class="metrica-numero metrica-revenue font-mono">{{ formatoMoneda(estadisticas.revenue_hoy) }}</span>
          <span
            v-if="estadisticas.variacion_pct !== null"
            class="badge-variacion"
            :class="estadisticas.variacion_pct >= 0 ? 'badge-variacion--positiva' : 'badge-variacion--negativa'"
          >
            {{ estadisticas.variacion_pct >= 0 ? '↗' : '↘' }} {{ Math.abs(estadisticas.variacion_pct).toFixed(1) }}% vs. ayer
          </span>
          <span v-else class="metrica-detalle">Sin datos de ayer para comparar</span>
        </div>

        <div class="tarjeta-metrica tarjeta-hot-items celda-hot-items">
          <div class="encabezado-seccion">
            <span class="label-mono">Más vendidos hoy</span>
          </div>
          <el-empty
            v-if="estadisticas.platos_mas_vendidos_hoy.length === 0"
            description="Todavía no se facturó nada hoy"
            :image-size="48"
          />
          <ul v-else class="lista-hot-items">
            <li v-for="plato in estadisticas.platos_mas_vendidos_hoy" :key="plato.menu_item_id">
              <span class="hot-item-nombre">{{ plato.nombre }}</span>
              <span class="hot-item-vendidos font-mono">{{ plato.cantidad_vendida }} vendidos</span>
              <span class="hot-item-precio font-mono">{{ formatoMoneda(plato.precio) }}</span>
            </li>
          </ul>
        </div>
      </div>

      <section class="seccion">
        <h2>Menú</h2>
        <el-empty v-if="restaurante.menu.length === 0" description="Sin platos todavía" />
        <ul v-else class="lista-menu">
          <li v-for="item in restaurante.menu" :key="item.id">
            <span>{{ item.nombre }}</span>
            <span class="precio">${{ Number(item.precio).toLocaleString('es-CO') }}</span>
          </li>
        </ul>
      </section>

      <section class="seccion">
        <h2>Mesas y códigos QR</h2>
        <el-empty v-if="mesas.length === 0" description="Sin mesas todavía" />
        <div v-else class="grid-qr">
          <div v-for="mesa in mesas" :key="mesa.id" class="tarjeta-qr">
            <div class="encabezado-tarjeta-qr">
              <p class="numero-mesa">Mesa {{ mesa.numero }}</p>
              <span class="badge-estado-mesa" :class="`badge-estado-mesa--${mesa.estado}`">
                {{ etiquetaEstadoMesa[mesa.estado] }}
              </span>
            </div>
            <p class="capacidad">{{ mesa.capacidad }} personas</p>
            <div class="marco-qr">
              <img v-if="qrUrls[mesa.id]" :src="qrUrls[mesa.id]" :alt="`QR mesa ${mesa.numero}`" />
              <el-skeleton v-else animated :rows="1" style="width: 100%" />
            </div>
            <div class="acciones-qr">
              <a v-if="qrUrls[mesa.id]" :href="qrUrls[mesa.id]" :download="`mesa-${mesa.numero}-qr.png`">
                <el-button size="small">Descargar</el-button>
              </a>
              <el-button size="small" @click="regenerar(mesa)">Regenerar</el-button>
            </div>
          </div>
        </div>
      </section>

      <section class="seccion">
        <div class="encabezado-seccion">
          <h2>Personal</h2>
          <el-button size="small" @click="abrirDialogoPersonal">Nueva cuenta</el-button>
        </div>
        <el-empty v-if="personal.length === 0" description="Sin mesero ni cocina todavía" />
        <ul v-else class="lista-personal">
          <li v-for="p in personal" :key="p.id">
            <div>
              <p class="nombre-personal">{{ p.nombre }}</p>
              <p class="email-personal">{{ p.email }}</p>
            </div>
            <span class="badge-rol">{{ etiquetaRol[p.rol] }}</span>
          </li>
        </ul>
      </section>
    </div>
    </main>

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
.layout {
  min-height: 100dvh;
}

.contenido-principal {
  margin-left: var(--sidebar-width);
  min-height: 100dvh;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  font-size: 0.875rem;
  font-weight: 500;
  background: none;
  border: none;
  cursor: pointer;
  width: 100%;
  text-align: left;
  transition: background var(--duration-fast) var(--ease-standard);
}

.nav-item:hover {
  background: var(--color-surface-container);
}

.contenido {
  max-width: 960px;
  margin: 0 auto;
  padding: var(--space-8) var(--space-6) var(--space-16);
}

.hero-restaurante {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-4);
  margin-bottom: var(--space-10);
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

.encabezado-seccion {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-4);
}

.encabezado-seccion h2 {
  margin: 0;
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
  padding: var(--space-4) var(--space-5);
}

.lista-menu li + li {
  border-top: 1px solid var(--border-subtle);
}

.precio {
  color: var(--text-secondary);
  font-weight: 500;
}

.grid-qr {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: var(--space-4);
}

.tarjeta-qr {
  background: var(--surface-raised);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: var(--space-5);
  text-align: center;
  box-shadow: var(--shadow-sm);
}

.encabezado-tarjeta-qr {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
}

.numero-mesa {
  font-weight: 600;
}

.badge-estado-mesa {
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.02em;
  padding: 2px var(--space-2);
  border-radius: var(--radius-full);
}

.badge-estado-mesa--libre {
  color: var(--color-success-text);
  background: var(--color-success-bg);
}

.badge-estado-mesa--reservada {
  color: var(--color-warning-text);
  background: var(--color-warning-bg);
}

.badge-estado-mesa--ocupada {
  color: var(--color-danger-text);
  background: var(--color-danger-bg);
}

/* ---- Dashboard: capacidad / revenue / hot items ---- */
/* Bento real: 3 métricas → 3 celdas (1 grande + 2 apiladas), no tres
   tarjetas idénticas en fila. La celda con más contenido (la lista de
   platos) se lleva el espacio grande. */
.grid-dashboard {
  display: grid;
  grid-template-columns: 1.3fr 1fr;
  grid-template-rows: 1fr 1fr;
  gap: var(--space-5);
  margin-bottom: var(--space-10);
}

.celda-hot-items {
  grid-column: 1;
  grid-row: 1 / 3;
}

.celda-capacidad {
  grid-column: 2;
  grid-row: 1;
}

.celda-revenue {
  grid-column: 2;
  grid-row: 2;
}

@media (max-width: 860px) {
  .grid-dashboard {
    grid-template-columns: 1fr;
    grid-template-rows: none;
  }

  .celda-hot-items,
  .celda-capacidad,
  .celda-revenue {
    grid-column: 1;
    grid-row: auto;
  }
}

.tarjeta-metrica {
  background: var(--surface-raised);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: var(--space-5);
  box-shadow: var(--shadow-soft-sm), var(--highlight-inset);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  transition: box-shadow var(--duration-base) var(--ease-standard);
}

.tarjeta-metrica:hover {
  box-shadow: var(--shadow-soft-md), var(--highlight-inset);
}

/* Única celda con variación de fondo del bento (evita "todo blanco"). */
.tarjeta-hot-items {
  background: linear-gradient(165deg, var(--color-secondary-soft) 0%, var(--surface-raised) 55%);
}

.metrica-capacidad {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
}

.metrica-numero {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 2rem;
  color: var(--color-secondary);
  line-height: 1;
}

.metrica-revenue {
  color: var(--text-primary);
}

.metrica-subtexto {
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.metrica-detalle {
  color: var(--text-tertiary);
  font-size: 0.8rem;
}

.barra-capacidad {
  height: 6px;
  border-radius: var(--radius-full);
  background: var(--color-surface-container);
  overflow: hidden;
  margin: var(--space-1) 0;
}

.barra-capacidad-relleno {
  height: 100%;
  background: var(--color-secondary);
  border-radius: var(--radius-full);
  transition: width var(--duration-base) var(--ease-standard);
}

.badge-variacion {
  align-self: flex-start;
  font-size: 0.8rem;
  font-weight: 600;
  padding: 2px var(--space-2);
  border-radius: var(--radius-full);
}

.badge-variacion--positiva {
  color: var(--color-success-text);
  background: var(--color-success-bg);
}

.badge-variacion--negativa {
  color: var(--color-danger-text);
  background: var(--color-danger-bg);
}

.tarjeta-hot-items :deep(.el-empty) {
  padding: var(--space-4) 0;
}

.lista-hot-items {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.lista-hot-items li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  font-size: 0.85rem;
}

.hot-item-nombre {
  font-weight: 500;
  flex: 1;
}

.hot-item-vendidos {
  color: var(--text-tertiary);
  font-size: 0.75rem;
}

.hot-item-precio {
  color: var(--color-secondary);
  font-weight: 600;
}

.capacidad {
  color: var(--text-tertiary);
  font-size: 0.85rem;
  margin-bottom: var(--space-3);
}

.marco-qr {
  background: var(--surface-sunken);
  border-radius: var(--radius-sm);
  padding: var(--space-3);
  margin-bottom: var(--space-3);
}

.tarjeta-qr img {
  width: 100%;
  height: auto;
  display: block;
}

.acciones-qr {
  display: flex;
  gap: var(--space-2);
  justify-content: center;
}

.lista-personal {
  list-style: none;
  padding: 0;
  background: var(--surface-raised);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.lista-personal li {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-4) var(--space-5);
}

.lista-personal li + li {
  border-top: 1px solid var(--border-subtle);
}

.nombre-personal {
  font-weight: 500;
}

.email-personal {
  color: var(--text-tertiary);
  font-size: 0.85rem;
  margin-top: var(--space-1);
}

.badge-rol {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--color-info);
  background: var(--color-info-bg);
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-full);
  white-space: nowrap;
}

@media print {
  .encabezado-pagina,
  .hero-restaurante,
  .lista-menu,
  .lista-personal,
  .acciones-qr,
  section h2 {
    display: none;
  }
}
</style>
