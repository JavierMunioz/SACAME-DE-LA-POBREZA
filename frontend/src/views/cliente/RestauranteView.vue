<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Minus, Plus, Van } from '@element-plus/icons-vue'
import { obtenerRestaurante, type MenuItem, type RestauranteConMenu } from '../../api/restaurantes'
import {
  consultarDisponibilidad,
  crearReserva,
  type MesaDisponibilidad,
} from '../../api/reservas'
import { crearPedidoDomicilio } from '../../api/pedidos'
import { useAuthStore } from '../../stores/auth'
import { imagenComida } from '../../utils/imagenesComida'
import { agruparMenuPorCategoria } from '../../utils/menuCategorias'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
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
  personas: 2,
})

const mesasFiltradas = computed(() =>
  mesas.value.filter((m) => m.capacidad >= form.personas),
)

const gruposMenu = computed(() =>
  restaurante.value ? agruparMenuPorCategoria(restaurante.value.menu) : [],
)

// Carrito de domicilio: menu_item_id -> cantidad. Vive solo en memoria,
// nada compartido en vivo (a diferencia del carrito de mesa, acá pide
// una sola persona, no hace falta websocket).
const carritoDomicilio = reactive<Record<number, number>>({})

const itemsCarrito = computed(() =>
  Object.entries(carritoDomicilio)
    .filter(([, cantidad]) => cantidad > 0)
    .map(([id, cantidad]) => {
      const item = restaurante.value?.menu.find((m) => m.id === Number(id))
      return item ? { item, cantidad } : null
    })
    .filter((x): x is { item: MenuItem; cantidad: number } => x !== null),
)

const totalItemsCarrito = computed(() =>
  itemsCarrito.value.reduce((acc, x) => acc + x.cantidad, 0),
)

const totalPrecioCarrito = computed(() =>
  itemsCarrito.value.reduce((acc, x) => acc + Number(x.item.precio) * x.cantidad, 0),
)

function agregarAlCarrito(itemId: number) {
  if (!auth.token) {
    router.push(`/login?redirect=${encodeURIComponent(route.fullPath)}`)
    return
  }
  carritoDomicilio[itemId] = (carritoDomicilio[itemId] ?? 0) + 1
}

function quitarDelCarrito(itemId: number) {
  carritoDomicilio[itemId] = Math.max(0, (carritoDomicilio[itemId] ?? 0) - 1)
}

const dialogoDomicilioAbierto = ref(false)
const enviandoDomicilio = ref(false)
const formDomicilio = reactive({ direccion: '', telefono: '' })

function abrirCheckoutDomicilio() {
  if (!auth.token) {
    router.push(`/login?redirect=${encodeURIComponent(route.fullPath)}`)
    return
  }
  dialogoDomicilioAbierto.value = true
}

async function confirmarPedidoDomicilio() {
  if (!formDomicilio.direccion.trim()) {
    ElMessage.warning('La dirección de entrega es obligatoria')
    return
  }
  enviandoDomicilio.value = true
  try {
    const pedido = await crearPedidoDomicilio({
      restauranteId: restauranteId,
      canal: 'domicilio_interno',
      direccionEntrega: formDomicilio.direccion,
      telefonoEntrega: formDomicilio.telefono || undefined,
      items: itemsCarrito.value.map((x) => ({ menu_item_id: x.item.id, cantidad: x.cantidad })),
    })
    dialogoDomicilioAbierto.value = false
    Object.keys(carritoDomicilio).forEach((k) => delete carritoDomicilio[Number(k)])
    ElMessage.success('Pedido enviado, te avisamos cuando salga')
    router.push(`/cliente/pedidos/${pedido.id}/seguimiento`)
  } catch {
    ElMessage.error('No se pudo enviar el pedido')
  } finally {
    enviandoDomicilio.value = false
  }
}

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

// Ninguna reserva de último minuto: cocina/mesero necesitan margen real
// para prepararse (regla real del negocio, no un límite técnico).
const HORAS_MINIMAS_ANTICIPACION = 2

async function reservar(mesa: MesaDisponibilidad) {
  // Reservar necesita identidad (para saludar por nombre al escanear el
  // QR); pedir sin reserva no la necesita. Frenamos acá, no antes.
  if (!auth.token) {
    router.push(`/login?redirect=${encodeURIComponent(route.fullPath)}`)
    return
  }
  const inicioDate = new Date(`${form.fecha}T${form.hora}:00`)
  const limite = new Date(Date.now() + HORAS_MINIMAS_ANTICIPACION * 60 * 60 * 1000)
  if (inicioDate < limite) {
    ElMessage.error(`Las reservas deben hacerse con al menos ${HORAS_MINIMAS_ANTICIPACION} horas de anticipación`)
    return
  }
  reservando.value = mesa.mesa_id
  try {
    await crearReserva({ mesa_id: mesa.mesa_id, inicio: inicioDate.toISOString() })
    ElMessage.success(`Mesa ${mesa.numero} reservada. Llegá 15 min antes.`)
    await buscarDisponibilidad()
  } catch (e: unknown) {
    const status = (e as { response?: { status?: number } })?.response?.status
    if (status === 409) ElMessage.error('Esa mesa ya se reservó, elegí otra')
    else if (status === 422)
      ElMessage.error(`Las reservas deben hacerse con al menos ${HORAS_MINIMAS_ANTICIPACION} horas de anticipación`)
    else ElMessage.error('No se pudo reservar')
  } finally {
    reservando.value = null
  }
}

function volver() {
  router.push('/cliente')
}

function irAMenu() {
  document.getElementById('menu')?.scrollIntoView({ behavior: 'smooth' })
}

function irAReservar() {
  document.getElementById('reservar')?.scrollIntoView({ behavior: 'smooth' })
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
    <header class="encabezado-pagina">
      <button type="button" class="volver" @click="volver">← Volver a restaurantes</button>
    </header>

    <div v-if="cargando" class="contenido">
      <el-skeleton animated :rows="6" />
    </div>

    <main v-else-if="restaurante" class="contenido">
      <div class="hero-restaurante">
        <img
          :src="imagenComida(restauranteId, 1400, 420)"
          :alt="restaurante.nombre"
          class="hero-restaurante-imagen"
        />
        <div class="hero-restaurante-overlay">
          <h1>{{ restaurante.nombre }}</h1>
          <p v-if="restaurante.descripcion" class="descripcion">{{ restaurante.descripcion }}</p>
          <div class="hero-restaurante-acciones">
            <el-button type="primary" size="large" @click="irAReservar">Reservar mesa</el-button>
            <el-button size="large" class="boton-outline-claro" @click="irAMenu">Ver menú</el-button>
            <el-button size="large" class="boton-outline-claro" @click="irAMenu">
              <el-icon :size="16" style="margin-right: 6px"><Van /></el-icon>
              Pedir domicilio
            </el-button>
          </div>
        </div>
      </div>

      <div class="layout-detalle">
        <section id="menu" class="columna-menu">
          <h2>Menú</h2>
          <el-empty v-if="restaurante.menu.length === 0" description="Sin platos todavía" />
          <template v-else>
            <div v-for="grupo in gruposMenu" :key="grupo.categoria?.id ?? 'otros'" class="grupo-categoria">
              <h3 v-if="gruposMenu.length > 1" class="titulo-categoria">
                {{ grupo.categoria?.nombre ?? 'Otros' }}
              </h3>
              <ul class="lista-menu">
                <li v-for="item in grupo.items" :key="item.id">
                  <img :src="imagenComida(item.id, 200, 200)" :alt="item.nombre" class="imagen-plato" />
                  <div class="info-plato">
                    <p class="nombre-plato">{{ item.nombre }}</p>
                    <p v-if="item.descripcion" class="descripcion-plato">{{ item.descripcion }}</p>
                    <div class="fila-precio-agregar">
                      <span class="precio">${{ Number(item.precio).toLocaleString('es-CO') }}</span>
                      <div class="stepper-plato">
                        <button
                          v-if="carritoDomicilio[item.id]"
                          type="button"
                          class="boton-stepper"
                          @click="quitarDelCarrito(item.id)"
                        >
                          <el-icon :size="14"><Minus /></el-icon>
                        </button>
                        <span v-if="carritoDomicilio[item.id]" class="cantidad-stepper">
                          {{ carritoDomicilio[item.id] }}
                        </span>
                        <button type="button" class="boton-stepper" @click="agregarAlCarrito(item.id)">
                          <el-icon :size="14"><Plus /></el-icon>
                        </button>
                      </div>
                    </div>
                  </div>
                </li>
              </ul>
            </div>
          </template>
        </section>

        <aside id="reservar" class="columna-reserva">
          <div class="tarjeta-reserva card-soft">
            <h3>Reservar mesa</h3>
            <label class="campo-reserva">
              <span class="label-mono">Fecha</span>
              <el-date-picker
                v-model="form.fecha"
                type="date"
                value-format="YYYY-MM-DD"
                size="large"
                style="width: 100%"
              />
            </label>
            <label class="campo-reserva">
              <span class="label-mono">Hora</span>
              <el-time-select
                v-model="form.hora"
                start="11:00"
                end="23:00"
                step="00:30"
                size="large"
                style="width: 100%"
              />
            </label>
            <label class="campo-reserva">
              <span class="label-mono">Personas</span>
              <el-input-number v-model="form.personas" :min="1" :max="20" size="large" style="width: 100%" />
            </label>
            <el-button
              type="primary"
              size="large"
              class="boton-disponibilidad"
              :loading="buscando"
              @click="buscarDisponibilidad"
            >
              Ver disponibilidad
            </el-button>

            <el-empty
              v-if="busquedaHecha && !buscando && mesasFiltradas.length === 0"
              description="No hay mesas para ese horario y cantidad de personas"
              :image-size="48"
            />

            <div v-if="mesasFiltradas.length > 0" class="lista-mesas">
              <div v-for="m in mesasFiltradas" :key="m.mesa_id" class="fila-mesa">
                <div>
                  <p class="numero-mesa">Mesa {{ m.numero }}</p>
                  <p class="capacidad">{{ m.capacidad }} personas</p>
                </div>
                <el-button
                  v-if="m.disponible"
                  type="primary"
                  size="small"
                  :loading="reservando === m.mesa_id"
                  @click="reservar(m)"
                >
                  Reservar
                </el-button>
                <el-tag v-else type="info" round>Ocupada</el-tag>
              </div>
            </div>
          </div>
        </aside>
      </div>
    </main>

    <div v-if="totalItemsCarrito > 0" class="barra-carrito">
      <div class="barra-carrito-info">
        <el-icon :size="18"><Van /></el-icon>
        <span>{{ totalItemsCarrito }} {{ totalItemsCarrito === 1 ? 'ítem' : 'ítems' }}</span>
        <span class="barra-carrito-total">${{ totalPrecioCarrito.toLocaleString('es-CO') }}</span>
      </div>
      <el-button type="primary" size="large" @click="abrirCheckoutDomicilio">
        Pedir domicilio
      </el-button>
    </div>

    <el-dialog v-model="dialogoDomicilioAbierto" title="Confirmar domicilio" width="420px">
      <div class="resumen-carrito">
        <div v-for="x in itemsCarrito" :key="x.item.id" class="fila-resumen-carrito">
          <span>{{ x.cantidad }}× {{ x.item.nombre }}</span>
          <span>${{ (Number(x.item.precio) * x.cantidad).toLocaleString('es-CO') }}</span>
        </div>
        <div class="fila-resumen-carrito fila-resumen-total">
          <span>Total</span>
          <span>${{ totalPrecioCarrito.toLocaleString('es-CO') }}</span>
        </div>
      </div>
      <el-form :model="formDomicilio" label-position="top">
        <el-form-item label="Dirección de entrega">
          <el-input v-model="formDomicilio.direccion" size="large" placeholder="Calle, número, barrio" />
        </el-form-item>
        <el-form-item label="Teléfono de contacto (opcional)">
          <el-input v-model="formDomicilio.telefono" size="large" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogoDomicilioAbierto = false">Cancelar</el-button>
        <el-button type="primary" :loading="enviandoDomicilio" @click="confirmarPedidoDomicilio">
          Confirmar pedido
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.pagina {
  min-height: 100dvh;
}

.encabezado-pagina {
  padding: var(--space-4) var(--space-6);
  background: var(--surface-raised);
  border-bottom: 1px solid var(--border-subtle);
  position: sticky;
  top: 0;
  z-index: 10;
}

.volver {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 0.875rem;
  color: var(--text-secondary);
  font-weight: 500;
  padding: 0;
}

.volver:hover {
  color: var(--text-primary);
}

.contenido {
  max-width: 1080px;
  margin: 0 auto;
  padding: var(--space-6) var(--space-6) var(--space-16);
}

.hero-restaurante {
  position: relative;
  border-radius: var(--radius-lg);
  overflow: hidden;
  margin-bottom: var(--space-8);
  min-height: 320px;
  display: flex;
  align-items: flex-end;
}

.hero-restaurante-imagen {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.hero-restaurante-overlay {
  position: relative;
  width: 100%;
  padding: var(--space-8);
  background: linear-gradient(180deg, transparent 0%, rgba(0, 0, 0, 0.75) 70%);
  color: white;
}

.hero-restaurante-overlay h1 {
  color: white;
  font-size: 2rem;
  margin-bottom: var(--space-2);
}

.hero-restaurante-overlay .descripcion {
  color: rgba(255, 255, 255, 0.85);
  max-width: 60ch;
  margin-bottom: var(--space-5);
}

.hero-restaurante-acciones {
  display: flex;
  gap: var(--space-3);
}

.boton-outline-claro {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.4);
  color: white;
}

.boton-outline-claro:hover {
  background: rgba(255, 255, 255, 0.18);
  border-color: white;
  color: white;
}

.layout-detalle {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--space-8);
  align-items: start;
}

@media (min-width: 860px) {
  .layout-detalle {
    grid-template-columns: 1.6fr 1fr;
  }
}

.columna-menu h2 {
  margin-bottom: var(--space-4);
}

.grupo-categoria + .grupo-categoria {
  margin-top: var(--space-8);
}

.titulo-categoria {
  font-family: var(--font-display);
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: var(--space-3);
}

.lista-menu {
  list-style: none;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.lista-menu li {
  display: flex;
  gap: var(--space-4);
  padding: var(--space-3);
  background: var(--surface-raised);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-soft), var(--highlight-inset);
}

.imagen-plato {
  width: 72px;
  height: 72px;
  border-radius: var(--radius-sm);
  object-fit: cover;
  flex-shrink: 0;
}

.info-plato {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  flex: 1;
}

.nombre-plato {
  font-weight: 500;
}

.descripcion-plato {
  color: var(--text-tertiary);
  font-size: 0.85rem;
}

.fila-precio-agregar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.precio {
  color: var(--color-secondary);
  font-weight: 600;
  font-size: 0.9rem;
}

.stepper-plato {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.boton-stepper {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border-radius: var(--radius-full);
  border: 1px solid var(--border-default);
  background: var(--surface-raised);
  color: var(--color-secondary);
  cursor: pointer;
  flex-shrink: 0;
}

.boton-stepper:hover {
  background: var(--color-secondary-soft);
}

.cantidad-stepper {
  min-width: 1.2em;
  text-align: center;
  font-weight: 700;
  font-family: var(--font-mono);
}

.barra-carrito {
  position: sticky;
  bottom: 0;
  z-index: 15;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background: var(--color-primary);
  color: white;
  box-shadow: var(--shadow-lg);
}

.barra-carrito-info {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: 0.9rem;
  min-width: 0;
}

.barra-carrito-total {
  font-weight: 700;
  font-family: var(--font-mono);
}

.resumen-carrito {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin-bottom: var(--space-5);
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--border-subtle);
}

.fila-resumen-carrito {
  display: flex;
  justify-content: space-between;
  gap: var(--space-3);
  font-size: 0.9rem;
}

.fila-resumen-total {
  font-weight: 700;
  padding-top: var(--space-2);
  border-top: 1px dashed var(--border-default);
}

.columna-reserva {
  position: sticky;
  top: calc(64px + var(--space-6));
}

.tarjeta-reserva {
  padding: var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.tarjeta-reserva h3 {
  margin-bottom: var(--space-1);
}

.campo-reserva {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.boton-disponibilidad {
  width: 100%;
  margin-top: var(--space-2);
  font-weight: 600;
}

.lista-mesas {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin-top: var(--space-2);
}

.fila-mesa {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3);
  background: var(--surface-muted);
  border-radius: var(--radius-sm);
}

.numero-mesa {
  font-weight: 600;
  font-size: 0.9rem;
}

.capacidad {
  color: var(--text-tertiary);
  font-size: 0.8rem;
}
</style>
