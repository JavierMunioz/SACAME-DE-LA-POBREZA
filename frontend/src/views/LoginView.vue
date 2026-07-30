<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { KnifeFork } from '@element-plus/icons-vue'
import { rolAHome, useAuthStore } from '../stores/auth'

const form = reactive({ email: '', password: '' })
const recordar = ref(true)
const cargando = ref(false)
const error = ref('')
const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

async function enviar() {
  error.value = ''
  cargando.value = true
  try {
    await auth.login(form.email, form.password, recordar.value)
    const destino =
      (route.query.redirect as string) || (auth.usuario ? rolAHome[auth.usuario.rol] : '/')
    router.push(destino)
  } catch {
    error.value = 'Email o contraseña incorrectos.'
  } finally {
    cargando.value = false
  }
}
</script>

<template>
  <div class="pagina">
    <div class="fondo-hero" aria-hidden="true"></div>
    <div class="tarjeta glass-panel">
      <div class="marca">
        <span class="marca-icono"><el-icon :size="20"><KnifeFork /></el-icon></span>
        <span class="marca-nombre">Sacame de la Pobreza</span>
        <span class="marca-subtitulo">Panel de gestión</span>
      </div>

      <div class="encabezado">
        <h1>Bienvenido de nuevo</h1>
        <p class="subtitulo">Entrá para gestionar reservas, mesas y pedidos.</p>
      </div>

      <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon class="alerta" />

      <form class="formulario" @submit.prevent="enviar">
        <label class="campo">
          <span class="campo-label label-mono">Email</span>
          <el-input
            v-model="form.email"
            type="email"
            size="large"
            autocomplete="username"
            placeholder="vos@ejemplo.com"
          />
        </label>
        <label class="campo">
          <span class="campo-label label-mono">Contraseña</span>
          <el-input
            v-model="form.password"
            type="password"
            size="large"
            autocomplete="current-password"
            show-password
            placeholder="••••••••"
          />
        </label>
        <label class="campo-checkbox">
          <el-checkbox v-model="recordar">Recordar este dispositivo</el-checkbox>
        </label>
        <el-button
          type="primary"
          size="large"
          native-type="submit"
          :loading="cargando"
          class="boton-entrar"
        >
          Entrar
        </el-button>
      </form>

      <p class="link-registro">
        ¿Todavía no tenés cuenta? <router-link to="/registro">Crear cuenta</router-link>
      </p>

      <div class="nota-invitado">
        <span>¿Venís a comer?</span> No hace falta cuenta: escaneá el QR de tu mesa y pedís directo.
      </div>
    </div>
  </div>
</template>

<style scoped>
.pagina {
  min-height: 100dvh;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-6);
  background: var(--surface-sunken);
  overflow: hidden;
}

.fondo-hero {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 12% 15%, rgba(79, 70, 229, 0.22), transparent 42%),
    radial-gradient(circle at 88% 20%, rgba(79, 70, 229, 0.12), transparent 38%),
    radial-gradient(circle at 80% 85%, rgba(24, 24, 27, 0.16), transparent 45%),
    radial-gradient(circle at 10% 90%, rgba(79, 70, 229, 0.1), transparent 40%);
  pointer-events: none;
}

.tarjeta {
  position: relative;
  width: 100%;
  max-width: 400px;
  border-radius: var(--radius-lg);
  padding: var(--space-8);
}

.marca {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: var(--space-2);
  margin-bottom: var(--space-8);
}

.marca-icono {
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  border-radius: var(--radius-md);
  background: var(--color-secondary);
  color: white;
  margin-bottom: var(--space-1);
}

.marca-nombre {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 1.05rem;
  color: var(--text-primary);
}

.marca-subtitulo {
  font-size: 0.8rem;
  color: var(--text-tertiary);
}

.encabezado {
  margin-bottom: var(--space-6);
  text-align: center;
}

.encabezado h1 {
  font-size: 1.4rem;
  margin-bottom: var(--space-1);
}

.subtitulo {
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.alerta {
  margin-bottom: var(--space-4);
  border-radius: var(--radius-sm);
}

.formulario {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.campo {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.campo-checkbox {
  margin-top: calc(var(--space-1) * -1);
}

.boton-entrar {
  width: 100%;
  margin-top: var(--space-2);
  font-weight: 600;
}

.link-registro {
  text-align: center;
  margin-top: var(--space-5);
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.link-registro a {
  color: var(--color-secondary);
  font-weight: 500;
  text-decoration: none;
}

.link-registro a:hover {
  text-decoration: underline;
}

.nota-invitado {
  margin-top: var(--space-6);
  padding: var(--space-4);
  background: var(--surface-sunken);
  border-radius: var(--radius-sm);
  font-size: 0.825rem;
  color: var(--text-secondary);
  line-height: 1.5;
}

.nota-invitado span {
  font-weight: 600;
  color: var(--text-primary);
}
</style>
