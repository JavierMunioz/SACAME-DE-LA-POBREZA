import { defineStore } from 'pinia'
import { ref } from 'vue'

export type Rol = 'admin' | 'cliente' | 'mesero' | 'cocina'

// Stub: la autenticación real se implementa en Fase 1 (ver Plan.md).
export const useAuthStore = defineStore('auth', () => {
  const rol = ref<Rol | null>(null)

  function setRol(nuevoRol: Rol) {
    rol.value = nuevoRol
  }

  return { rol, setRol }
})
