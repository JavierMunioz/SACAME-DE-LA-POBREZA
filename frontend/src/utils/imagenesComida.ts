// No hay fotos reales de restaurantes/platos en el dominio todavía.
// En vez de picsum.photos (fotos random sin relación con comida — salían
// paisajes/montañas en las tarjetas de un restaurante) se usa un set
// curado de fotos reales de comida de Unsplash, elegido de forma
// determinística por id: mismo restaurante/plato, misma foto siempre.
const FOTOS_COMIDA = [
  'https://images.unsplash.com/photo-1546069901-ba9599a7e63c',
  'https://images.unsplash.com/photo-1565299624946-b28f40a0ae38',
  'https://images.unsplash.com/photo-1568901346375-23c9450c58cd',
  'https://images.unsplash.com/photo-1579584425555-c3ce17fd4351',
  'https://images.unsplash.com/photo-1414235077428-338989a2e8c0',
  'https://images.unsplash.com/photo-1512621776951-a57141f2eefd',
  'https://images.unsplash.com/photo-1467003909585-2f8a72700288',
  'https://images.unsplash.com/photo-1600891964599-f61ba0e24092',
]

export function imagenComida(id: number, ancho = 600, alto = 400): string {
  const foto = FOTOS_COMIDA[id % FOTOS_COMIDA.length]
  return `${foto}?w=${ancho}&h=${alto}&fit=crop&q=80`
}
