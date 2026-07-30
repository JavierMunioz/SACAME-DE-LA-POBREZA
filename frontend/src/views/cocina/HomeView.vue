<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { listarPedidos, type Pedido } from '../../api/pedidos'
import { useAuthStore } from '../../stores/auth'

// Mismo enfoque que la comanda del mesero: polling simple, sin
// WebSockets todavía (ver Brain.md).
const INTERVALO_POLLING_MS = 5000

const pedidos = ref<Pedido[]>([])
const cargando = ref(true)
let intervalo: ReturnType<typeof setInterval> | undefined

const router = useRouter()
const auth = useAuthStore()

async function cargar() {
  // El backend ya devuelve orden FIFO por hora de confirmación cuando se
  // filtra por estado=confirmado.
  pedidos.value = await listarPedidos('confirmado')
  cargando.value = false
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
      <h1>Comanda de cocina</h1>
      <el-button @click="cerrarSesion">Salir</el-button>
    </header>

    <el-empty v-if="!cargando && pedidos.length === 0" description="No hay pedidos en cocina" />

    <div v-loading="cargando" class="lista-pedidos">
      <el-card v-for="(pedido, i) in pedidos" :key="pedido.id" class="tarjeta-pedido">
        <div class="cabecera-pedido">
          <span class="orden">#{{ i + 1 }}</span>
          <span class="mesa">Mesa {{ pedido.mesa_numero }}</span>
        </div>
        <ul class="items-pedido">
          <li v-for="item in pedido.items" :key="item.id">
            <span class="cantidad">{{ item.cantidad }}x</span> {{ item.menu_item_nombre }}
            <div v-if="item.observaciones" class="observaciones">{{ item.observaciones }}</div>
          </li>
        </ul>
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
  align-items: baseline;
  margin-bottom: 0.75rem;
}

.orden {
  color: #909399;
  font-size: 0.85rem;
}

.mesa {
  font-weight: 600;
}

.items-pedido {
  list-style: none;
  padding: 0;
  margin: 0;
}

.items-pedido li {
  padding: 0.4rem 0;
  border-top: 1px solid #ebeef5;
}

.items-pedido li:first-child {
  border-top: none;
}

.cantidad {
  font-weight: 600;
}

.observaciones {
  color: #e6a23c;
  font-size: 0.85rem;
}
</style>
