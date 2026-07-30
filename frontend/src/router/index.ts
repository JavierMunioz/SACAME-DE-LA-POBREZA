import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore, type Rol } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/cliente',
    },
    {
      path: '/cliente',
      name: 'cliente',
      component: () => import('../views/cliente/HomeView.vue'),
      meta: { rol: 'cliente' as Rol },
    },
    {
      path: '/mesero',
      name: 'mesero',
      component: () => import('../views/mesero/HomeView.vue'),
      meta: { rol: 'mesero' as Rol },
    },
    {
      path: '/cocina',
      name: 'cocina',
      component: () => import('../views/cocina/HomeView.vue'),
      meta: { rol: 'cocina' as Rol },
    },
    {
      path: '/admin',
      name: 'admin',
      component: () => import('../views/admin/HomeView.vue'),
      meta: { rol: 'admin' as Rol },
    },
  ],
})

// Guard por rol. La autenticación real llega en Fase 1 (ver Plan.md);
// por ahora solo bloquea navegar a un rol distinto al activo en el store.
router.beforeEach((to) => {
  const rolRequerido = to.meta.rol as Rol | undefined
  if (!rolRequerido) return true

  const auth = useAuthStore()
  if (auth.rol === null) {
    auth.setRol(rolRequerido)
    return true
  }
  if (auth.rol !== rolRequerido) {
    return false
  }
  return true
})

export default router
