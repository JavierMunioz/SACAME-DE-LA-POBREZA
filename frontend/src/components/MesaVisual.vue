<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  capacidad: number
  estado: 'libre' | 'reservada' | 'ocupada'
}>()

// Sillas distribuidas en círculo alrededor del tablero, empezando arriba
// y en sentido horario — una por persona de capacidad real de la mesa.
const sillas = computed(() => {
  const n = Math.max(1, props.capacidad)
  const radio = 41
  const centro = 50
  return Array.from({ length: n }, (_, i) => {
    const angulo = (-90 + (360 / n) * i) * (Math.PI / 180)
    return {
      x: centro + radio * Math.cos(angulo),
      y: centro + radio * Math.sin(angulo),
    }
  })
})
</script>

<template>
  <svg viewBox="0 0 100 100" class="mesa-visual" :class="`mesa-visual--${estado}`" aria-hidden="true">
    <circle v-for="(s, i) in sillas" :key="i" :cx="s.x" :cy="s.y" r="7" class="silla" />
    <rect x="27" y="27" width="46" height="46" rx="10" class="tablero" />
  </svg>
</template>

<style scoped>
.mesa-visual {
  width: 100%;
  height: 100%;
  overflow: visible;
}

.tablero {
  fill: var(--surface-raised);
  stroke: var(--border-default);
  stroke-width: 3;
}

.silla {
  fill: var(--border-default);
}

.mesa-visual--libre .tablero {
  stroke: var(--color-success);
}

.mesa-visual--libre .silla {
  fill: var(--color-success);
  opacity: 0.55;
}

.mesa-visual--ocupada .tablero {
  fill: var(--color-secondary-soft);
  stroke: var(--color-secondary);
}

.mesa-visual--ocupada .silla {
  fill: var(--color-secondary);
}

.mesa-visual--reservada .tablero {
  stroke: var(--color-warning);
}

.mesa-visual--reservada .silla {
  fill: var(--color-warning);
  opacity: 0.7;
}
</style>
