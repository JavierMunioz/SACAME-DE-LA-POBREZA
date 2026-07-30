<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const form = reactive({ nombre: '', email: '', password: '' })
const cargando = ref(false)
const error = ref('')
const auth = useAuthStore()
const router = useRouter()

async function enviar() {
  error.value = ''
  if (!form.nombre || !form.email || !form.password) {
    error.value = 'Completá todos los campos.'
    return
  }
  if (form.password.length < 8) {
    error.value = 'La contraseña necesita al menos 8 caracteres.'
    return
  }
  cargando.value = true
  try {
    await auth.registro(form.nombre, form.email, form.password)
    router.push('/cliente')
  } catch (e: unknown) {
    const status = (e as { response?: { status?: number } })?.response?.status
    error.value =
      status === 409 ? 'Ese email ya está registrado.' : 'No se pudo crear la cuenta.'
  } finally {
    cargando.value = false
  }
}
</script>

<template>
  <div class="pagina">
    <div class="tarjeta">
      <div class="marca">
        <span class="marca-icono">S</span>
        <span class="marca-nombre">Sacame de la Pobreza</span>
      </div>

      <div class="encabezado">
        <h1>Crear cuenta</h1>
        <p class="subtitulo">Para reservar mesa con anticipación.</p>
      </div>

      <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon class="alerta" />

      <form class="formulario" @submit.prevent="enviar">
        <label class="campo">
          <span class="campo-label">Nombre</span>
          <el-input v-model="form.nombre" size="large" autocomplete="name" placeholder="Tu nombre" />
        </label>
        <label class="campo">
          <span class="campo-label">Email</span>
          <el-input
            v-model="form.email"
            type="email"
            size="large"
            autocomplete="username"
            placeholder="vos@ejemplo.com"
          />
        </label>
        <label class="campo">
          <span class="campo-label">Contraseña</span>
          <el-input
            v-model="form.password"
            type="password"
            size="large"
            autocomplete="new-password"
            show-password
            placeholder="Mínimo 8 caracteres"
          />
        </label>
        <el-button
          type="primary"
          size="large"
          native-type="submit"
          :loading="cargando"
          class="boton-crear"
        >
          Crear cuenta
        </el-button>
      </form>

      <p class="link-login">
        ¿Ya tenés cuenta? <router-link to="/login">Iniciar sesión</router-link>
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
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-6);
  background: var(--surface-sunken);
}

.tarjeta {
  width: 100%;
  max-width: 400px;
  background: var(--surface-raised);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  padding: var(--space-8);
}

.marca {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-8);
}

.marca-icono {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  background: var(--color-primary);
  color: white;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 0.95rem;
}

.marca-nombre {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 0.95rem;
  color: var(--text-primary);
}

.encabezado {
  margin-bottom: var(--space-6);
}

.encabezado h1 {
  font-size: 1.5rem;
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

.campo-label {
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--text-primary);
}

.boton-crear {
  width: 100%;
  margin-top: var(--space-2);
  font-weight: 600;
}

.link-login {
  text-align: center;
  margin-top: var(--space-5);
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.link-login a {
  color: var(--color-secondary);
  font-weight: 500;
  text-decoration: none;
}

.link-login a:hover {
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
