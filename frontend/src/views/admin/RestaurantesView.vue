<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  crearRestaurante,
  listarRestaurantes,
  type MenuItemCreate,
  type Restaurante,
} from '../../api/restaurantes'
import { useAuthStore } from '../../stores/auth'

const router = useRouter()
const auth = useAuthStore()

const restaurantes = ref<Restaurante[]>([])
const cargando = ref(true)
const dialogoAbierto = ref(false)
const guardando = ref(false)

const form = reactive({
  nombre: '',
  descripcion: '',
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
  <div class="page">
    <header class="encabezado">
      <div>
        <h1>Restaurantes</h1>
        <p class="subtitulo">{{ auth.usuario?.nombre }} · administrador general</p>
      </div>
      <div class="acciones">
        <el-button type="primary" @click="abrirDialogo">Nuevo restaurante</el-button>
        <el-button @click="cerrarSesion">Salir</el-button>
      </div>
    </header>

    <el-table v-loading="cargando" :data="restaurantes" @row-click="(r) => irADetalle(r.id)">
      <el-table-column prop="nombre" label="Nombre" />
      <el-table-column prop="descripcion" label="Descripción" />
      <el-table-column label="Creado">
        <template #default="{ row }">{{ new Date(row.created_at).toLocaleDateString() }}</template>
      </el-table-column>
    </el-table>

    <el-empty v-if="!cargando && restaurantes.length === 0" description="Todavía no hay restaurantes" />

    <el-dialog v-model="dialogoAbierto" title="Nuevo restaurante" width="520px">
      <el-form :model="form" label-position="top">
        <el-form-item label="Nombre">
          <el-input v-model="form.nombre" />
        </el-form-item>
        <el-form-item label="Descripción">
          <el-input v-model="form.descripcion" type="textarea" :rows="2" />
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
.page {
  max-width: 960px;
  margin: 0 auto;
  padding: 2.5rem 1.5rem;
}

.encabezado {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1.5rem;
}

.subtitulo {
  color: #909399;
  font-size: 0.9rem;
}

.acciones {
  display: flex;
  gap: 0.5rem;
}

:deep(.el-table__row) {
  cursor: pointer;
}

.menu-items {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  width: 100%;
}

.menu-item-row {
  display: grid;
  grid-template-columns: 1fr auto auto;
  gap: 0.5rem;
  align-items: center;
}
</style>
