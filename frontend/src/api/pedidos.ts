import { api } from './client'

export interface ItemPedidoInput {
  menu_item_id: number
  cantidad: number
  observaciones?: string
}

export async function crearPedido(mesaId: number, items: ItemPedidoInput[]) {
  const { data } = await api.post('/pedidos', { mesa_id: mesaId, items })
  return data
}
