import { api } from './client'
import type { MenuItem } from './restaurantes'

export interface ReservaInfo {
  id: number
  mesa_id: number
  cliente_id: number
  inicio: string
  duracion_minutos: number
  estado: string
  created_at: string
}

export interface MesaQrInfo {
  mesa_id: number
  restaurante_id: number
  restaurante_nombre: string
  numero: number
  capacidad: number
  reserva_propia: ReservaInfo | null
  mesa_libre_ahora: boolean
  menu: MenuItem[]
}

export async function canjearQr(token: string): Promise<MesaQrInfo> {
  const { data } = await api.get<MesaQrInfo>(`/mesas/qr/${token}`)
  return data
}
