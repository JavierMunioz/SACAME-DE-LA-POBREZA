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
  check_in_at: string | null
}

export interface MesaQrInfo {
  mesa_id: number
  restaurante_id: number
  restaurante_nombre: string
  numero: number
  capacidad: number
  reserva_propia: ReservaInfo | null
  mesa_libre_ahora: boolean
  estado: 'libre' | 'reservada' | 'ocupada'
  requiere_codigo: boolean
  menu: MenuItem[]
}

export interface SesionMesa {
  token: string
  codigo_acceso: string
  mesa_id: number
  nombre: string
}

export async function canjearQr(token: string): Promise<MesaQrInfo> {
  const { data } = await api.get<MesaQrInfo>(`/mesas/qr/${token}`)
  return data
}

export async function ocuparMesa(
  mesaId: number,
  qrToken: string,
  opciones: { nombreInvitado?: string; reservaId?: number } = {},
): Promise<SesionMesa> {
  const { data } = await api.post<SesionMesa>(`/mesas/${mesaId}/ocupar`, {
    qr_token: qrToken,
    nombre_invitado: opciones.nombreInvitado,
    reserva_id: opciones.reservaId,
  })
  return data
}

export async function unirseAMesa(
  mesaId: number,
  qrToken: string,
  codigoAcceso: string,
): Promise<SesionMesa> {
  const { data } = await api.post<SesionMesa>(`/mesas/${mesaId}/unirse`, {
    qr_token: qrToken,
    codigo_acceso: codigoAcceso,
  })
  return data
}
