import { api } from './client'

export interface MesaDisponibilidad {
  mesa_id: number
  numero: number
  capacidad: number
  disponible: boolean
}

export async function consultarDisponibilidad(
  restauranteId: number,
  inicio: string,
  duracionMinutos = 90,
): Promise<MesaDisponibilidad[]> {
  const { data } = await api.get<MesaDisponibilidad[]>(
    `/restaurantes/${restauranteId}/disponibilidad`,
    { params: { inicio, duracion_minutos: duracionMinutos } },
  )
  return data
}

export async function crearReserva(payload: {
  mesa_id: number
  inicio: string
  duracion_minutos?: number
}) {
  const { data } = await api.post('/reservas', payload)
  return data
}
