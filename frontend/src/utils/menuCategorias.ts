import type { Categoria, MenuItem } from '../api/restaurantes'

export interface GrupoMenu {
  categoria: Categoria | null
  items: MenuItem[]
}

/** Agrupa platos por categoría, en el orden que definió el admin. Un
 * plato en varias categorías aparece repetido en cada una (es la forma
 * natural de navegar un menú por secciones). Los platos sin ninguna
 * categoría asignada quedan al final bajo "Otros" — pero si NINGÚN plato
 * tiene categoría (restaurante que no las configuró todavía), devuelve
 * un solo grupo sin categoría, para que el caller pueda decidir no
 * mostrar encabezados de sección. */
export function agruparMenuPorCategoria(items: MenuItem[]): GrupoMenu[] {
  const categoriasVistas = new Map<number, Categoria>()
  for (const item of items) {
    for (const categoria of item.categorias) {
      if (!categoriasVistas.has(categoria.id)) categoriasVistas.set(categoria.id, categoria)
    }
  }
  const categoriasOrdenadas = [...categoriasVistas.values()].sort((a, b) => a.orden - b.orden)

  const grupos: GrupoMenu[] = categoriasOrdenadas.map((categoria) => ({
    categoria,
    items: items.filter((item) => item.categorias.some((c) => c.id === categoria.id)),
  }))

  const sinCategoria = items.filter((item) => item.categorias.length === 0)
  if (sinCategoria.length > 0) {
    grupos.push({ categoria: null, items: sinCategoria })
  }

  return grupos
}
