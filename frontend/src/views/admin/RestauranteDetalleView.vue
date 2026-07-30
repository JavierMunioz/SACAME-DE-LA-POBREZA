<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Grid } from '@element-plus/icons-vue'
import { api } from '../../api/client'
import {
  agregarItemMenu,
  crearCategoria,
  crearMesa,
  crearPersonal,
  editarCategoria,
  editarItemMenu,
  editarRestaurante,
  eliminarCategoria,
  listarMesas,
  listarPersonal,
  obtenerEstadisticas,
  obtenerRestaurante,
  regenerarQr,
  type Categoria,
  type Estadisticas,
  type Mesa,
  type MenuItem,
  type Personal,
  type RestauranteConMenu,
  type RolPersonal,
} from '../../api/restaurantes'
import { obtenerUbicacion } from '../../api/mesas'
import { agruparMenuPorCategoria } from '../../utils/menuCategorias'
import { useAuthStore } from '../../stores/auth'
import AppTopNav from '../../components/AppTopNav.vue'

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

const dialogoUbicacionAbierto = ref(false)
const guardandoUbicacion = ref(false)
const buscandoUbicacion = ref(false)
const formUbicacion = reactive({ latitud: null as number | null, longitud: null as number | null })

function abrirDialogoUbicacion() {
  formUbicacion.latitud = restaurante.value?.latitud ?? null
  formUbicacion.longitud = restaurante.value?.longitud ?? null
  dialogoUbicacionAbierto.value = true
}

async function usarUbicacionActual() {
  buscandoUbicacion.value = true
  try {
    const ubicacion = await obtenerUbicacion()
    if (!ubicacion) {
      ElMessage.error('No se pudo obtener la ubicación. Activá el permiso en el navegador.')
      return
    }
    formUbicacion.latitud = ubicacion.lat
    formUbicacion.longitud = ubicacion.lng
  } finally {
    buscandoUbicacion.value = false
  }
}

async function guardarUbicacion() {
  guardandoUbicacion.value = true
  try {
    const actualizado = await editarRestaurante(restauranteId, {
      latitud: formUbicacion.latitud,
      longitud: formUbicacion.longitud,
    })
    if (restaurante.value) {
      restaurante.value.latitud = actualizado.latitud
      restaurante.value.longitud = actualizado.longitud
    }
    dialogoUbicacionAbierto.value = false
    ElMessage.success('Ubicación guardada')
  } catch {
    ElMessage.error('No se pudo guardar la ubicación')
  } finally {
    guardandoUbicacion.value = false
  }
}

const dialogoMenuAbierto = ref(false)
const guardandoMenu = ref(false)
const itemMenuEditando = ref<MenuItem | null>(null)
const formMenu = reactive({
  nombre: '',
  descripcion: '',
  precio: 0,
  disponible: true,
  categoriaIds: [] as number[],
})

const dialogoCategoriaAbierto = ref(false)
const guardandoCategoria = ref(false)
const categoriaEditando = ref<Categoria | null>(null)
const formCategoria = reactive({ nombre: '' })

function abrirDialogoNuevaCategoria() {
  categoriaEditando.value = null
  formCategoria.nombre = ''
  dialogoCategoriaAbierto.value = true
}

function abrirDialogoEditarCategoria(categoria: Categoria) {
  categoriaEditando.value = categoria
  formCategoria.nombre = categoria.nombre
  dialogoCategoriaAbierto.value = true
}

async function guardarCategoria() {
  if (!restaurante.value || !formCategoria.nombre.trim()) return
  guardandoCategoria.value = true
  try {
    if (categoriaEditando.value) {
      const actualizada = await editarCategoria(restauranteId, categoriaEditando.value.id, {
        nombre: formCategoria.nombre,
      })
      const idx = restaurante.value.categorias_menu.findIndex((c) => c.id === actualizada.id)
      if (idx !== -1) restaurante.value.categorias_menu[idx] = actualizada
      // el nombre de la categoría también vive embebido en cada plato.
      for (const item of restaurante.value.menu) {
        const c = item.categorias.find((c) => c.id === actualizada.id)
        if (c) c.nombre = actualizada.nombre
      }
      ElMessage.success('Categoría actualizada')
    } else {
      const nueva = await crearCategoria(restauranteId, formCategoria.nombre)
      restaurante.value.categorias_menu.push(nueva)
      ElMessage.success('Categoría creada')
    }
    dialogoCategoriaAbierto.value = false
  } catch (e: unknown) {
    const status = (e as { response?: { status?: number } })?.response?.status
    ElMessage.error(status === 409 ? 'Ya existe una categoría con ese nombre' : 'No se pudo guardar la categoría')
  } finally {
    guardandoCategoria.value = false
  }
}

async function borrarCategoria(categoria: Categoria) {
  if (!restaurante.value) return
  try {
    await ElMessageBox.confirm(
      `¿Borrar la categoría "${categoria.nombre}"? Los platos no se borran, solo dejan de estar agrupados ahí.`,
      'Borrar categoría',
      { type: 'warning' },
    )
  } catch {
    return
  }
  try {
    await eliminarCategoria(restauranteId, categoria.id)
    restaurante.value.categorias_menu = restaurante.value.categorias_menu.filter(
      (c) => c.id !== categoria.id,
    )
    for (const item of restaurante.value.menu) {
      item.categorias = item.categorias.filter((c) => c.id !== categoria.id)
    }
    ElMessage.success('Categoría borrada')
  } catch {
    ElMessage.error('No se pudo borrar la categoría')
  }
}

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

function abrirDialogoNuevoPlato() {
  itemMenuEditando.value = null
  formMenu.nombre = ''
  formMenu.descripcion = ''
  formMenu.precio = 0
  formMenu.disponible = true
  formMenu.categoriaIds = []
  dialogoMenuAbierto.value = true
}

function abrirDialogoEditarPlato(item: MenuItem) {
  itemMenuEditando.value = item
  formMenu.nombre = item.nombre
  formMenu.descripcion = item.descripcion ?? ''
  formMenu.precio = Number(item.precio)
  formMenu.disponible = item.disponible
  formMenu.categoriaIds = item.categorias.map((c) => c.id)
  dialogoMenuAbierto.value = true
}

async function guardarPlato() {
  if (!restaurante.value) return
  guardandoMenu.value = true
  try {
    if (itemMenuEditando.value) {
      const actualizado = await editarItemMenu(restauranteId, itemMenuEditando.value.id, {
        nombre: formMenu.nombre,
        descripcion: formMenu.descripcion || undefined,
        precio: formMenu.precio,
        disponible: formMenu.disponible,
        categoria_ids: formMenu.categoriaIds,
      })
      const idx = restaurante.value.menu.findIndex((m) => m.id === actualizado.id)
      if (idx !== -1) restaurante.value.menu[idx] = actualizado
      ElMessage.success('Plato actualizado')
    } else {
      const nuevo = await agregarItemMenu(restauranteId, {
        nombre: formMenu.nombre,
        descripcion: formMenu.descripcion || undefined,
        precio: formMenu.precio,
        disponible: formMenu.disponible,
        categoria_ids: formMenu.categoriaIds,
      })
      restaurante.value.menu.push(nuevo)
      ElMessage.success('Plato agregado')
    }
    dialogoMenuAbierto.value = false
  } catch {
    ElMessage.error('No se pudo guardar el plato')
  } finally {
    guardandoMenu.value = false
  }
}

const gruposMenuAdmin = computed(() =>
  restaurante.value ? agruparMenuPorCategoria(restaurante.value.menu) : [],
)

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
  <div class="pagina">
    <AppTopNav
      :subtitulo="auth.usuario?.rol === 'admin_restaurante' ? 'Admin de restaurante' : 'Admin General'"
      @salir="cerrarSesion"
    >
      <template #nav>
        <button
          v-if="auth.usuario?.rol === 'admin_general'"
          type="button"
          class="nav-item"
          @click="volver"
        >
          <el-icon :size="16"><Grid /></el-icon>
          <span>Restaurantes</span>
        </button>
      </template>
    </AppTopNav>

    <main class="contenido-principal">
    <div v-if="cargando" class="contenido">
      <el-skeleton animated :rows="8" />
    </div>

    <div v-else-if="restaurante" class="contenido">
      <div class="hero-restaurante">
        <div>
          <h1>{{ restaurante.nombre }}</h1>
          <p v-if="restaurante.descripcion" class="descripcion">{{ restaurante.descripcion }}</p>
          <p class="estado-ubicacion">
            {{
              restaurante.latitud !== null
                ? 'Ubicación configurada — el QR exige estar en el local para ocupar mesa'
                : 'Sin ubicación configurada — cualquiera puede ocupar una mesa escaneando el QR desde donde sea'
            }}
            <button type="button" class="link-editar-ubicacion" @click="abrirDialogoUbicacion">
              {{ restaurante.latitud !== null ? 'Editar' : 'Configurar' }}
            </button>
          </p>
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
        <div class="encabezado-seccion">
          <h2>Categorías del menú</h2>
          <el-button size="small" @click="abrirDialogoNuevaCategoria">Nueva categoría</el-button>
        </div>
        <el-empty
          v-if="restaurante.categorias_menu.length === 0"
          description="Sin categorías — el menú se muestra en una sola lista"
          :image-size="48"
        />
        <div v-else class="lista-chips-categoria">
          <span v-for="categoria in restaurante.categorias_menu" :key="categoria.id" class="chip-categoria">
            {{ categoria.nombre }}
            <button type="button" class="boton-chip" @click="abrirDialogoEditarCategoria(categoria)">✎</button>
            <button type="button" class="boton-chip" @click="borrarCategoria(categoria)">✕</button>
          </span>
        </div>
      </section>

      <section class="seccion">
        <div class="encabezado-seccion">
          <h2>Menú</h2>
          <el-button size="small" @click="abrirDialogoNuevoPlato">Agregar plato</el-button>
        </div>
        <el-empty v-if="restaurante.menu.length === 0" description="Sin platos todavía" />
        <template v-else>
          <div v-for="grupo in gruposMenuAdmin" :key="grupo.categoria?.id ?? 'otros'" class="grupo-categoria-admin">
            <h3 v-if="gruposMenuAdmin.length > 1" class="titulo-categoria-admin">
              {{ grupo.categoria?.nombre ?? 'Sin categoría' }}
            </h3>
            <ul class="lista-menu">
              <li v-for="item in grupo.items" :key="item.id">
                <span class="fila-plato-nombre">
                  {{ item.nombre }}
                  <el-tag v-if="!item.disponible" type="info" size="small">No disponible</el-tag>
                </span>
                <span class="fila-plato-acciones">
                  <span class="precio">${{ Number(item.precio).toLocaleString('es-CO') }}</span>
                  <el-button size="small" text @click="abrirDialogoEditarPlato(item)">Editar</el-button>
                </span>
              </li>
            </ul>
          </div>
        </template>
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

    <el-dialog
      v-model="dialogoMenuAbierto"
      :title="itemMenuEditando ? 'Editar plato' : 'Nuevo plato'"
      width="380px"
    >
      <el-form :model="formMenu" label-position="top">
        <el-form-item label="Nombre">
          <el-input v-model="formMenu.nombre" />
        </el-form-item>
        <el-form-item label="Descripción">
          <el-input v-model="formMenu.descripcion" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="Precio">
          <el-input-number v-model="formMenu.precio" :min="0" style="width: 100%" />
        </el-form-item>
        <el-form-item label="Disponible">
          <el-switch v-model="formMenu.disponible" />
        </el-form-item>
        <el-form-item label="Categorías">
          <el-select v-model="formMenu.categoriaIds" multiple style="width: 100%" placeholder="Ninguna">
            <el-option
              v-for="categoria in restaurante?.categorias_menu ?? []"
              :key="categoria.id"
              :label="categoria.nombre"
              :value="categoria.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogoMenuAbierto = false">Cancelar</el-button>
        <el-button type="primary" :loading="guardandoMenu" @click="guardarPlato">
          Guardar
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="dialogoCategoriaAbierto"
      :title="categoriaEditando ? 'Editar categoría' : 'Nueva categoría'"
      width="340px"
    >
      <el-form :model="formCategoria" label-position="top">
        <el-form-item label="Nombre">
          <el-input v-model="formCategoria.nombre" placeholder="ej. Entradas" @keyup.enter="guardarCategoria" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogoCategoriaAbierto = false">Cancelar</el-button>
        <el-button type="primary" :loading="guardandoCategoria" @click="guardarCategoria">
          Guardar
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="dialogoUbicacionAbierto" title="Ubicación del restaurante" width="380px">
      <p class="texto-ayuda-ubicacion">
        Si configurás la ubicación real del local, el QR de las mesas va a exigir que quien
        escanea esté físicamente cerca para poder ocupar una mesa — evita que alguien use una
        foto del QR desde otro lado.
      </p>
      <el-button :loading="buscandoUbicacion" style="width: 100%; margin-bottom: 16px" @click="usarUbicacionActual">
        Usar mi ubicación actual
      </el-button>
      <el-form :model="formUbicacion" label-position="top">
        <el-form-item label="Latitud">
          <el-input-number v-model="formUbicacion.latitud" :precision="6" :step="0.0001" style="width: 100%" />
        </el-form-item>
        <el-form-item label="Longitud">
          <el-input-number v-model="formUbicacion.longitud" :precision="6" :step="0.0001" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button
          v-if="formUbicacion.latitud !== null"
          text
          @click="formUbicacion.latitud = null; formUbicacion.longitud = null"
        >
          Quitar ubicación
        </el-button>
        <el-button @click="dialogoUbicacionAbierto = false">Cancelar</el-button>
        <el-button type="primary" :loading="guardandoUbicacion" @click="guardarUbicacion">
          Guardar
        </el-button>
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
.pagina {
  min-height: 100dvh;
  background: var(--surface-sunken);
}

.contenido-principal {
  min-height: 100dvh;
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

.estado-ubicacion {
  margin-top: var(--space-2);
  font-size: 0.8rem;
  color: var(--text-tertiary);
}

.link-editar-ubicacion {
  background: none;
  border: none;
  padding: 0;
  margin-left: var(--space-1);
  color: var(--color-secondary);
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  text-decoration: underline;
}

.texto-ayuda-ubicacion {
  color: var(--text-secondary);
  font-size: 0.85rem;
  line-height: 1.5;
  margin-bottom: var(--space-4);
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

.fila-plato-nombre {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.fila-plato-acciones {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.lista-chips-categoria {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.chip-categoria {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-2) var(--space-1) var(--space-3);
  background: var(--surface-muted);
  border-radius: var(--radius-full);
  font-size: 0.825rem;
  font-weight: 500;
}

.boton-chip {
  background: none;
  border: none;
  padding: var(--space-1);
  cursor: pointer;
  color: var(--text-tertiary);
  font-size: 0.75rem;
  line-height: 1;
}

.boton-chip:hover {
  color: var(--text-primary);
}

.grupo-categoria-admin + .grupo-categoria-admin {
  margin-top: var(--space-6);
}

.titulo-categoria-admin {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: var(--space-2);
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
  box-shadow: var(--shadow-soft), var(--highlight-inset);
  transition: box-shadow var(--duration-base) var(--ease-standard);
}

.tarjeta-qr:hover {
  box-shadow: var(--shadow-soft-hover), var(--highlight-inset);
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
  box-shadow: var(--shadow-soft), var(--highlight-inset);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  transition: box-shadow var(--duration-base) var(--ease-standard);
}

.tarjeta-metrica:hover {
  box-shadow: var(--shadow-soft-hover), var(--highlight-inset);
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
  background: var(--surface-muted);
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
