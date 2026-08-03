<script setup lang="ts">
import { KnifeFork, SwitchButton } from '@element-plus/icons-vue'
import logoWordmark from '../assets/brand/logo-wordmark.png'

defineProps<{
  subtitulo: string
}>()

const emit = defineEmits<{ salir: [] }>()
</script>

<template>
  <header class="topnav">
    <div class="topnav-marca">
      <div class="topnav-marca-icono">
        <el-icon :size="16"><KnifeFork /></el-icon>
      </div>
      <div class="topnav-marca-textos">
        <img :src="logoWordmark" alt="LagoPos" class="topnav-marca-logo" />
        <span class="topnav-marca-sub">{{ subtitulo }}</span>
      </div>
    </div>

    <nav class="topnav-nav">
      <slot name="nav" />
    </nav>

    <div class="topnav-acciones">
      <slot name="accion-principal" />
      <button type="button" class="topnav-salir" @click="emit('salir')">
        <el-icon :size="16"><SwitchButton /></el-icon>
        <span class="topnav-salir-texto">Salir</span>
      </button>
    </div>
  </header>
</template>

<style scoped>
/* Mobile-first: base = compacto (gap chico, padding chico, cabe en
   celular angosto sin desbordar). Se agranda recién a partir de 640px. */
.topnav {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background: var(--surface-raised);
  border-bottom: 1px solid var(--border-subtle);
  position: sticky;
  top: 0;
  z-index: 20;
  overflow-x: auto;
}

@media (min-width: 640px) {
  .topnav {
    gap: var(--space-6);
    padding: var(--space-3) var(--space-6);
  }
}

.topnav-marca {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-shrink: 0;
}

.topnav-marca-icono {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  background: var(--color-secondary);
  color: white;
  flex-shrink: 0;
}

.topnav-marca-textos {
  display: none;
  flex-direction: column;
  line-height: 1.2;
}

@media (min-width: 640px) {
  .topnav-marca-textos {
    display: flex;
  }
}

.topnav-marca-logo {
  height: 18px;
  width: auto;
  display: block;
}

.topnav-marca-sub {
  font-size: 0.7rem;
  color: var(--text-tertiary);
}

.topnav-nav {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex: 1;
  min-width: 0;
}

.topnav-acciones {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-shrink: 0;
}

.topnav-salir {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-sm);
  border: none;
  background: none;
  color: var(--text-secondary);
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;
  flex-shrink: 0;
  transition: background var(--duration-fast) var(--ease-standard);
}

.topnav-salir-texto {
  display: none;
}

@media (min-width: 640px) {
  .topnav-salir-texto {
    display: inline;
  }
}

.topnav-salir:hover {
  background: var(--surface-muted);
  color: var(--text-primary);
}
</style>
