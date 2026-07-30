<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'

const form = reactive({ email: '', password: '' })
const cargando = ref(false)
const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const rolAHome: Record<string, string> = {
  admin_general: '/admin',
  admin_restaurante: '/admin',
  cliente: '/cliente',
  mesero: '/mesero',
  cocina: '/cocina',
}

async function enviar() {
  cargando.value = true
  try {
    await auth.login(form.email, form.password)
    const destino =
      (route.query.redirect as string) || rolAHome[auth.usuario?.rol ?? ''] || '/'
    router.push(destino)
  } catch {
    ElMessage.error('Email o contraseña incorrectos')
  } finally {
    cargando.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <el-card class="login-card">
      <h1>Sacame de la Pobreza</h1>
      <p class="subtitulo">Iniciar sesión</p>
      <el-form :model="form" label-position="top" @submit.prevent="enviar">
        <el-form-item label="Email">
          <el-input v-model="form.email" type="email" autocomplete="username" />
        </el-form-item>
        <el-form-item label="Contraseña">
          <el-input
            v-model="form.password"
            type="password"
            autocomplete="current-password"
            show-password
          />
        </el-form-item>
        <el-button type="primary" native-type="submit" :loading="cargando" style="width: 100%">
          Entrar
        </el-button>
      </el-form>
    </el-card>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f2f3f5;
}

.login-card {
  width: 360px;
}

h1 {
  font-size: 1.25rem;
  margin-bottom: 0.25rem;
}

.subtitulo {
  color: #909399;
  margin-bottom: 1.5rem;
}
</style>
