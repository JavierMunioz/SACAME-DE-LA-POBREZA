<script setup lang="ts">
import { KnifeFork, SwitchButton } from '@element-plus/icons-vue'

defineProps<{
  subtitulo: string
}>()

const emit = defineEmits<{ salir: [] }>()
</script>

<template>
  <aside class="sidebar">
    <div class="sidebar-marca">
      <div class="sidebar-marca-icono">
        <el-icon :size="18"><KnifeFork /></el-icon>
      </div>
      <div>
        <h1 class="sidebar-marca-nombre">Sacame de la Pobreza</h1>
        <p class="sidebar-marca-sub">{{ subtitulo }}</p>
      </div>
    </div>

    <nav class="sidebar-nav">
      <slot name="nav" />
    </nav>

    <div class="sidebar-footer">
      <slot name="accion-principal" />
      <button type="button" class="sidebar-link" @click="emit('salir')">
        <el-icon :size="16"><SwitchButton /></el-icon>
        <span>Salir</span>
      </button>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: var(--sidebar-width);
  min-height: 100vh;
  background: var(--surface-raised);
  border-right: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  position: fixed;
  left: 0;
  top: 0;
}

.sidebar-marca {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-5) var(--gutter);
}

.sidebar-marca-icono {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  background: var(--color-secondary);
  color: white;
  flex-shrink: 0;
}

.sidebar-marca-nombre {
  font-size: 0.875rem;
  font-weight: 600;
  line-height: 1.3;
}

.sidebar-marca-sub {
  font-size: 0.75rem;
  color: var(--text-tertiary);
}

.sidebar-nav {
  margin-top: var(--space-2);
  flex: 1;
  padding: 0 var(--space-3);
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.sidebar-footer {
  padding: var(--space-3);
  border-top: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.sidebar-link {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  font-size: 0.8125rem;
  font-weight: 500;
  background: none;
  border: none;
  cursor: pointer;
  text-align: left;
  width: 100%;
  transition: background var(--duration-fast) var(--ease-standard);
}

.sidebar-link:hover {
  background: var(--surface-muted);
  color: var(--text-primary);
}
</style>
