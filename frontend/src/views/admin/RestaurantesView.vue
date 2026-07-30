<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Grid, Plus } from '@element-plus/icons-vue'
import {
  crearRestaurante,
  listarRestaurantes,
  type MenuItemCreate,
  type Restaurante,
} from '../../api/restaurantes'
import { useAuthStore } from '../../stores/auth'
import AppTopNav from '../../components/AppTopNav.vue'

const router = useRouter()
const auth = useAuthStore()

const restaurantes = ref<Restaurante[]>([])
const cargando = ref(true)
const dialogoAbierto = ref(false)
const guardando = ref(false)

const CATEGORIAS = ['Mariscos', 'Italiana', 'Hamburguesas', 'Parrilla', 'Sushi', 'Otra']

const form = reactive({
  nombre: '',
  descripcion: '',
  categoria: '',
  menu: [] as MenuItemCreate[],
})

async function cargar() {
  cargando.value = true
  restaurantes.value = await listarRestaurantes()
  cargando.value = false
}

function agregarItemMenu() {
  form.menu.push({ nombre: '', precio: 0 })
}

function quitarItemMenu(index: number) {
  form.menu.splice(index, 1)
}

function abrirDialogo() {
  form.nombre = ''
  form.descripcion = ''
  form.categoria = ''
  form.menu = []
  dialogoAbierto.value = true
}

async function guardar() {
  if (!form.nombre.trim()) {
    ElMessage.warning('El nombre es obligatorio')
    return
  }
  guardando.value = true
  try {
    await crearRestaurante({
      nombre: form.nombre,
      descripcion: form.descripcion || undefined,
      categoria: form.categoria || undefined,
      menu_inicial: form.menu.filter((m) => m.nombre.trim()),
    })
    ElMessage.success('Restaurante creado')
    dialogoAbierto.value = false
    await cargar()
  } catch {
    ElMessage.error('No se pudo crear el restaurante')
  } finally {
    guardando.value = false
  }
}

function irADetalle(id: number) {
  router.push(`/admin/restaurantes/${id}`)
}

function cerrarSesion() {
  auth.logout()
  router.push('/login')
}

onMounted(cargar)
</script>

<template>
  <div class="pagina">
    <AppTopNav subtitulo="Admin General" @salir="cerrarSesion">
      <template #nav>
        <span class="nav-item nav-item--activo">
          <el-icon :size="16"><Grid /></el-icon>
          <span>Restaurantes</span>
        </span>
      </template>
      <template #accion-principal>
        <el-button type="primary" @click="abrirDialogo">
          <el-icon :size="16" style="margin-right: 6px"><Plus /></el-icon>
          Nuevo restaurante
        </el-button>
      </template>
    </AppTopNav>

    <main class="contenido-principal">
      <div class="titulo-seccion">
        <h1>Restaurantes</h1>
        <p class="subtitulo">Hola, {{ auth.usuario?.nombre }}</p>
      </div>

      <div class="contenido">
        <div v-if="cargando" class="grid-restaurantes">
          <el-skeleton v-for="i in 3" :key="i" animated :rows="2" class="tarjeta-skeleton" />
        </div>

        <div v-else-if="restaurantes.length === 0" class="estado-vacio">
          <p class="estado-vacio-titulo">Todavía no hay restaurantes</p>
          <p class="estado-vacio-texto">
            Creá el primero para empezar a dar de alta mesas y personal.
          </p>
          <el-button type="primary" @click="abrirDialogo">Nuevo restaurante</el-button>
        </div>

        <div v-else class="grid-restaurantes">
          <button
            v-for="r in restaurantes"
            :key="r.id"
            type="button"
            class="tarjeta-restaurante"
            @click="irADetalle(r.id)"
          >
            <h2>{{ r.nombre }}</h2>
            <p v-if="r.descripcion" class="descripcion">{{ r.descripcion }}</p>
            <p class="fecha">Creado el {{ new Date(r.created_at).toLocaleDateString('es-CO') }}</p>
          </button>
        </div>
      </div>
    </main>

    <el-dialog v-model="dialogoAbierto" title="Nuevo restaurante" width="520px">
      <el-form :model="form" label-position="top">
        <el-form-item label="Nombre">
          <el-input v-model="form.nombre" size="large" />
        </el-form-item>
        <el-form-item label="Descripción">
          <el-input v-model="form.descripcion" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="Categoría">
          <el-select v-model="form.categoria" placeholder="Elegí una categoría" style="width: 100%">
            <el-option v-for="c in CATEGORIAS" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>

        <el-form-item label="Menú inicial (opcional)">
          <div class="menu-items">
            <div v-for="(item, i) in form.menu" :key="i" class="menu-item-row">
              <el-input v-model="item.nombre" placeholder="Nombre del plato" />
              <el-input-number v-model="item.precio" :min="0" :step="1000" controls-position="right" />
              <el-button text type="danger" @click="quitarItemMenu(i)">Quitar</el-button>
            </div>
            <el-button text @click="agregarItemMenu">+ Agregar plato</el-button>
          </div>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogoAbierto = false">Cancelar</el-button>
        <el-button type="primary" :loading="guardando" @click="guardar">Crear</el-button>
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
  max-width: 1160px;
  margin: 0 auto;
  padding: var(--space-8) var(--space-6) var(--space-16);
}

.titulo-seccion {
  margin-bottom: var(--space-8);
}

.titulo-seccion h1 {
  font-size: 1.75rem;
  margin-bottom: var(--space-1);
}

.subtitulo {
  color: var(--text-tertiary);
  font-size: 0.875rem;
}

.contenido {
  width: 100%;
}

.grid-restaurantes {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: var(--gutter);
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
  margin-bottom: var(--space-5);
}

.tarjeta-restaurante {
  text-align: left;
  background: var(--surface-raised);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: var(--space-6);
  cursor: pointer;
  box-shadow: var(--shadow-soft), var(--highlight-inset);
  transition:
    box-shadow var(--duration-base) var(--ease-standard),
    border-color var(--duration-base) var(--ease-standard);
}

.tarjeta-restaurante:hover {
  box-shadow: var(--shadow-soft-hover), var(--highlight-inset);
  border-color: var(--color-secondary);
}

.tarjeta-restaurante h2 {
  font-size: 1.1rem;
  margin-bottom: var(--space-2);
}

.descripcion {
  color: var(--text-secondary);
  font-size: 0.9rem;
  margin-bottom: var(--space-3);
}

.fecha {
  color: var(--text-tertiary);
  font-size: 0.8rem;
}

.menu-items {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  width: 100%;
}

.menu-item-row {
  display: grid;
  grid-template-columns: 1fr auto auto;
  gap: var(--space-2);
  align-items: center;
}
</style>
