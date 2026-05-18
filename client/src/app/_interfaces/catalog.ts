export interface Catalog {
  id: string | number
  name: string
  description: string | null
}

export interface CatalogPayload {
  name: string
  description: string | null
}
