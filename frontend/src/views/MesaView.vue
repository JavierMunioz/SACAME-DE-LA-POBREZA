<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { canjearQr, type MesaQrInfo } from '../api/mesas'
import { crearPedido } from '../api/pedidos'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const info = ref<MesaQrInfo | null>(null)
const cargando = ref(true)
const errorToken = ref(false)
const aceptoUsarSinReserva = ref(false)
const enviandoPedido = ref(false)

// carrito: menu_item_id -> cantidad
const carrito = reactive<Record<number, number>>({})
const observaciones = reactive<Record<number, string>>({})

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
  } catch {
    errorToken.value = true
  } finally {
    cargando.value = false
  }
}

function sumar(menuItemId: number) {
  carrito[menuItemId] = (carrito[menuItemId] ?? 0) + 1
}

function restar(menuItemId: number) {
  if (!carrito[menuItemId]) return
  carrito[menuItemId] -= 1
  if (carrito[menuItemId] <= 0) delete carrito[menuItemId]
}

const totalItems = computed(() => Object.values(carrito).reduce((a, b) => a + b, 0))

const totalPrecio = computed(() => {
  if (!info.value) return 0
  return Object.entries(carrito).reduce((suma, [menuItemId, cantidad]) => {
    const item = info.value!.menu.find((m) => m.id === Number(menuItemId))
    return suma + (item ? Number(item.precio) * cantidad : 0)
  }, 0)
})

const puedeVerMenu = computed(
  () => !!info.value?.reserva_propia || (info.value?.mesa_libre_ahora && aceptoUsarSinReserva.value),
)

async function enviarPedido() {
  if (!info.value) return
  enviandoPedido.value = true
  try {
    const items = Object.entries(carrito).map(([menuItemId, cantidad]) => ({
      menu_item_id: Number(menuItemId),
      cantidad,
      observaciones: observaciones[Number(menuItemId)] || undefined,
    }))
    await crearPedido(info.value.mesa_id, items)
    ElMessage.success('Pedido enviado a la cocina')
    Object.keys(carrito).forEach((k) => delete carrito[Number(k)])
    router.push('/cliente')
  } catch {
    ElMessage.error('No se pudo enviar el pedido')
  } finally {
    enviandoPedido.value = false
  }
}

onMounted(cargar)
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
      <header class="encabezado">
        <h1>{{ info.restaurante_nombre }}</h1>
        <p class="subtitulo">Mesa {{ info.numero }}</p>
      </header>

      <div class="contenido" :class="{ 'con-carrito': totalItems > 0 }">
        <div v-if="info.reserva_propia" class="banner banner-exito">
          <span class="banner-icono">✓</span>
          <span>Hola {{ auth.usuario?.nombre ?? '' }}, tu reserva está confirmada.</span>
        </div>

        <div v-else-if="info.mesa_libre_ahora && !aceptoUsarSinReserva" class="contenido-centrado sin-padding-top">
          <div class="estado-mensaje">
            <p class="estado-titulo">Esta mesa está libre</p>
            <p class="estado-texto">Podés usarla sin reserva previa.</p>
            <el-button type="primary" size="large" class="boton-usar" @click="aceptoUsarSinReserva = true">
              Usar esta mesa
            </el-button>
          </div>
        </div>

        <div v-else-if="!info.mesa_libre_ahora && !info.reserva_propia" class="contenido-centrado sin-padding-top">
          <div class="estado-mensaje">
            <p class="estado-titulo">Esta mesa está ocupada</p>
            <p class="estado-texto">Buscá al mesero si creés que es un error.</p>
          </div>
        </div>

        <section v-if="puedeVerMenu" class="menu">
          <div class="menu-encabezado">
            <h2>Menú</h2>
            <span v-if="!auth.usuario" class="chip-invitado">Pidiendo como invitado</span>
          </div>

          <div v-for="item in info.menu" :key="item.id" class="fila-menu">
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
        </section>
      </div>

      <div v-if="puedeVerMenu && totalItems > 0" class="barra-carrito">
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
    </template>
  </div>
</template>

<style scoped>
.pagina {
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
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
}

.estado-titulo {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 1.25rem;
  margin-bottom: var(--space-2);
}

.estado-texto {
  color: var(--text-secondary);
  font-size: 0.9rem;
  margin-bottom: var(--space-5);
}

.boton-usar {
  font-weight: 600;
}

.encabezado {
  padding: var(--space-5) var(--space-6);
  background: var(--surface-raised);
  border-bottom: 1px solid var(--border-subtle);
}

.encabezado h1 {
  font-size: 1.25rem;
}

.subtitulo {
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.contenido {
  max-width: 560px;
  margin: 0 auto;
  padding: var(--space-6);
  width: 100%;
  flex: 1;
}

.contenido.con-carrito {
  padding-bottom: calc(var(--space-6) + 88px);
}

.banner {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-5);
  border-radius: var(--radius-md);
  font-size: 0.9rem;
  font-weight: 500;
  margin-bottom: var(--space-6);
}

.banner-exito {
  background: var(--color-success-bg);
  color: var(--color-success-text);
}

.banner-icono {
  display: grid;
  place-items: center;
  width: 24px;
  height: 24px;
  border-radius: var(--radius-full);
  background: var(--color-success);
  color: white;
  font-size: 0.8rem;
  flex-shrink: 0;
}

.menu {
  margin-top: var(--space-6);
}

.menu-encabezado {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-4);
}

.chip-invitado {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-info);
  background: var(--color-info-bg);
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-full);
}

.fila-menu {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-4) 0;
}

.fila-menu + .fila-menu {
  border-top: 1px solid var(--border-subtle);
}

.nombre-plato {
  font-weight: 500;
}

.descripcion-plato {
  color: var(--text-tertiary);
  font-size: 0.825rem;
  margin-top: var(--space-1);
}

.precio-plato {
  color: var(--text-secondary);
  font-size: 0.875rem;
  margin-top: var(--space-1);
}

.controles-cantidad {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-shrink: 0;
}

.boton-stepper {
  width: 36px;
  height: 36px;
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
</style>
