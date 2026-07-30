import { api } from './client'
import type { ItemPedido } from './pedidos'

export interface Factura {
  id: number
  mesa_id: number
  mesa_numero: number
  subtotal: string
  incluye_propina: boolean
  propina: string
  total: string
  created_at: string
  items: ItemPedido[]
}

export async function generarFactura(
  mesaId: number,
  payload: { incluye_propina: boolean; porcentaje_propina?: string },
): Promise<Factura> {
  const { data } = await api.post<Factura>(`/mesas/${mesaId}/factura`, payload)
  return data
}

export async function obtenerFactura(facturaId: number): Promise<Factura> {
  const { data } = await api.get<Factura>(`/facturas/${facturaId}`)
  return data
}
