import { createRouter, createWebHistory } from 'vue-router'
import { homeDeUsuario, useAuthStore, type Rol } from '../stores/auth'

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
      path: '/registro',
      name: 'registro',
      component: () => import('../views/RegistroView.vue'),
    },
    {
      // Público a propósito: escanear el QR y pedir no debería exigir
      // cuenta (ver Readme — mesa libre sin reserva se usa sin fricción).
      path: '/mesa/:restauranteId/:mesaId',
      name: 'mesa-qr',
      component: () => import('../views/MesaView.vue'),
    },
    {
      // Público: navegar restaurantes y ver el menú no requiere cuenta.
      // Solo reservar (acción que necesita identidad) pide login, y en
      // ese momento puntual.
      path: '/cliente',
      name: 'cliente',
      component: () => import('../views/cliente/HomeView.vue'),
    },
    {
      path: '/cliente/restaurantes/:id',
      name: 'cliente-restaurante',
      component: () => import('../views/cliente/RestauranteView.vue'),
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
      // admin_general entra a cualquier restaurante desde la lista;
      // admin_restaurante llega directo al suyo (ver homeDeUsuario) —
      // por eso acepta ambos roles, no solo admin_general.
      path: '/admin/restaurantes/:id',
      name: 'admin-restaurante-detalle',
      component: () => import('../views/admin/RestauranteDetalleView.vue'),
      meta: { rol: ['admin_general', 'admin_restaurante'] as Rol[] },
    },
  ],
})

router.beforeEach(async (to) => {
  const rolMeta = to.meta.rol as Rol | Rol[] | undefined
  if (!rolMeta) return true
  const rolesPermitidos = Array.isArray(rolMeta) ? rolMeta : [rolMeta]

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
  if (auth.usuario && !rolesPermitidos.includes(auth.usuario.rol)) {
    // No lo mandamos a login (ya está autenticado) ni lo dejamos con
    // pantalla en blanco (pasaba con `return false` en carga directa,
    // sin ruta anterior a la que volver): lo mandamos al home de su rol.
    const home = homeDeUsuario(auth.usuario)
    return to.path === home ? false : home
  }
  return true
})

export default router
