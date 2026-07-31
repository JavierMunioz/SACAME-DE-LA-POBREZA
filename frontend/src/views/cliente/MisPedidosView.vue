<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { listarPedidos, type Pedido } from '../../api/pedidos'

const pedidos = ref<Pedido[]>([])
const cargando = ref(true)
const router = useRouter()

const etiquetaEstado: Record<Pedido['estado'], string> = {
  pendiente: 'Pendiente',
  confirmado: 'Confirmado',
  preparando: 'Preparando',
  listo: 'Listo',
  en_camino: 'En camino',
  entregado: 'Entregado',
  cancelado: 'Cancelado',
}

const etiquetaCanal: Record<Pedido['canal'], string> = {
  mesa: 'En el local',
  domicilio_interno: 'Domicilio',
  rappi: 'Rappi',
  didi: 'Didi',
}

function totalPedido(pedido: Pedido): number {
  return pedido.items.reduce((acc, i) => acc + Number(i.precio_unitario) * i.cantidad, 0)
}

function irASeguimiento(pedido: Pedido) {
  if (pedido.canal !== 'domicilio_interno') return
  router.push(`/cliente/pedidos/${pedido.id}/seguimiento`)
}

function volver() {
  router.push('/cliente')
}

onMounted(async () => {
  pedidos.value = await listarPedidos()
  cargando.value = false
})
</script>

<template>
  <div class="pagina">
    <header class="encabezado-pagina">
      <button type="button" class="volver" @click="volver">← Volver</button>
    </header>

    <main class="contenido">
      <h1 class="titulo">Mis pedidos</h1>

      <el-skeleton v-if="cargando" animated :rows="5" />

      <div v-else-if="pedidos.length === 0" class="estado-vacio">
        <p class="estado-vacio-titulo">Todavía no pediste nada</p>
        <p class="estado-vacio-texto">Cuando hagas un pedido, aparece acá.</p>
      </div>

      <ul v-else class="lista-pedidos">
        <li
          v-for="pedido in pedidos"
          :key="pedido.id"
          class="tarjeta-pedido card-soft"
          :class="{ 'tarjeta-pedido--clickeable': pedido.canal === 'domicilio_interno' }"
          @click="irASeguimiento(pedido)"
        >
          <div class="cabecera-pedido">
            <span class="canal">{{ etiquetaCanal[pedido.canal] }}</span>
            <el-tag :type="pedido.estado === 'entregado' ? 'success' : 'info'" round>
              {{ etiquetaEstado[pedido.estado] }}
            </el-tag>
          </div>
          <p class="items-resumen">
            {{ pedido.items.map((i) => `${i.cantidad}× ${i.menu_item_nombre}`).join(', ') }}
          </p>
          <div class="pie-pedido">
            <span class="fecha">{{ new Date(pedido.created_at).toLocaleDateString('es-CO') }}</span>
            <span class="total">${{ totalPedido(pedido).toLocaleString('es-CO') }}</span>
          </div>
        </li>
      </ul>
    </main>
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
  max-width: 640px;
  margin: 0 auto;
  padding: var(--space-6) var(--space-4) var(--space-16);
}

.titulo {
  margin-bottom: var(--space-6);
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

.lista-pedidos {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.tarjeta-pedido {
  padding: var(--space-4);
}

.tarjeta-pedido--clickeable {
  cursor: pointer;
}

.cabecera-pedido {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
}

.canal {
  font-weight: 600;
}

.items-resumen {
  color: var(--text-secondary);
  font-size: 0.875rem;
  margin-bottom: var(--space-3);
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.pie-pedido {
  display: flex;
  justify-content: space-between;
  font-size: 0.8rem;
  color: var(--text-tertiary);
}

.total {
  font-weight: 700;
  font-family: var(--font-mono);
  color: var(--text-primary);
}
</style>
