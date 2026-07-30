import '@fontsource-variable/geist'
import '@fontsource-variable/geist-mono'
import 'element-plus/dist/index.css'
// Va después de Element Plus a propósito: pisa sus --el-* con nuestros
// tokens (mismo :root, misma especificidad, gana el que carga último).
import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'

import App from './App.vue'
import router from './router'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(ElementPlus)

app.mount('#app')
