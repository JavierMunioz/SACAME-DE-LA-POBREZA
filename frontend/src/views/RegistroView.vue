<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'

const form = reactive({ nombre: '', email: '', password: '' })
const cargando = ref(false)
const auth = useAuthStore()
const router = useRouter()

async function enviar() {
  if (!form.nombre || !form.email || !form.password) {
    ElMessage.warning('Completá todos los campos')
    return
  }
  cargando.value = true
  try {
    await auth.registro(form.nombre, form.email, form.password)
    router.push('/cliente')
  } catch (e: unknown) {
    const status = (e as { response?: { status?: number } })?.response?.status
    ElMessage.error(status === 409 ? 'Ese email ya está registrado' : 'No se pudo crear la cuenta')
  } finally {
    cargando.value = false
  }
}
</script>

<template>
  <div class="registro-page">
    <el-card class="registro-card">
      <h1>Crear cuenta</h1>
      <p class="subtitulo">Sacame de la Pobreza</p>
      <el-form :model="form" label-position="top" @submit.prevent="enviar">
        <el-form-item label="Nombre">
          <el-input v-model="form.nombre" autocomplete="name" />
        </el-form-item>
        <el-form-item label="Email">
          <el-input v-model="form.email" type="email" autocomplete="username" />
        </el-form-item>
        <el-form-item label="Contraseña">
          <el-input
            v-model="form.password"
            type="password"
            autocomplete="new-password"
            show-password
          />
        </el-form-item>
        <el-button type="primary" native-type="submit" :loading="cargando" style="width: 100%">
          Crear cuenta
        </el-button>
      </el-form>
      <p class="link-login">
        ¿Ya tenés cuenta? <router-link to="/login">Iniciar sesión</router-link>
      </p>
    </el-card>
  </div>
</template>

<style scoped>
.registro-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f2f3f5;
}

.registro-card {
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

.link-login {
  text-align: center;
  margin-top: 1rem;
  font-size: 0.9rem;
  color: #606266;
}
</style>
