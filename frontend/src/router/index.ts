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
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue'),
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
      component: () => import('../views/admin/RestaurantesView.vue'),
      meta: { rol: 'admin_general' as Rol },
    },
    {
      path: '/admin/restaurantes/:id',
      name: 'admin-restaurante-detalle',
      component: () => import('../views/admin/RestauranteDetalleView.vue'),
      meta: { rol: 'admin_general' as Rol },
    },
  ],
})

router.beforeEach(async (to) => {
  const rolRequerido = to.meta.rol as Rol | undefined
  if (!rolRequerido) return true

  const auth = useAuthStore()
  if (!auth.token) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (!auth.usuario) {
    try {
      await auth.cargarUsuario()
    } catch {
      auth.logout()
      return { name: 'login', query: { redirect: to.fullPath } }
    }
  }
  if (auth.usuario?.rol !== rolRequerido) {
    return false
  }
  return true
})

export default router
