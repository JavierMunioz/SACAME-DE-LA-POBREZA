<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { cancelarPedido, confirmarPedido, listarPedidos, type Pedido } from '../../api/pedidos'
import { useAuthStore } from '../../stores/auth'

// Sin infraestructura de tiempo real todavía (ver Brain.md): se refresca
// por polling cada 5s, simple y suficiente para el volumen de un MVP.
const INTERVALO_POLLING_MS = 5000

const pedidos = ref<Pedido[]>([])
const cargando = ref(true)
const procesando = ref<number | null>(null)
let intervalo: ReturnType<typeof setInterval> | undefined

const router = useRouter()
const auth = useAuthStore()

async function cargar() {
  pedidos.value = await listarPedidos()
  cargando.value = false
}

async function confirmar(pedido: Pedido) {
  procesando.value = pedido.id
  try {
    await confirmarPedido(pedido.id)
    ElMessage.success(`Pedido de mesa ${pedido.mesa_numero} enviado a cocina`)
    await cargar()
  } catch {
    ElMessage.error('No se pudo confirmar el pedido')
  } finally {
    procesando.value = null
  }
}

async function cancelar(pedido: Pedido) {
  procesando.value = pedido.id
  try {
    await cancelarPedido(pedido.id)
    ElMessage.info(`Pedido de mesa ${pedido.mesa_numero} cancelado`)
    await cargar()
  } catch {
    ElMessage.error('No se pudo cancelar el pedido')
  } finally {
    procesando.value = null
  }
}

function cerrarSesion() {
  auth.logout()
  router.push('/login')
}

onMounted(() => {
  cargar()
  intervalo = setInterval(cargar, INTERVALO_POLLING_MS)
})
onUnmounted(() => clearInterval(intervalo))
</script>

<template>
  <div class="page">
    <header class="encabezado">
      <h1>Comanda principal</h1>
      <el-button @click="cerrarSesion">Salir</el-button>
    </header>

    <el-empty
      v-if="!cargando && pedidos.length === 0"
      description="No hay pedidos pendientes ni confirmados"
    />

    <div v-loading="cargando" class="lista-pedidos">
      <el-card v-for="pedido in pedidos" :key="pedido.id" class="tarjeta-pedido">
        <div class="cabecera-pedido">
          <span class="mesa">Mesa {{ pedido.mesa_numero }}</span>
          <el-tag :type="pedido.estado === 'confirmado' ? 'success' : 'warning'">
            {{ pedido.estado }}
          </el-tag>
        </div>
        <ul class="items-pedido">
          <li v-for="item in pedido.items" :key="item.id">
            {{ item.cantidad }}x {{ item.menu_item_nombre }}
            <span v-if="item.observaciones" class="observaciones">— {{ item.observaciones }}</span>
          </li>
        </ul>
        <div v-if="pedido.estado === 'pendiente'" class="acciones-pedido">
          <el-button
            type="danger"
            plain
            size="small"
            :loading="procesando === pedido.id"
            @click="cancelar(pedido)"
          >
            Cancelar
          </el-button>
          <el-button
            type="primary"
            size="small"
            :loading="procesando === pedido.id"
            @click="confirmar(pedido)"
          >
            Confirmar
          </el-button>
        </div>
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
  align-items: center;
  margin-bottom: 1.5rem;
}

.lista-pedidos {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 1rem;
}

.cabecera-pedido {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.mesa {
  font-weight: 600;
}

.items-pedido {
  list-style: none;
  padding: 0;
  margin: 0 0 1rem;
  font-size: 0.9rem;
}

.items-pedido li {
  padding: 0.25rem 0;
}

.observaciones {
  color: #909399;
}

.acciones-pedido {
  display: flex;
  gap: 0.5rem;
  justify-content: flex-end;
}
</style>
