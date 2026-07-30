<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { listarRestaurantes, type Restaurante } from '../../api/restaurantes'
import { useAuthStore } from '../../stores/auth'

const restaurantes = ref<Restaurante[]>([])
const cargando = ref(true)
const router = useRouter()
const auth = useAuthStore()

async function cargar() {
  cargando.value = true
  restaurantes.value = await listarRestaurantes()
  cargando.value = false
}

function verRestaurante(id: number) {
  router.push(`/cliente/restaurantes/${id}`)
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
        <p class="subtitulo">Hola, {{ auth.usuario?.nombre }}</p>
      </div>
      <el-button @click="cerrarSesion">Salir</el-button>
    </header>

    <el-empty v-if="!cargando && restaurantes.length === 0" description="Todavía no hay restaurantes afiliados" />

    <div v-loading="cargando" class="grid-restaurantes">
      <el-card
        v-for="r in restaurantes"
        :key="r.id"
        class="tarjeta-restaurante"
        @click="verRestaurante(r.id)"
      >
        <h2>{{ r.nombre }}</h2>
        <p>{{ r.descripcion }}</p>
      </el-card>
    </div>
  </div>
</template>

<style scoped>
.page {
  max-width: 900px;
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

.grid-restaurantes {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 1rem;
}

.tarjeta-restaurante {
  cursor: pointer;
}

.tarjeta-restaurante h2 {
  font-size: 1.1rem;
  margin-bottom: 0.25rem;
}

.tarjeta-restaurante p {
  color: #606266;
  font-size: 0.9rem;
}
</style>
