import { api } from './client'

export interface ItemPedidoInput {
  menu_item_id: number
  cantidad: number
  observaciones?: string
}

export interface ItemPedido {
  id: number
  menu_item_id: number
  menu_item_nombre: string
  cantidad: number
  precio_unitario: string
  observaciones: string | null
}

export interface Pedido {
  id: number
  mesa_id: number
  mesa_numero: number
  cliente_id: number | null
  estado: 'pendiente' | 'confirmado' | 'preparando' | 'listo' | 'cancelado' | 'entregado'
  created_at: string
  confirmado_at: string | null
  items: ItemPedido[]
}

export async function crearPedido(mesaId: number, items: ItemPedidoInput[]) {
  const { data } = await api.post('/pedidos', { mesa_id: mesaId, items })
  return data
}

export async function listarPedidos(estado?: Pedido['estado']): Promise<Pedido[]> {
  const { data } = await api.get<Pedido[]>('/pedidos', { params: estado ? { estado } : {} })
  return data
}

export async function confirmarPedido(pedidoId: number): Promise<Pedido> {
  const { data } = await api.post<Pedido>(`/pedidos/${pedidoId}/confirmar`)
  return data
}

export async function cancelarPedido(pedidoId: number): Promise<Pedido> {
  const { data } = await api.post<Pedido>(`/pedidos/${pedidoId}/cancelar`)
  return data
}

export async function marcarPreparando(pedidoId: number): Promise<Pedido> {
  const { data } = await api.post<Pedido>(`/pedidos/${pedidoId}/marcar-preparando`)
  return data
}

export async function marcarListo(pedidoId: number): Promise<Pedido> {
  const { data } = await api.post<Pedido>(`/pedidos/${pedidoId}/marcar-listo`)
  return data
}
