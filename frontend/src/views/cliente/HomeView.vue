<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { listarRestaurantes, type Restaurante } from '../../api/restaurantes'
import { useAuthStore } from '../../stores/auth'

const restaurantes = ref<Restaurante[]>([])
const cargando = ref(true)
const router = useRouter()
const auth = useAuthStore()

const estaLogueado = computed(() => !!auth.usuario)

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
    <div class="fondo-hero" aria-hidden="true"></div>
    <header class="encabezado glass-panel">
      <div class="marca">
        <span class="marca-icono">S</span>
        <span class="marca-nombre">Sacame de la Pobreza</span>
      </div>
      <div class="acciones-header">
        <span v-if="estaLogueado" class="saludo">Hola, {{ auth.usuario?.nombre }}</span>
        <el-button v-if="estaLogueado" @click="cerrarSesion">Salir</el-button>
        <router-link v-else to="/login">
          <el-button>Iniciar sesión</el-button>
        </router-link>
      </div>
    </header>

    <main class="contenido">
      <div class="titulo-seccion">
        <h1>Restaurantes</h1>
        <p class="subtitulo">Elegí dónde comer y reservá en segundos.</p>
      </div>

      <div v-if="cargando" class="grid-restaurantes">
        <div v-for="i in 3" :key="i" class="tarjeta-skeleton">
          <el-skeleton animated>
            <template #template>
              <el-skeleton-item variant="text" style="width: 60%; height: 20px" />
              <el-skeleton-item variant="text" style="width: 90%; margin-top: 10px" />
              <el-skeleton-item variant="text" style="width: 40%; margin-top: 10px" />
            </template>
          </el-skeleton>
        </div>
      </div>

      <div v-else-if="restaurantes.length === 0" class="estado-vacio">
        <p class="estado-vacio-titulo">Todavía no hay restaurantes afiliados</p>
        <p class="estado-vacio-texto">Volvé a intentarlo más tarde.</p>
      </div>

      <div v-else class="grid-restaurantes">
        <button
          v-for="r in restaurantes"
          :key="r.id"
          type="button"
          class="tarjeta-restaurante"
          @click="verRestaurante(r.id)"
        >
          <h2>{{ r.nombre }}</h2>
          <p v-if="r.descripcion" class="descripcion">{{ r.descripcion }}</p>
          <span class="ver-mas">Ver menú y reservar →</span>
        </button>
      </div>
    </main>
  </div>
</template>

<style scoped>
.pagina {
  position: relative;
  min-height: 100dvh;
}

.fondo-hero {
  position: fixed;
  inset: 0;
  z-index: -1;
  background:
    radial-gradient(circle at 10% 0%, rgba(79, 70, 229, 0.1), transparent 40%),
    radial-gradient(circle at 90% 15%, rgba(24, 24, 27, 0.06), transparent 40%);
  pointer-events: none;
}

.encabezado {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-4) var(--space-6);
  border-bottom: 1px solid var(--border-subtle);
  position: sticky;
  top: 0;
  z-index: 10;
}

.marca {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.marca-icono {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border-radius: var(--radius-sm);
  background: var(--color-primary);
  color: white;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 0.85rem;
}

.marca-nombre {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 0.9rem;
  display: none;
}

@media (min-width: 640px) {
  .marca-nombre {
    display: inline;
  }
}

.acciones-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.saludo {
  font-size: 0.875rem;
  color: var(--text-secondary);
  display: none;
}

@media (min-width: 480px) {
  .saludo {
    display: inline;
  }
}

.contenido {
  max-width: 720px;
  margin: 0 auto;
  padding: var(--space-8) var(--space-6) var(--space-16);
}

.titulo-seccion {
  margin-bottom: var(--space-8);
}

.titulo-seccion h1 {
  font-size: 1.75rem;
  margin-bottom: var(--space-2);
}

.subtitulo {
  color: var(--text-secondary);
  font-size: 1rem;
}

.grid-restaurantes {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--space-4);
}

@media (min-width: 560px) {
  .grid-restaurantes {
    grid-template-columns: repeat(2, 1fr);
  }
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
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.tarjeta-restaurante:hover {
  box-shadow: var(--shadow-soft-hover), var(--highlight-inset);
  border-color: var(--color-secondary);
}

.tarjeta-restaurante h2 {
  font-size: 1.15rem;
}

.tarjeta-restaurante .descripcion {
  color: var(--text-secondary);
  font-size: 0.9rem;
  line-height: 1.5;
}

.ver-mas {
  margin-top: var(--space-2);
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-secondary);
}

.tarjeta-skeleton {
  background: var(--surface-raised);
  border: 1px solid var(--border-subtle);
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
</style>
