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

export type CanalPedido = 'mesa' | 'domicilio_interno' | 'rappi' | 'didi'

export interface Pedido {
  id: number
  mesa_id: number | null
  mesa_numero: number | null
  restaurante_id: number
  canal: CanalPedido
  direccion_entrega: string | null
  telefono_entrega: string | null
  repartidor_id: number | null
  repartidor_nombre: string | null
  repartidor_lat: number | null
  repartidor_lng: number | null
  repartidor_actualizado_at: string | null
  cliente_id: number | null
  nombre_invitado: string | null
  estado: 'pendiente' | 'confirmado' | 'preparando' | 'listo' | 'en_camino' | 'cancelado' | 'entregado'
  created_at: string
  confirmado_at: string | null
  factura_id: number | null
  factura_total: string | null
  factura_pagado: boolean | null
  items: ItemPedido[]
}

export async function crearPedido(mesaId: number, items: ItemPedidoInput[], sesionToken?: string) {
  const { data } = await api.post('/pedidos', {
    mesa_id: mesaId,
    items,
    sesion_token: sesionToken,
  })
  return data
}

export async function crearPedidoDomicilio(datos: {
  restauranteId: number
  canal: Extract<CanalPedido, 'domicilio_interno' | 'rappi' | 'didi'>
  items: ItemPedidoInput[]
  direccionEntrega?: string
  telefonoEntrega?: string
}): Promise<Pedido> {
  const { data } = await api.post<Pedido>('/pedidos', {
    restaurante_id: datos.restauranteId,
    canal: datos.canal,
    direccion_entrega: datos.direccionEntrega,
    telefono_entrega: datos.telefonoEntrega,
    items: datos.items,
  })
  return data
}

export async function obtenerPedido(pedidoId: number): Promise<Pedido> {
  const { data } = await api.get<Pedido>(`/pedidos/${pedidoId}`)
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

export async function marcarEntregado(pedidoId: number, pagado = true): Promise<Pedido> {
  const { data } = await api.post<Pedido>(`/pedidos/${pedidoId}/marcar-entregado`, { pagado })
  return data
}

export async function asignarRepartidor(pedidoId: number, repartidorId: number): Promise<Pedido> {
  const { data } = await api.post<Pedido>(`/pedidos/${pedidoId}/asignar-repartidor`, {
    repartidor_id: repartidorId,
  })
  return data
}

export async function marcarEnCamino(pedidoId: number): Promise<Pedido> {
  const { data } = await api.post<Pedido>(`/pedidos/${pedidoId}/marcar-en-camino`)
  return data
}

export async function actualizarUbicacionRepartidor(
  pedidoId: number,
  lat: number,
  lng: number,
): Promise<Pedido> {
  const { data } = await api.patch<Pedido>(`/pedidos/${pedidoId}/ubicacion`, { lat, lng })
  return data
}
