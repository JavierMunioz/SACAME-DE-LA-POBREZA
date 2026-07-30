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
  <div class="page" v-loading="cargando">
    <el-result v-if="errorToken" icon="error" title="Código QR inválido" />

    <template v-else-if="info">
      <header class="encabezado">
        <h1>{{ info.restaurante_nombre }}</h1>
        <p class="subtitulo">Mesa {{ info.numero }}</p>
      </header>

      <el-alert
        v-if="info.reserva_propia"
        type="success"
        :closable="false"
        :title="`Hola ${auth.usuario?.nombre ?? ''}, tu reserva está confirmada`"
        show-icon
      />

      <template v-else-if="info.mesa_libre_ahora && !aceptoUsarSinReserva">
        <el-result icon="info" title="Esta mesa está libre">
          <template #extra>
            <el-button type="primary" @click="aceptoUsarSinReserva = true">
              Usar esta mesa
            </el-button>
          </template>
        </el-result>
      </template>

      <el-result
        v-else-if="!info.mesa_libre_ahora && !info.reserva_propia"
        icon="warning"
        title="Esta mesa está ocupada"
        sub-title="Buscá al mesero si creés que es un error"
      />

      <section v-if="puedeVerMenu" class="menu">
        <h2>Menú</h2>
        <div v-for="item in info.menu" :key="item.id" class="fila-menu">
          <div class="info-plato">
            <p class="nombre-plato">{{ item.nombre }}</p>
            <p class="precio-plato">${{ Number(item.precio).toLocaleString('es-CO') }}</p>
          </div>
          <div class="controles-cantidad">
            <el-button size="small" circle @click="restar(item.id)">-</el-button>
            <span class="cantidad">{{ carrito[item.id] ?? 0 }}</span>
            <el-button size="small" circle @click="sumar(item.id)">+</el-button>
          </div>
        </div>

        <el-button
          type="primary"
          :disabled="totalItems === 0"
          :loading="enviandoPedido"
          style="width: 100%; margin-top: 1.5rem"
          @click="enviarPedido"
        >
          Enviar pedido ({{ totalItems }})
        </el-button>
      </section>
    </template>
  </div>
</template>

<style scoped>
.page {
  max-width: 640px;
  margin: 0 auto;
  padding: 2.5rem 1.5rem;
}

.encabezado {
  margin-bottom: 1.5rem;
}

.subtitulo {
  color: #909399;
}

.menu {
  margin-top: 2rem;
}

.fila-menu {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 0;
  border-bottom: 1px solid #ebeef5;
}

.nombre-plato {
  font-weight: 500;
}

.precio-plato {
  color: #909399;
  font-size: 0.85rem;
}

.controles-cantidad {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.cantidad {
  min-width: 1.5rem;
  text-align: center;
}
</style>
