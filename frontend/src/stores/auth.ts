import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '../api/client'

export type Rol = 'admin_general' | 'admin_restaurante' | 'cliente' | 'mesero' | 'cocina'

export const rolAHome: Record<Rol, string> = {
  admin_general: '/admin',
  admin_restaurante: '/admin',
  cliente: '/cliente',
  mesero: '/mesero',
  cocina: '/cocina',
}

interface Usuario {
  id: number
  nombre: string
  email: string
  rol: Rol
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(
    localStorage.getItem('token') ?? sessionStorage.getItem('token'),
  )
  const usuario = ref<Usuario | null>(null)

  // "Recordar este dispositivo": localStorage sobrevive cerrar el
  // navegador; sessionStorage se borra solo al cerrar la pestaña — útil
  // en un dispositivo compartido (ej. tablet del restaurante).
  async function login(email: string, password: string, recordar = true) {
    const form = new URLSearchParams()
    form.set('username', email)
    form.set('password', password)
    const { data } = await api.post('/auth/login', form, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
    token.value = data.access_token
    localStorage.removeItem('token')
    sessionStorage.removeItem('token')
    ;(recordar ? localStorage : sessionStorage).setItem('token', data.access_token)
    await cargarUsuario()
  }

  async function cargarUsuario() {
    if (!token.value) return
    const { data } = await api.get<Usuario>('/auth/me')
    usuario.value = data
  }

  async function registro(nombre: string, email: string, password: string) {
    await api.post('/auth/registro', { nombre, email, password })
    await login(email, password)
  }

  function logout() {
    token.value = null
    usuario.value = null
    localStorage.removeItem('token')
    sessionStorage.removeItem('token')
  }

  return { token, usuario, login, logout, cargarUsuario, registro }
})
