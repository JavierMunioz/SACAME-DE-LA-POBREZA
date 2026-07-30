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

// No hay fotos reales de los restaurantes en el dominio todavía — se usa
// una imagen determinística (mismo restaurante = misma foto siempre) en
// vez de dejar la tarjeta sin imagen o inventar una URL falsa.
function imagenRestaurante(r: Restaurante, ancho: number, alto: number): string {
  return `https://picsum.photos/seed/restaurante-${r.id}/${ancho}/${alto}`
}

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
              <el-skeleton-item variant="image" style="height: 140px" />
              <el-skeleton-item variant="text" style="width: 60%; height: 20px; margin-top: 12px" />
              <el-skeleton-item variant="text" style="width: 40%; margin-top: 8px" />
            </template>
          </el-skeleton>
        </div>
      </div>

      <div v-else-if="restaurantes.length === 0" class="estado-vacio">
        <p class="estado-vacio-titulo">Todavía no hay restaurantes afiliados</p>
        <p class="estado-vacio-texto">Volvé a intentarlo más tarde.</p>
      </div>

      <div v-else class="bento-restaurantes">
        <button
          v-for="(r, i) in restaurantes"
          :key="r.id"
          type="button"
          class="tarjeta-restaurante"
          :class="{ 'tarjeta-restaurante--destacada': i === 0 }"
          @click="verRestaurante(r.id)"
        >
          <div class="tarjeta-restaurante-imagen">
            <img
              :src="imagenRestaurante(r, i === 0 ? 800 : 400, i === 0 ? 480 : 260)"
              :alt="r.nombre"
              loading="lazy"
            />
          </div>
          <div class="tarjeta-restaurante-cuerpo">
            <h2>{{ r.nombre }}</h2>
            <p v-if="r.descripcion" class="descripcion">{{ r.descripcion }}</p>
            <span class="ver-mas">Ver menú y reservar →</span>
          </div>
        </button>
      </div>
    </main>
  </div>
</template>

<style scoped>
.pagina {
  min-height: 100dvh;
  background: var(--surface-sunken);
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
  max-width: 960px;
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

/* Bento real: el primer restaurante ocupa una tarjeta grande a todo lo
   ancho (imagen más grande), el resto en una grilla de 2 columnas. */
.bento-restaurantes {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-5);
}

@media (max-width: 640px) {
  .bento-restaurantes {
    grid-template-columns: 1fr;
  }
}

.tarjeta-restaurante--destacada {
  grid-column: 1 / -1;
}

.tarjeta-restaurante--destacada .tarjeta-restaurante-imagen {
  height: 220px;
}

.tarjeta-restaurante {
  text-align: left;
  background: var(--surface-raised);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  overflow: hidden;
  cursor: pointer;
  box-shadow: var(--shadow-soft), var(--highlight-inset);
  transition:
    box-shadow var(--duration-base) var(--ease-standard),
    transform var(--duration-base) var(--ease-standard);
  display: flex;
  flex-direction: column;
  padding: 0;
}

.tarjeta-restaurante:hover {
  box-shadow: var(--shadow-soft-hover), var(--highlight-inset);
  transform: translateY(-2px);
}

.tarjeta-restaurante-imagen {
  height: 140px;
  overflow: hidden;
  background: var(--surface-muted);
}

.tarjeta-restaurante-imagen img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.tarjeta-restaurante-cuerpo {
  padding: var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
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

.tarjeta-skeleton {
  background: var(--surface-raised);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: var(--space-5);
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
