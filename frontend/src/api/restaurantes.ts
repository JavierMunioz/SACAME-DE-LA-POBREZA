import { api } from './client'

export interface MenuItem {
  id: number
  nombre: string
  descripcion: string | null
  precio: string
  disponible: boolean
}

export interface MenuItemCreate {
  nombre: string
  descripcion?: string
  precio: number
  disponible?: boolean
}

export interface Restaurante {
  id: number
  nombre: string
  descripcion: string | null
  created_at: string
}

export interface RestauranteConMenu extends Restaurante {
  menu: MenuItem[]
}

export interface Mesa {
  id: number
  restaurante_id: number
  numero: number
  capacidad: number
  qr_generado_at: string
  qr_url: string
}

export async function listarRestaurantes(): Promise<Restaurante[]> {
  const { data } = await api.get<Restaurante[]>('/restaurantes')
  return data
}

export async function obtenerRestaurante(id: number): Promise<RestauranteConMenu> {
  const { data } = await api.get<RestauranteConMenu>(`/restaurantes/${id}`)
  return data
}

export async function crearRestaurante(payload: {
  nombre: string
  descripcion?: string
  menu_inicial: MenuItemCreate[]
}): Promise<RestauranteConMenu> {
  const { data } = await api.post<RestauranteConMenu>('/restaurantes', payload)
  return data
}

export async function listarMesas(restauranteId: number): Promise<Mesa[]> {
  const { data } = await api.get<Mesa[]>(`/restaurantes/${restauranteId}/mesas`)
  return data
}

export async function crearMesa(
  restauranteId: number,
  payload: { numero: number; capacidad: number },
): Promise<Mesa> {
  const { data } = await api.post<Mesa>(`/restaurantes/${restauranteId}/mesas`, payload)
  return data
}

export async function regenerarQr(mesaId: number): Promise<Mesa> {
  const { data } = await api.post<Mesa>(`/mesas/${mesaId}/regenerar-qr`)
  return data
}

export function urlImagenQr(mesaId: number): string {
  return `${api.defaults.baseURL}/mesas/${mesaId}/qr.png`
}

export type RolPersonal = 'mesero' | 'cocina' | 'admin_restaurante'

export interface Personal {
  id: number
  nombre: string
  email: string
  rol: RolPersonal
  restaurante_id: number | null
}

export async function listarPersonal(restauranteId: number): Promise<Personal[]> {
  const { data } = await api.get<Personal[]>(`/restaurantes/${restauranteId}/personal`)
  return data
}

export async function crearPersonal(
  restauranteId: number,
  payload: { nombre: string; email: string; password: string; rol: RolPersonal },
): Promise<Personal> {
  const { data } = await api.post<Personal>(`/restaurantes/${restauranteId}/personal`, payload)
  return data
}
