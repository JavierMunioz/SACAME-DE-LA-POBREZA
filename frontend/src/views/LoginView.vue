<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { homeDeUsuario, useAuthStore } from '../stores/auth'
import logoWordmark from '../assets/brand/logo-wordmark.png'
import logoMark from '../assets/brand/logo-mark.png'

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
      (route.query.redirect as string) || (auth.usuario ? homeDeUsuario(auth.usuario) : '/')
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
    <aside class="panel-marca">
      <div class="marca-icono">
        <img :src="logoMark" alt="" class="marca-icono-img" />
      </div>
      <img :src="logoWordmark" alt="LagoPos" class="panel-marca-logo" />
      <p class="panel-marca-texto">
        Reservas, mesas y pedidos en un solo lugar. Escaneá, pedí, servís, cerrá la mesa.
      </p>
      <ul class="panel-marca-lista">
        <li>Pedidos de invitados sin cuenta</li>
        <li>Carrito de mesa sincronizado en vivo</li>
        <li>Cocina y mesero conectados en tiempo real</li>
      </ul>
    </aside>

    <main class="panel-form">
      <div class="formulario-wrap">
        <div class="encabezado">
          <h2>Bienvenido de nuevo</h2>
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
    </main>
  </div>
</template>

<style scoped>
.pagina {
  min-height: 100dvh;
  display: grid;
  grid-template-columns: 1fr;
}

@media (min-width: 900px) {
  .pagina {
    grid-template-columns: 1fr 1fr;
  }
}

.panel-marca {
  display: none;
  position: relative;
  flex-direction: column;
  justify-content: center;
  padding: var(--space-16) var(--space-12);
  overflow: hidden;
  background:
    radial-gradient(circle at 20% 20%, rgba(255, 85, 85, 0.35), transparent 45%),
    radial-gradient(circle at 80% 0%, rgba(255, 85, 85, 0.2), transparent 40%),
    radial-gradient(circle at 60% 90%, rgba(31, 49, 67, 0.5), transparent 50%),
    var(--color-primary);
}

@media (min-width: 900px) {
  .panel-marca {
    display: flex;
  }
}

.marca-icono {
  display: grid;
  place-items: center;
  width: 56px;
  height: 56px;
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.08);
  align-self: flex-start;
  margin-bottom: var(--space-6);
  overflow: hidden;
}

.marca-icono-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  padding: 8px;
  box-sizing: border-box;
}

.panel-marca-logo {
  height: 52px;
  width: auto;
  align-self: flex-start;
  margin-bottom: var(--space-8);
}

.panel-marca-texto {
  color: rgba(255, 255, 255, 0.75);
  font-size: 1rem;
  line-height: 1.6;
  max-width: 32ch;
  margin-bottom: var(--space-8);
}

.panel-marca-lista {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.panel-marca-lista li {
  color: rgba(255, 255, 255, 0.9);
  font-size: 0.875rem;
  padding-left: var(--space-5);
  position: relative;
}

.panel-marca-lista li::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0.5em;
  width: 6px;
  height: 6px;
  border-radius: var(--radius-full);
  background: var(--color-secondary);
}

.panel-form {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-6);
  background: var(--surface-raised);
}

.formulario-wrap {
  width: 100%;
  max-width: 360px;
}

.encabezado {
  margin-bottom: var(--space-6);
}

.encabezado h2 {
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
  background: var(--surface-muted);
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
