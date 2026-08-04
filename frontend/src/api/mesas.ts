import { api } from './client'
import type { MenuItem } from './restaurantes'
import type { Pedido } from './pedidos'

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
  restaurante_descripcion: string | null
  restaurante_categoria: string | null
  numero: number
  capacidad: number
  reserva_propia: ReservaInfo | null
  mesa_libre_ahora: boolean
  estado: 'libre' | 'reservada' | 'ocupada'
  requiere_codigo: boolean
  requiere_ubicacion: boolean
  menu: MenuItem[]
}

export interface SesionMesa {
  token: string
  token_dueno: string | null
  codigo_acceso: string
  mesa_id: number
  nombre: string
}

export function urlWsCarrito(mesaId: number, token: string): string {
  const base = api.defaults.baseURL ?? 'http://localhost:8001'
  const wsBase = base.replace(/^http/, 'ws')
  return `${wsBase}/mesas/${mesaId}/ws?token=${encodeURIComponent(token)}`
}

export async function canjearQr(token: string): Promise<MesaQrInfo> {
  const { data } = await api.get<MesaQrInfo>(`/mesas/qr/${token}`)
  return data
}

export async function ocuparMesa(
  mesaId: number,
  qrToken: string,
  opciones: {
    nombreInvitado?: string
    reservaId?: number
    lat?: number
    lng?: number
  } = {},
): Promise<SesionMesa> {
  const { data } = await api.post<SesionMesa>(`/mesas/${mesaId}/ocupar`, {
    qr_token: qrToken,
    nombre_invitado: opciones.nombreInvitado,
    reserva_id: opciones.reservaId,
    lat: opciones.lat,
    lng: opciones.lng,
  })
  return data
}

/** Pide la ubicación del navegador. `null` si el permiso se niega, el
 * dispositivo no tiene geolocalización, o tarda más de 8s (por ejemplo
 * sin señal GPS en interiores) — el llamador decide cómo reaccionar. */
export function obtenerUbicacion(): Promise<{ lat: number; lng: number } | null> {
  return new Promise((resolve) => {
    if (!navigator.geolocation) {
      resolve(null)
      return
    }
    navigator.geolocation.getCurrentPosition(
      (posicion) => resolve({ lat: posicion.coords.latitude, lng: posicion.coords.longitude }),
      () => resolve(null),
      { timeout: 8000, maximumAge: 60000 },
    )
  })
}

export async function ocuparMesaStaff(
  mesaId: number,
  nombreInvitado?: string,
): Promise<SesionMesa> {
  const { data } = await api.post<SesionMesa>(`/mesas/${mesaId}/ocupar-staff`, {
    nombre_invitado: nombreInvitado,
  })
  return data
}

export async function liberarMesa(mesaId: number): Promise<void> {
  await api.post(`/mesas/${mesaId}/liberar`)
}

export async function llamarMesero(mesaId: number): Promise<void> {
  await api.post(`/mesas/${mesaId}/llamar-mesero`)
}

export async function atenderLlamado(mesaId: number): Promise<void> {
  await api.post(`/mesas/${mesaId}/atender-llamado`)
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

/** Para el invitado sin cuenta: ver el estado de sus pedidos con el token
 * de la sesión de mesa, sin necesitar login. */
export async function misPedidosDeLaMesa(mesaId: number, token: string): Promise<Pedido[]> {
  const { data } = await api.get<Pedido[]>(`/mesas/${mesaId}/mis-pedidos`, { params: { token } })
  return data
}
