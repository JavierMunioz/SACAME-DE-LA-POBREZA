<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { cancelarPedido, confirmarPedido, listarPedidos, type Pedido } from '../../api/pedidos'
import { generarFactura, type Factura } from '../../api/facturas'
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

// La factura cierra los pedidos confirmados (pasan a "entregado"); una vez
// facturados dejan de ser accionables, no tiene sentido seguir mostrándolos
// en la comanda activa.
const pedidosActivos = computed(() =>
  pedidos.value.filter((p) => p.estado === 'pendiente' || p.estado === 'confirmado'),
)

const mesasParaCerrar = computed(() => {
  const vistas = new Map<number, number>()
  for (const p of pedidosActivos.value) {
    if (p.estado === 'confirmado') vistas.set(p.mesa_id, p.mesa_numero)
  }
  return [...vistas.entries()].map(([mesa_id, mesa_numero]) => ({ mesa_id, mesa_numero }))
})

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

const dialogoFacturaAbierto = ref(false)
const generandoFactura = ref(false)
const mesaAFacturar = ref<{ mesa_id: number; mesa_numero: number } | null>(null)
const formFactura = reactive({ incluirPropina: false, porcentaje: 10 })

const voucherAbierto = ref(false)
const voucher = ref<Factura | null>(null)

function abrirDialogoFactura(mesa: { mesa_id: number; mesa_numero: number }) {
  mesaAFacturar.value = mesa
  formFactura.incluirPropina = false
  formFactura.porcentaje = 10
  dialogoFacturaAbierto.value = true
}

async function confirmarFactura() {
  if (!mesaAFacturar.value) return
  generandoFactura.value = true
  try {
    voucher.value = await generarFactura(mesaAFacturar.value.mesa_id, {
      incluye_propina: formFactura.incluirPropina,
      porcentaje_propina: (formFactura.porcentaje / 100).toFixed(2),
    })
    dialogoFacturaAbierto.value = false
    voucherAbierto.value = true
    await cargar()
  } catch {
    ElMessage.error('No se pudo generar la factura')
  } finally {
    generandoFactura.value = false
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

    <section v-if="mesasParaCerrar.length > 0" class="mesas-para-cerrar">
      <span class="etiqueta">Listas para cerrar:</span>
      <el-button
        v-for="mesa in mesasParaCerrar"
        :key="mesa.mesa_id"
        size="small"
        @click="abrirDialogoFactura(mesa)"
      >
        Cerrar mesa {{ mesa.mesa_numero }}
      </el-button>
    </section>

    <el-empty
      v-if="!cargando && pedidosActivos.length === 0"
      description="No hay pedidos pendientes ni confirmados"
    />

    <div v-loading="cargando" class="lista-pedidos">
      <el-card v-for="pedido in pedidosActivos" :key="pedido.id" class="tarjeta-pedido">
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

    <el-dialog v-model="dialogoFacturaAbierto" title="Cerrar mesa" width="360px">
      <p v-if="mesaAFacturar">Mesa {{ mesaAFacturar.mesa_numero }}</p>
      <el-form label-position="top">
        <el-form-item label="¿Incluir propina?">
          <el-switch v-model="formFactura.incluirPropina" />
        </el-form-item>
        <el-form-item v-if="formFactura.incluirPropina" label="Porcentaje">
          <el-input-number v-model="formFactura.porcentaje" :min="0" :max="100" />
          <span style="margin-left: 0.5rem">%</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogoFacturaAbierto = false">Cancelar</el-button>
        <el-button type="primary" :loading="generandoFactura" @click="confirmarFactura">
          Generar factura
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="voucherAbierto" title="Factura" width="380px" class="dialogo-voucher">
      <div v-if="voucher" class="voucher">
        <p class="voucher-mesa">Mesa {{ voucher.mesa_numero }}</p>
        <ul class="voucher-items">
          <li v-for="item in voucher.items" :key="item.id">
            <span>{{ item.cantidad }}x {{ item.menu_item_nombre }}</span>
            <span>${{ (Number(item.precio_unitario) * item.cantidad).toLocaleString('es-CO') }}</span>
          </li>
        </ul>
        <div class="voucher-linea">
          <span>Subtotal</span>
          <span>${{ Number(voucher.subtotal).toLocaleString('es-CO') }}</span>
        </div>
        <div v-if="voucher.incluye_propina" class="voucher-linea">
          <span>Propina</span>
          <span>${{ Number(voucher.propina).toLocaleString('es-CO') }}</span>
        </div>
        <div class="voucher-linea voucher-total">
          <span>Total</span>
          <span>${{ Number(voucher.total).toLocaleString('es-CO') }}</span>
        </div>
        <el-button disabled style="width: 100%; margin-top: 1rem">Factura electrónica</el-button>
      </div>
      <template #footer>
        <el-button @click="voucherAbierto = false">Cerrar</el-button>
        <el-button type="primary" @click="window.print()">Imprimir</el-button>
      </template>
    </el-dialog>
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

.mesas-para-cerrar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-bottom: 1.5rem;
  padding: 0.75rem 1rem;
  background: #f5f7fa;
  border-radius: 4px;
}

.etiqueta {
  font-size: 0.85rem;
  color: #606266;
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

.voucher-mesa {
  font-weight: 600;
  margin-bottom: 0.75rem;
}

.voucher-items {
  list-style: none;
  padding: 0;
  margin: 0 0 0.75rem;
}

.voucher-items li {
  display: flex;
  justify-content: space-between;
  padding: 0.3rem 0;
  font-size: 0.9rem;
}

.voucher-linea {
  display: flex;
  justify-content: space-between;
  padding: 0.3rem 0;
  border-top: 1px solid #ebeef5;
}

.voucher-total {
  font-weight: 700;
  font-size: 1.05rem;
}
</style>
