<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Bell, Check, InfoFilled, Search, ShoppingBag, Grid } from '@element-plus/icons-vue'
import {
  canjearQr,
  llamarMesero as llamarMeseroApi,
  obtenerUbicacion,
  ocuparMesa,
  unirseAMesa,
  urlWsCarrito,
  type MesaQrInfo,
  type SesionMesa,
} from '../api/mesas'
import { crearPedido } from '../api/pedidos'
import { useAuthStore } from '../stores/auth'
import { agruparMenuPorCategoria } from '../utils/menuCategorias'
import { imagenComida } from '../utils/imagenesComida'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const info = ref<MesaQrInfo | null>(null)
const cargando = ref(true)
const errorToken = ref(false)
const enviandoPedido = ref(false)

const sesion = ref<SesionMesa | null>(null)
const reclamando = ref(false)
const nombreInput = ref('')
const codigoInput = ref('')
const errorReclamo = ref('')

const busqueda = ref('')
const infoAbierta = ref(false)
const llamandoMesero = ref(false)
const meseroAvisado = ref(false)

// carrito: espejo local del carrito compartido — lo actualiza el
// WebSocket, no se muta a mano (así todos los dispositivos de la mesa
// ven siempre los mismos números).
const carrito = reactive<Record<number, number>>({})
const observaciones = reactive<Record<number, string>>({})

const esDueno = computed(() => !!sesion.value?.token_dueno)

let ws: WebSocket | null = null

function claveSesion(mesaId: number) {
  return `sesion-mesa-${mesaId}`
}

function leerSesionGuardada(mesaId: number): SesionMesa | null {
  const raw = localStorage.getItem(claveSesion(mesaId))
  if (!raw) return null
  try {
    return JSON.parse(raw) as SesionMesa
  } catch {
    return null
  }
}

function guardarSesion(s: SesionMesa) {
  localStorage.setItem(claveSesion(s.mesa_id), JSON.stringify(s))
}

function borrarSesion(mesaId: number) {
  localStorage.removeItem(claveSesion(mesaId))
}

function conectarCarritoEnVivo(mesaId: number, token: string) {
  desconectarCarritoEnVivo()
  ws = new WebSocket(urlWsCarrito(mesaId, token))
  ws.onmessage = (evento) => {
    const datos = JSON.parse(evento.data)
    if (datos.tipo !== 'carrito') return
    Object.keys(carrito).forEach((k) => delete carrito[Number(k)])
    for (const item of datos.items as { menu_item_id: number; cantidad: number; observaciones: string | null }[]) {
      carrito[item.menu_item_id] = item.cantidad
      if (item.observaciones) observaciones[item.menu_item_id] = item.observaciones
    }
  }
}

function desconectarCarritoEnVivo() {
  ws?.close()
  ws = null
}

function enviarCambioItem(menuItemId: number, cantidad: number) {
  if (!ws || ws.readyState !== WebSocket.OPEN) return
  ws.send(
    JSON.stringify({
      accion: 'set_item',
      menu_item_id: menuItemId,
      cantidad,
      observaciones: observaciones[menuItemId] || null,
    }),
  )
}

async function cargar() {
  if (auth.token && !auth.usuario) {
    try {
      await auth.cargarUsuario()
    } catch {
      auth.logout()
    }
  }

  const token = route.query.token as string | undefined
  if (!token) {
    errorToken.value = true
    cargando.value = false
    return
  }
  try {
    info.value = await canjearQr(token)
    const guardada = leerSesionGuardada(info.value.mesa_id)
    // Si la mesa no tiene ninguna sesión activa pero teníamos una guardada,
    // es de una visita anterior ya cerrada — no sirve, se descarta.
    sesion.value = info.value.requiere_codigo || guardada ? guardada : null
    if (!info.value.requiere_codigo && guardada) borrarSesion(info.value.mesa_id)
    if (sesion.value) conectarCarritoEnVivo(info.value.mesa_id, sesion.value.token)
  } catch {
    errorToken.value = true
  } finally {
    cargando.value = false
  }
}

// Si el restaurante configuró su ubicación real, hay que pedir permiso de
// geolocalización antes de ocupar (ver Brain.md: QR fotografiado y usado
// a distancia). Si el restaurante no la configuró, no se pide nada.
async function ubicacionParaOcupar(): Promise<{ lat: number; lng: number } | undefined> {
  if (!info.value?.requiere_ubicacion) return undefined
  const ubicacion = await obtenerUbicacion()
  if (!ubicacion) {
    errorReclamo.value =
      'Necesitamos tu ubicación para abrir la mesa. Activá la ubicación del navegador e intentá de nuevo.'
    throw new Error('sin-ubicacion')
  }
  return ubicacion
}

async function reclamarComoInvitado() {
  if (!info.value) return
  if (!nombreInput.value.trim()) {
    errorReclamo.value = 'Necesitamos tu nombre para abrir la mesa'
    return
  }
  await reclamar(async () => {
    const ubicacion = await ubicacionParaOcupar()
    return ocuparMesa(info.value!.mesa_id, route.query.token as string, {
      nombreInvitado: nombreInput.value,
      ...ubicacion,
    })
  })
}

async function reclamarComoClienteLogueado() {
  if (!info.value) return
  await reclamar(async () => {
    const ubicacion = await ubicacionParaOcupar()
    return ocuparMesa(info.value!.mesa_id, route.query.token as string, { ...ubicacion })
  })
}

async function confirmarLlegada() {
  if (!info.value?.reserva_propia) return
  await reclamar(async () => {
    const ubicacion = await ubicacionParaOcupar()
    return ocuparMesa(info.value!.mesa_id, route.query.token as string, {
      reservaId: info.value!.reserva_propia!.id,
      ...ubicacion,
    })
  })
}

async function unirseConCodigo() {
  if (!info.value) return
  if (codigoInput.value.trim().length !== 4) {
    errorReclamo.value = 'El código tiene 4 dígitos'
    return
  }
  await reclamar(() =>
    unirseAMesa(info.value!.mesa_id, route.query.token as string, codigoInput.value.trim()),
  )
}

async function reclamar(accion: () => Promise<SesionMesa>) {
  errorReclamo.value = ''
  reclamando.value = true
  try {
    const s = await accion()
    sesion.value = s
    guardarSesion(s)
    if (info.value) conectarCarritoEnVivo(info.value.mesa_id, s.token)
  } catch (e: unknown) {
    if (e instanceof Error && e.message === 'sin-ubicacion') {
      // el mensaje específico ya quedó seteado en ubicacionParaOcupar.
    } else {
      const respuesta = (e as { response?: { status?: number; data?: { detail?: string } } })
        ?.response
      errorReclamo.value =
        respuesta?.status === 403 && respuesta.data?.detail
          ? respuesta.data.detail
          : 'No se pudo completar la acción. Puede que alguien se te haya adelantado — recargá la página.'
    }
  } finally {
    reclamando.value = false
  }
}

function sumar(menuItemId: number) {
  enviarCambioItem(menuItemId, (carrito[menuItemId] ?? 0) + 1)
}

function restar(menuItemId: number) {
  if (!carrito[menuItemId]) return
  enviarCambioItem(menuItemId, carrito[menuItemId] - 1)
}

const menuFiltrado = computed(() => {
  if (!info.value) return []
  const q = busqueda.value.trim().toLowerCase()
  if (!q) return info.value.menu
  return info.value.menu.filter(
    (item) =>
      item.nombre.toLowerCase().includes(q) || (item.descripcion ?? '').toLowerCase().includes(q),
  )
})

const gruposMenu = computed(() => agruparMenuPorCategoria(menuFiltrado.value))

function claveGrupo(id: number | undefined): string {
  return id !== undefined ? `categoria-${id}` : 'categoria-otros'
}

function irACategoria(id: number | undefined) {
  document.getElementById(claveGrupo(id))?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

const totalItems = computed(() => Object.values(carrito).reduce((a, b) => a + b, 0))

const totalPrecio = computed(() => {
  if (!info.value) return 0
  return Object.entries(carrito).reduce((suma, [menuItemId, cantidad]) => {
    const item = info.value!.menu.find((m) => m.id === Number(menuItemId))
    return suma + (item ? Number(item.precio) * cantidad : 0)
  }, 0)
})

const itemsDelCarrito = computed(() => {
  if (!info.value) return []
  return Object.entries(carrito)
    .filter(([, cantidad]) => cantidad > 0)
    .map(([menuItemId, cantidad]) => {
      const item = info.value!.menu.find((m) => m.id === Number(menuItemId))
      return { id: Number(menuItemId), nombre: item?.nombre ?? '', cantidad, precio: item ? Number(item.precio) : 0 }
    })
})

async function enviarPedido() {
  if (!info.value || !sesion.value?.token_dueno) return
  enviandoPedido.value = true
  try {
    const items = Object.entries(carrito).map(([menuItemId, cantidad]) => ({
      menu_item_id: Number(menuItemId),
      cantidad,
      observaciones: observaciones[Number(menuItemId)] || undefined,
    }))
    await crearPedido(info.value.mesa_id, items, sesion.value.token_dueno)
    ElMessage.success('Pedido enviado a la cocina')
    Object.keys(carrito).forEach((k) => delete carrito[Number(k)])
    router.push('/cliente')
  } catch (e: unknown) {
    const status = (e as { response?: { status?: number } })?.response?.status
    if (status === 401 && info.value) {
      borrarSesion(info.value.mesa_id)
      sesion.value = null
      desconectarCarritoEnVivo()
      ElMessage.error('Tu sesión de mesa venció. Volvé a abrir o unirte a la mesa.')
    } else {
      ElMessage.error('No se pudo enviar el pedido')
    }
  } finally {
    enviandoPedido.value = false
  }
}

async function llamarMesero() {
  if (!info.value) return
  llamandoMesero.value = true
  try {
    await llamarMeseroApi(info.value.mesa_id)
    meseroAvisado.value = true
    ElMessage.success('Ya avisamos al mesero, ya viene')
    setTimeout(() => {
      meseroAvisado.value = false
    }, 60000)
  } catch {
    ElMessage.error('No se pudo avisar al mesero')
  } finally {
    llamandoMesero.value = false
  }
}

function volverAlRestaurante() {
  if (info.value) router.push(`/cliente/restaurantes/${info.value.restaurante_id}`)
  else router.push('/cliente')
}

onMounted(cargar)
onUnmounted(desconectarCarritoEnVivo)
</script>

<template>
  <div class="pagina">
    <div v-if="cargando" class="contenido-centrado">
      <el-skeleton animated :rows="5" style="width: 100%; max-width: 480px" />
    </div>

    <div v-else-if="errorToken" class="contenido-centrado">
      <div class="estado-mensaje">
        <p class="estado-titulo">Código QR inválido</p>
        <p class="estado-texto">Pedile al mesero un código nuevo.</p>
      </div>
    </div>

    <template v-else-if="info">
      <header class="barra-superior">
        <button type="button" class="enlace-volver" @click="volverAlRestaurante">
          <el-icon :size="16"><ArrowLeft /></el-icon>
          Volver al restaurante
        </button>
        <div class="acciones-barra-superior">
          <button type="button" class="boton-barra-superior" @click="infoAbierta = true">
            <el-icon :size="16"><InfoFilled /></el-icon>
            Información del restaurante
          </button>
          <button
            v-if="sesion"
            type="button"
            class="boton-barra-superior boton-llamar"
            :disabled="llamandoMesero || meseroAvisado"
            @click="llamarMesero"
          >
            <el-icon :size="16"><Bell /></el-icon>
            {{ meseroAvisado ? 'Mesero avisado' : 'Llamar al mesero' }}
          </button>
        </div>
      </header>

      <div class="contenido" :class="{ 'con-carrito': totalItems > 0 && sesion && esDueno }">
        <div class="hero-restaurante">
          <img :src="imagenComida(info.restaurante_id, 200, 200)" :alt="info.restaurante_nombre" class="foto-restaurante" />
          <div class="info-hero">
            <h1>{{ info.restaurante_nombre }}</h1>
            <p v-if="info.restaurante_categoria || info.restaurante_descripcion" class="subtitulo-hero">
              {{ info.restaurante_categoria || info.restaurante_descripcion }}
            </p>
          </div>
        </div>

        <div v-if="sesion" class="tarjeta-sesion">
          <div class="fila-saludo">
            <span class="icono-check"><el-icon :size="14"><Check /></el-icon></span>
            <span>Hola, <strong>{{ sesion.nombre }}</strong> — ya estás en la <strong>Mesa {{ info.numero }}</strong></span>
          </div>
          <div class="divisor-sesion"></div>
          <div class="fila-codigo">
            <span>Código de tu mesa: <strong class="font-mono">{{ sesion.codigo_acceso }}</strong></span>
            <span class="icono-qr"><el-icon :size="18"><Grid /></el-icon></span>
          </div>
        </div>

        <template v-if="sesion">
          <p v-if="!esDueno" class="aviso-no-dueno">
            Podés sumar platos al carrito, pero solo quien abrió la mesa puede enviar el pedido.
          </p>

          <div class="layout-pedido">
            <section class="columna-menu-mesa">
              <div class="barra-filtros">
                <div class="pildoras-categoria">
                  <button
                    v-for="grupo in gruposMenu"
                    :key="claveGrupo(grupo.categoria?.id)"
                    type="button"
                    class="pildora-categoria"
                    @click="irACategoria(grupo.categoria?.id)"
                  >
                    {{ grupo.categoria?.nombre ?? 'Otros' }}
                  </button>
                </div>
                <el-input v-model="busqueda" placeholder="Buscar en el menú..." class="input-buscar" :prefix-icon="Search" />
              </div>

              <div
                v-for="grupo in gruposMenu"
                :key="claveGrupo(grupo.categoria?.id)"
                :id="claveGrupo(grupo.categoria?.id)"
                class="grupo-categoria"
              >
                <h3 v-if="gruposMenu.length > 1" class="titulo-categoria">
                  {{ grupo.categoria?.nombre ?? 'Otros' }}
                </h3>
                <div v-for="item in grupo.items" :key="item.id" class="tarjeta-plato">
                  <img :src="imagenComida(item.id, 160, 160)" :alt="item.nombre" class="foto-plato" />
                  <div class="info-plato">
                    <p class="nombre-plato">{{ item.nombre }}</p>
                    <p v-if="item.descripcion" class="descripcion-plato">{{ item.descripcion }}</p>
                    <p class="precio-plato">${{ Number(item.precio).toLocaleString('es-CO') }}</p>
                  </div>
                  <div class="controles-cantidad">
                    <button
                      type="button"
                      class="boton-stepper"
                      :disabled="!carrito[item.id]"
                      @click="restar(item.id)"
                    >
                      −
                    </button>
                    <span class="cantidad">{{ carrito[item.id] ?? 0 }}</span>
                    <button type="button" class="boton-stepper boton-stepper-primario" @click="sumar(item.id)">
                      +
                    </button>
                  </div>
                </div>
              </div>

              <el-empty v-if="gruposMenu.length === 0" description="No encontramos platos con esa búsqueda" />
            </section>

            <aside class="columna-carrito-mesa">
              <div class="tarjeta-carrito">
                <div class="cabecera-carrito">
                  <span class="titulo-carrito"><el-icon :size="18"><ShoppingBag /></el-icon> Tu pedido</span>
                  <span class="badge-cantidad-carrito">{{ totalItems }} {{ totalItems === 1 ? 'producto' : 'productos' }}</span>
                </div>

                <div v-if="itemsDelCarrito.length === 0" class="carrito-vacio">
                  <el-icon :size="40" class="icono-carrito-vacio"><ShoppingBag /></el-icon>
                  <p class="carrito-vacio-titulo">Aún no has agregado productos a tu pedido</p>
                  <p class="carrito-vacio-texto">Explorá el menú y agregá los platos que más te gusten.</p>
                </div>
                <ul v-else class="lista-carrito">
                  <li v-for="item in itemsDelCarrito" :key="item.id">
                    <span class="cantidad-item-carrito">{{ item.cantidad }}×</span>
                    <span class="nombre-item-carrito">{{ item.nombre }}</span>
                    <span class="precio-item-carrito font-mono">${{ (item.cantidad * item.precio).toLocaleString('es-CO') }}</span>
                  </li>
                </ul>

                <el-button
                  v-if="esDueno"
                  type="primary"
                  class="boton-enviar-carrito"
                  :disabled="totalItems === 0"
                  :loading="enviandoPedido"
                  @click="enviarPedido"
                >
                  Enviar pedido
                </el-button>
                <p v-else class="texto-solo-dueno">Solo quien abrió la mesa puede enviar el pedido</p>

                <p class="total-carrito">Total: <strong>${{ totalPrecio.toLocaleString('es-CO') }}</strong></p>

                <div class="nota-carrito">
                  <el-icon :size="14"><InfoFilled /></el-icon>
                  Tu pedido será enviado al mesero para su confirmación.
                </div>
              </div>
            </aside>
          </div>
        </template>

        <div v-else-if="info.estado === 'ocupada'" class="contenido-centrado sin-padding-top">
          <div class="estado-mensaje">
            <p class="estado-titulo">Esta mesa está ocupada</p>
            <p class="estado-texto">Pedile el código de 4 dígitos a quien la abrió.</p>
            <el-input
              v-model="codigoInput"
              maxlength="4"
              placeholder="0000"
              size="large"
              class="input-reclamo"
            />
            <el-alert v-if="errorReclamo" :title="errorReclamo" type="error" :closable="false" class="alerta-reclamo" />
            <el-button type="primary" size="large" :loading="reclamando" class="boton-usar" @click="unirseConCodigo">
              Unirme a la mesa
            </el-button>
          </div>
        </div>

        <div v-else-if="info.reserva_propia" class="contenido-centrado sin-padding-top">
          <div class="estado-mensaje">
            <p class="estado-titulo">Hola {{ auth.usuario?.nombre ?? '' }}, tu reserva está confirmada</p>
            <p class="estado-texto">Confirmá tu llegada para abrir la mesa.</p>
            <el-alert v-if="errorReclamo" :title="errorReclamo" type="error" :closable="false" class="alerta-reclamo" />
            <el-button type="primary" size="large" :loading="reclamando" class="boton-usar" @click="confirmarLlegada">
              Confirmar llegada
            </el-button>
          </div>
        </div>

        <div v-else-if="info.estado === 'reservada'" class="contenido-centrado sin-padding-top">
          <div class="estado-mensaje">
            <p class="estado-titulo">Esta mesa está reservada</p>
            <p class="estado-texto">Buscá al mesero si creés que es un error.</p>
          </div>
        </div>

        <div v-else-if="auth.usuario" class="contenido-centrado sin-padding-top">
          <div class="estado-mensaje">
            <p class="estado-titulo">Esta mesa está libre</p>
            <p class="estado-texto">Podés usarla sin reserva previa.</p>
            <el-alert v-if="errorReclamo" :title="errorReclamo" type="error" :closable="false" class="alerta-reclamo" />
            <el-button type="primary" size="large" :loading="reclamando" class="boton-usar" @click="reclamarComoClienteLogueado">
              Usar esta mesa
            </el-button>
          </div>
        </div>

        <div v-else class="contenido-centrado sin-padding-top">
          <div class="estado-mensaje">
            <p class="estado-titulo">Esta mesa está libre</p>
            <p class="estado-texto">Dejanos tu nombre para abrir la mesa.</p>
            <el-input v-model="nombreInput" placeholder="Tu nombre" size="large" class="input-reclamo" />
            <el-alert v-if="errorReclamo" :title="errorReclamo" type="error" :closable="false" class="alerta-reclamo" />
            <el-button type="primary" size="large" :loading="reclamando" class="boton-usar" @click="reclamarComoInvitado">
              Usar esta mesa
            </el-button>
          </div>
        </div>
      </div>

      <div v-if="sesion && esDueno && totalItems > 0" class="barra-carrito">
        <div class="barra-carrito-info">
          <span class="barra-carrito-items">{{ totalItems }} {{ totalItems === 1 ? 'ítem' : 'ítems' }}</span>
          <span class="barra-carrito-total">${{ totalPrecio.toLocaleString('es-CO') }}</span>
        </div>
        <el-button
          type="primary"
          size="large"
          :loading="enviandoPedido"
          class="boton-enviar"
          @click="enviarPedido"
        >
          Enviar pedido
        </el-button>
      </div>

      <el-dialog v-model="infoAbierta" title="Información del restaurante" width="360px">
        <p class="dialogo-info-nombre">{{ info.restaurante_nombre }}</p>
        <p v-if="info.restaurante_categoria" class="dialogo-info-linea">{{ info.restaurante_categoria }}</p>
        <p
          v-if="info.restaurante_descripcion && info.restaurante_descripcion !== info.restaurante_categoria"
          class="dialogo-info-linea"
        >
          {{ info.restaurante_descripcion }}
        </p>
        <p v-if="!info.restaurante_categoria && !info.restaurante_descripcion" class="dialogo-info-linea">
          Este restaurante todavía no cargó más información.
        </p>
      </el-dialog>
    </template>
  </div>
</template>

<style scoped>
.pagina {
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
  background: var(--surface-sunken);
}

.contenido-centrado {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-8) var(--space-6);
}

.sin-padding-top {
  padding-top: 0;
}

.estado-mensaje {
  text-align: center;
  max-width: 320px;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.estado-titulo {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 1.25rem;
}

.estado-texto {
  color: var(--text-secondary);
  font-size: 0.9rem;
  margin-bottom: var(--space-2);
}

.input-reclamo {
  text-align: center;
}

.alerta-reclamo {
  border-radius: var(--radius-sm);
  text-align: left;
}

.boton-usar {
  font-weight: 600;
}

.barra-superior {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-6);
  background: var(--surface-raised);
  border-bottom: 1px solid var(--border-subtle);
  position: sticky;
  top: 0;
  z-index: 15;
}

.enlace-volver {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  background: none;
  border: none;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-primary);
  padding: 0;
}

.acciones-barra-superior {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-wrap: wrap;
}

.boton-barra-superior {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  background: var(--surface-muted);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-full);
  padding: var(--space-2) var(--space-4);
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-secondary);
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-standard);
}

.boton-barra-superior:hover {
  background: var(--border-subtle);
}

.boton-llamar {
  background: var(--color-secondary-soft);
  color: var(--color-secondary);
  border-color: transparent;
}

.boton-llamar:hover {
  background: var(--color-secondary-soft);
}

.boton-llamar:disabled {
  opacity: 0.6;
  cursor: default;
}

.contenido {
  max-width: 1100px;
  margin: 0 auto;
  padding: var(--space-6);
  width: 100%;
  flex: 1;
}

.contenido.con-carrito {
  padding-bottom: calc(var(--space-6) + 88px);
}

.hero-restaurante {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  margin-bottom: var(--space-4);
}

.foto-restaurante {
  width: 72px;
  height: 72px;
  border-radius: var(--radius-md);
  object-fit: cover;
  flex-shrink: 0;
}

.info-hero h1 {
  font-size: 1.4rem;
}

.subtitulo-hero {
  color: var(--text-secondary);
  font-size: 0.9rem;
  margin-top: var(--space-1);
}

.tarjeta-sesion {
  background: var(--color-success-bg);
  border-radius: var(--radius-md);
  padding: var(--space-4) var(--space-5);
  margin-bottom: var(--space-4);
}

.fila-saludo {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--color-success-text);
  font-size: 0.9rem;
}

.icono-check {
  display: grid;
  place-items: center;
  width: 22px;
  height: 22px;
  border-radius: var(--radius-full);
  background: var(--color-success);
  color: white;
  flex-shrink: 0;
}

.divisor-sesion {
  height: 1px;
  background: rgba(0, 0, 0, 0.08);
  margin: var(--space-3) 0;
}

.fila-codigo {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: var(--color-success-text);
  font-size: 0.9rem;
}

.icono-qr {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: var(--radius-sm);
  background: var(--surface-raised);
  color: var(--color-success);
}

.aviso-no-dueno {
  font-size: 0.8rem;
  color: var(--text-tertiary);
  margin-bottom: var(--space-4);
}

.layout-pedido {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--space-6);
}

@media (min-width: 900px) {
  .layout-pedido {
    grid-template-columns: 1fr 340px;
    align-items: start;
  }
}

.barra-filtros {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  margin-bottom: var(--space-5);
}

.pildoras-categoria {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
  flex: 1;
}

.pildora-categoria {
  background: var(--surface-raised);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-full);
  padding: var(--space-2) var(--space-4);
  font-size: 0.825rem;
  font-weight: 600;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-standard);
}

.pildora-categoria:hover {
  border-color: var(--color-secondary);
  color: var(--color-secondary);
}

.input-buscar {
  max-width: 260px;
  flex-shrink: 0;
}

.grupo-categoria {
  scroll-margin-top: 88px;
}

.grupo-categoria + .grupo-categoria {
  margin-top: var(--space-6);
}

.titulo-categoria {
  font-family: var(--font-display);
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: var(--space-3);
}

.tarjeta-plato {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-4);
  background: var(--surface-raised);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-soft);
}

.tarjeta-plato + .tarjeta-plato {
  margin-top: var(--space-3);
}

.foto-plato {
  width: 64px;
  height: 64px;
  border-radius: var(--radius-sm);
  object-fit: cover;
  flex-shrink: 0;
}

.info-plato {
  flex: 1;
  min-width: 0;
}

.nombre-plato {
  font-weight: 600;
}

.descripcion-plato {
  color: var(--text-tertiary);
  font-size: 0.825rem;
  margin-top: var(--space-1);
}

.precio-plato {
  color: var(--color-secondary);
  font-weight: 600;
  font-size: 0.9rem;
  margin-top: var(--space-1);
}

.controles-cantidad {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-shrink: 0;
}

.boton-stepper {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-full);
  border: 1px solid var(--border-default);
  background: var(--surface-raised);
  font-size: 1.1rem;
  line-height: 1;
  cursor: pointer;
  color: var(--text-primary);
  transition: all var(--duration-fast) var(--ease-standard);
}

.boton-stepper:disabled {
  opacity: 0.35;
  cursor: default;
}

.boton-stepper:not(:disabled):hover {
  border-color: var(--color-secondary);
}

.boton-stepper-primario {
  background: var(--color-secondary);
  border-color: var(--color-secondary);
  color: white;
}

.boton-stepper-primario:hover {
  background: var(--color-secondary-hover);
}

.cantidad {
  min-width: 1.25rem;
  text-align: center;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.columna-carrito-mesa {
  display: none;
}

@media (min-width: 900px) {
  .columna-carrito-mesa {
    display: block;
    position: sticky;
    top: 88px;
  }
}

.tarjeta-carrito {
  background: var(--surface-raised);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: var(--space-5);
  box-shadow: var(--shadow-soft);
}

.cabecera-carrito {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-4);
}

.titulo-carrito {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-weight: 700;
}

.badge-cantidad-carrito {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-secondary);
  background: var(--color-secondary-soft);
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-full);
}

.carrito-vacio {
  text-align: center;
  padding: var(--space-6) var(--space-2);
}

.icono-carrito-vacio {
  color: var(--text-tertiary);
  margin-bottom: var(--space-3);
}

.carrito-vacio-titulo {
  font-weight: 600;
  font-size: 0.9rem;
  margin-bottom: var(--space-2);
}

.carrito-vacio-texto {
  color: var(--text-tertiary);
  font-size: 0.825rem;
}

.lista-carrito {
  list-style: none;
  padding: 0;
  margin: 0 0 var(--space-4);
}

.lista-carrito li {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) 0;
  border-bottom: 1px solid var(--border-subtle);
  font-size: 0.875rem;
}

.cantidad-item-carrito {
  font-weight: 700;
  color: var(--color-secondary);
}

.nombre-item-carrito {
  flex: 1;
}

.boton-enviar-carrito {
  width: 100%;
  font-weight: 600;
  margin-top: var(--space-2);
}

.texto-solo-dueno {
  font-size: 0.8rem;
  color: var(--text-tertiary);
  font-style: italic;
  text-align: center;
}

.total-carrito {
  text-align: center;
  margin-top: var(--space-4);
  font-size: 1rem;
}

.nota-carrito {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-top: var(--space-4);
  padding: var(--space-3);
  background: var(--surface-muted);
  border-radius: var(--radius-sm);
  font-size: 0.75rem;
  color: var(--text-tertiary);
}

.barra-carrito {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: var(--surface-raised);
  border-top: 1px solid var(--border-subtle);
  box-shadow: var(--shadow-lg);
  padding: var(--space-4) var(--space-6);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  z-index: 20;
  padding-bottom: max(var(--space-4), env(safe-area-inset-bottom));
}

@media (min-width: 900px) {
  .barra-carrito {
    display: none;
  }
}

.barra-carrito-info {
  display: flex;
  flex-direction: column;
}

.barra-carrito-items {
  font-size: 0.75rem;
  color: var(--text-tertiary);
}

.barra-carrito-total {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 1.15rem;
}

.boton-enviar {
  font-weight: 600;
  padding-inline: var(--space-8);
}

.dialogo-info-nombre {
  font-weight: 700;
  margin-bottom: var(--space-2);
}

.dialogo-info-linea {
  color: var(--text-secondary);
  font-size: 0.9rem;
  margin-bottom: var(--space-1);
}
</style>
