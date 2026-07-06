export interface MediaCollection {
  id: string | number
  name: string
  external_id: string
  media_source: string | number
  media_source_name: string
  is_active: boolean
  analyzed_at: string | null
  analyze_status: number
  programming_role: number | null
  nature: number | null
  container_kind: number | null
  is_anime: boolean | null
}
