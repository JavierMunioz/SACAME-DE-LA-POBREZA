<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Grid, List, Search } from '@element-plus/icons-vue'
import { listarRestaurantes, type Restaurante } from '../../api/restaurantes'
import { useAuthStore } from '../../stores/auth'
import { imagenComida } from '../../utils/imagenesComida'

const restaurantes = ref<Restaurante[]>([])
const busqueda = ref('')
const categoriaActiva = ref('Todos')
const dialogoComoFuncionaAbierto = ref(false)
const cargando = ref(true)
const router = useRouter()
const auth = useAuthStore()

const estaLogueado = computed(() => !!auth.usuario)

// Favoritos reales guardados en localStorage — no hace falta cuenta para
// marcar uno, es un gusto de dispositivo, no un dato de servidor.
const CLAVE_FAVORITOS = 'restaurantes-favoritos'
const favoritos = reactive<Set<number>>(
  new Set(JSON.parse(localStorage.getItem(CLAVE_FAVORITOS) ?? '[]')),
)

function alternarFavorito(id: number, evento: MouseEvent) {
  evento.stopPropagation()
  if (favoritos.has(id)) favoritos.delete(id)
  else favoritos.add(id)
  localStorage.setItem(CLAVE_FAVORITOS, JSON.stringify([...favoritos]))
}

// Categorías reales de los restaurantes cargados, no una lista inventada.
const categorias = computed(() => {
  const set = new Set(restaurantes.value.map((r) => r.categoria).filter((c): c is string => !!c))
  return ['Todos', ...set]
})

const restaurantesFiltrados = computed(() => {
  const q = busqueda.value.trim().toLowerCase()
  return restaurantes.value.filter((r) => {
    const coincideCategoria = categoriaActiva.value === 'Todos' || r.categoria === categoriaActiva.value
    const coincideBusqueda =
      !q || r.nombre.toLowerCase().includes(q) || (r.descripcion ?? '').toLowerCase().includes(q)
    return coincideCategoria && coincideBusqueda
  })
})

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
    <header class="encabezado">
      <div class="marca">
        <span class="marca-icono">S</span>
        <span class="marca-nombre">Sacame de la Pobreza</span>
      </div>
      <nav class="nav-principal">
        <span class="nav-link nav-link--activo">
          <el-icon :size="16"><Grid /></el-icon>
          Inicio
        </span>
        <button type="button" class="nav-link" @click="dialogoComoFuncionaAbierto = true">
          ¿Cómo funciona?
        </button>
        <router-link v-if="estaLogueado" to="/cliente/pedidos" class="nav-link">
          <el-icon :size="16"><List /></el-icon>
          Mis pedidos
        </router-link>
      </nav>
      <div class="acciones-header">
        <span v-if="estaLogueado" class="saludo">Hola, {{ auth.usuario?.nombre }}</span>
        <el-button v-if="estaLogueado" @click="cerrarSesion">Salir</el-button>
        <router-link v-else to="/login">
          <el-button type="primary">Iniciar sesión</el-button>
        </router-link>
      </div>
    </header>

    <main class="contenido">
      <div class="titulo-seccion">
        <h1>Restaurantes cerca de ti</h1>
        <p class="subtitulo">Reservá tu mesa y pedí desde tu celular en segundos.</p>
        <el-input
          v-model="busqueda"
          size="large"
          placeholder="Buscar restaurante o tipo de cocina..."
          class="buscador"
          clearable
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>

        <div v-if="categorias.length > 1" class="chips-categoria">
          <button
            v-for="c in categorias"
            :key="c"
            type="button"
            class="chip"
            :class="{ 'chip--activo': categoriaActiva === c }"
            @click="categoriaActiva = c"
          >
            {{ c }}
          </button>
        </div>
      </div>

      <div v-if="cargando" class="grid-restaurantes">
        <div v-for="i in 4" :key="i" class="tarjeta-skeleton">
          <el-skeleton animated>
            <template #template>
              <el-skeleton-item variant="image" style="height: 160px" />
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

      <div v-else-if="restaurantesFiltrados.length === 0" class="estado-vacio">
        <p class="estado-vacio-titulo">Sin resultados</p>
        <p class="estado-vacio-texto">Probá con otro nombre, categoría o búsqueda.</p>
      </div>

      <div v-else class="grid-restaurantes">
        <button
          v-for="r in restaurantesFiltrados"
          :key="r.id"
          type="button"
          class="tarjeta-restaurante"
          @click="verRestaurante(r.id)"
        >
          <div class="tarjeta-restaurante-imagen">
            <img :src="imagenComida(r.id, 400, 260)" :alt="r.nombre" loading="lazy" />
            <span v-if="r.mesas_disponibles" class="badge-disponible">
              <span class="punto-verde" /> Mesas disponibles
            </span>
            <button
              type="button"
              class="boton-favorito"
              :class="{ 'boton-favorito--activo': favoritos.has(r.id) }"
              :aria-label="favoritos.has(r.id) ? 'Quitar de favoritos' : 'Agregar a favoritos'"
              @click="alternarFavorito(r.id, $event)"
            >
              ♥
            </button>
          </div>
          <div class="tarjeta-restaurante-cuerpo">
            <h2>{{ r.nombre }}</h2>
            <p class="meta-restaurante">
              <span v-if="r.categoria">{{ r.categoria }}</span>
              <span v-if="r.descripcion" class="descripcion">{{ r.descripcion }}</span>
            </p>
            <span class="ver-mas">Ver menú y reservar →</span>
          </div>
        </button>
      </div>

      <div class="franja-features card-soft">
        <div class="feature-item">
          <p class="feature-titulo">Reservá en segundos</p>
          <p class="feature-texto">Sin llamadas, sin esperas.</p>
        </div>
        <div class="feature-item">
          <p class="feature-titulo">Pedí desde tu celular</p>
          <p class="feature-texto">Escaneá el QR y pedís directo, sin cuenta.</p>
        </div>
        <div class="feature-item">
          <p class="feature-titulo">Carrito en vivo</p>
          <p class="feature-texto">Toda la mesa ve lo mismo, en tiempo real.</p>
        </div>
        <div class="feature-item">
          <p class="feature-titulo">Cocina conectada</p>
          <p class="feature-texto">Tu pedido llega a cocina apenas se confirma.</p>
        </div>
      </div>
    </main>

    <el-dialog v-model="dialogoComoFuncionaAbierto" title="¿Cómo funciona?" width="420px">
      <ol class="pasos-como-funciona">
        <li>
          <strong>Elegí un restaurante</strong>
          <p>Buscá o filtrá por categoría y entrá a ver el menú.</p>
        </li>
        <li>
          <strong>Reservá o escaneá el QR de tu mesa</strong>
          <p>Con cuenta podés reservar con anticipación. Sin cuenta, escaneás el QR al llegar.</p>
        </li>
        <li>
          <strong>Pedí y seguí tu orden</strong>
          <p>Tu pedido llega directo a cocina. Si van varios, todos ven el mismo carrito en vivo.</p>
        </li>
      </ol>
    </el-dialog>
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
  gap: var(--space-6);
  padding: var(--space-4) var(--space-6);
  background: var(--surface-raised);
  border-bottom: 1px solid var(--border-subtle);
  position: sticky;
  top: 0;
  z-index: 10;
}

.marca {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-shrink: 0;
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

.nav-principal {
  display: none;
  align-items: center;
  gap: var(--space-5);
  flex: 1;
  justify-content: center;
}

@media (min-width: 780px) {
  .nav-principal {
    display: flex;
  }
}

.nav-link {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-secondary);
  background: none;
  border: none;
  cursor: pointer;
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-sm);
  text-decoration: none;
}

.nav-link:hover {
  color: var(--text-primary);
}

.nav-link--activo {
  background: var(--color-secondary-soft);
  color: var(--color-secondary);
}

.acciones-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-shrink: 0;
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
  max-width: 1160px;
  margin: 0 auto;
  padding: var(--space-8) var(--space-6) var(--space-16);
}

.titulo-seccion {
  margin-bottom: var(--space-8);
}

.titulo-seccion h1 {
  font-size: 2.25rem;
  margin-bottom: var(--space-2);
}

.subtitulo {
  color: var(--text-secondary);
  font-size: 1rem;
  margin-bottom: var(--space-5);
}

.buscador {
  max-width: 560px;
  margin-bottom: var(--space-4);
}

.buscador :deep(.el-input__wrapper) {
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-md);
}

.chips-categoria {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.chip {
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-full);
  border: 1px solid var(--border-default);
  background: var(--surface-raised);
  color: var(--text-secondary);
  font-size: 0.825rem;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-standard);
}

.chip:hover {
  border-color: var(--color-secondary);
}

.chip--activo {
  background: var(--color-secondary-soft);
  border-color: var(--color-secondary);
  color: var(--color-secondary);
}

.franja-features {
  margin-top: var(--space-10);
  padding: var(--space-6);
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-5);
}

@media (min-width: 720px) {
  .franja-features {
    grid-template-columns: repeat(4, 1fr);
  }
}

.feature-titulo {
  font-weight: 600;
  font-size: 0.9rem;
  margin-bottom: var(--space-1);
}

.feature-texto {
  color: var(--text-secondary);
  font-size: 0.825rem;
  line-height: 1.5;
}

/* Grilla uniforme de 4 columnas, todas las tarjetas del mismo tamaño. */
.grid-restaurantes {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-5);
}

@media (min-width: 720px) {
  .grid-restaurantes {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (min-width: 1040px) {
  .grid-restaurantes {
    grid-template-columns: repeat(4, 1fr);
  }
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
  position: relative;
  height: 160px;
  overflow: hidden;
  background: var(--surface-muted);
}

.tarjeta-restaurante-imagen img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.badge-disponible {
  position: absolute;
  top: var(--space-3);
  left: var(--space-3);
  display: flex;
  align-items: center;
  gap: var(--space-1);
  padding: 4px var(--space-3);
  background: var(--surface-raised);
  border-radius: var(--radius-full);
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--text-primary);
}

.punto-verde {
  width: 6px;
  height: 6px;
  border-radius: var(--radius-full);
  background: var(--color-success);
}

.boton-favorito {
  position: absolute;
  top: var(--space-3);
  right: var(--space-3);
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  border-radius: var(--radius-full);
  border: none;
  background: var(--surface-raised);
  color: var(--text-tertiary);
  cursor: pointer;
  font-size: 1rem;
  line-height: 1;
  transition: color var(--duration-fast) var(--ease-standard);
}

.boton-favorito--activo {
  color: var(--color-danger);
}

.tarjeta-restaurante-cuerpo {
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.tarjeta-restaurante h2 {
  font-size: 1rem;
}

.meta-restaurante {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.meta-restaurante span:first-child {
  color: var(--color-secondary);
  font-weight: 600;
}

.ver-mas {
  margin-top: var(--space-2);
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--color-secondary);
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

.pasos-como-funciona {
  list-style: none;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  counter-reset: paso;
}

.pasos-como-funciona li {
  padding-left: var(--space-8);
  position: relative;
}

.pasos-como-funciona li::before {
  counter-increment: paso;
  content: counter(paso);
  position: absolute;
  left: 0;
  top: 0;
  width: 24px;
  height: 24px;
  border-radius: var(--radius-full);
  background: var(--color-secondary-soft);
  color: var(--color-secondary);
  font-size: 0.75rem;
  font-weight: 700;
  display: grid;
  place-items: center;
}

.pasos-como-funciona strong {
  display: block;
  margin-bottom: var(--space-1);
  font-size: 0.9rem;
}

.pasos-como-funciona p {
  color: var(--text-secondary);
  font-size: 0.85rem;
  line-height: 1.5;
}
</style>
