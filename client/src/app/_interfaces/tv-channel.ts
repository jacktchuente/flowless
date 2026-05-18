export interface GridBlock {
  id: string | number
  starts_at: string
  ends_at: string
  priority: number
  min_items: number
  max_items: number
  min_duration_seconds_per_item: number | null
  max_duration_seconds_per_item: number | null
  allowed_categories: string[]
  forbidden_categories: string[]
  preferred_categories: string[]
  allowed_natures: Array<string | number>
  forbidden_natures: Array<string | number>
  preferred_natures: Array<string | number>
  allowed_container_kinds: Array<string | number>
  forbidden_container_kinds: Array<string | number>
  preferred_container_kinds: Array<string | number>
  post_filler_policy: string | number | null
  post_filler_policy_name: string | null
}

export interface EditorialLineData {
  allowed_categories: string[]
  forbidden_categories: string[]
  preferred_categories: string[]
  allowed_natures: Array<string | number>
  forbidden_natures: Array<string | number>
  preferred_natures: Array<string | number>
  allowed_container_kinds: Array<string | number>
  forbidden_container_kinds: Array<string | number>
  preferred_container_kinds: Array<string | number>
  start_at: string
  end_at: string
  allow_filler: boolean
}

export interface ScheduledMediaItem {
  id: string | number
  starts_at: string
  ends_at: string
  item: string | number
  media_item_title: string
  media_item_description: string | null
  media_container_id: string | number
  media_container_title: string
  block_id: string | number
  block_name: string
}

export interface GridData {
  id: string | number
  created_at: string
  is_active: boolean
  blocks: GridBlock[]
}

export interface TvChannel {
  id: string | number
  name: string
  description: string | null
  specification: string | null
  analyze_status: string | number
  catalog: string | number
  catalog_name: string
  is_enabled: boolean
  external_playout_id?: string | null
  logo?: string | null
  created_at: string
  updated_at: string
  grid_data: GridData | null
  editorial_line_data: EditorialLineData | null
  active_schedule_items: ScheduledMediaItem[]
  active_playout_id?: string | number | null
}

export interface TvChannelPayload {
  name: string
  description: string | null
  specification?: string | null
  catalog: string | number
}
