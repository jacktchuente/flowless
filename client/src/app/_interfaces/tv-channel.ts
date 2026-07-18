export interface RuleValuesByAxis {
  categories?: string[]
  natures?: Array<string | number>
  container_kinds?: Array<string | number>
  directors?: string[]
  writers?: string[]
  creators?: string[]
  actors?: string[]
  studios?: string[]
  countries?: string[]
  audio_languages?: string[]
  subtitle_languages?: string[]
}

export interface RuleOptionSearchResult {
  axis: string
  value: string
}

export interface RuleOptionSearchResponse {
  results: RuleOptionSearchResult[]
}

export interface GridBlock {
  id: string | number
  starts_at: string
  ends_at: string
  priority: number
  min_items: number
  max_items: number
  min_duration_seconds_per_item: number | null
  max_duration_seconds_per_item: number | null
  allowed: RuleValuesByAxis
  preferred: RuleValuesByAxis
  forbidden: RuleValuesByAxis
  post_filler_policy: string | number | null
  post_filler_policy_name: string | null
}

export interface EditorialLineData {
  allowed: RuleValuesByAxis
  preferred: RuleValuesByAxis
  forbidden: RuleValuesByAxis
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
  media_nature: number | null
  block_id: string | number | null
  block_name: string
  flexible_selection_id?: string | number | null
  selection_type?: 'fixed' | 'flexible'
  role?: number
  role_label?: string
  parent_schedule_item?: string | number | null
}

export interface MarathonKindPolicy {
  container_kind: number
  container_kind_label?: string
  min_run: number
  max_run: number
  quota: number
}

export interface MarathonConfigData {
  kind_policies: MarathonKindPolicy[]
}

export interface GridData {
  id: string | number
  created_at: string
  is_active: boolean
  mode: number
  post_filler_policy: string | number | null
  blocks: GridBlock[]
  marathon_config?: MarathonConfigData | null
}

export interface PlayoutGenerationIssue {
  code: string
  severity: 'error' | 'warning' | 'info'
  message: string
  schedule_item_id?: string | number | null
  starts_at?: string | null
  ends_at?: string | null
}

export interface PlayoutGenerationReport {
  id: string | number
  tv_playout?: string | number
  created_at: string
  trigger: 'generate' | 'extend'
  window_start?: string | null
  window_end?: string | null
  generated_items: number
  filled_items: number
  repaired_gaps: number
  trimmed_overlaps: number
  issues?: PlayoutGenerationIssue[]
  issue_counts: {error: number, warning: number, info: number}
}

export interface TvChannel {
  id: string | number
  name: string
  description: string | null
  specification: string | null
  analyze_status: string | number
  catalog: string | number
  catalog_name: string
  programming_mode?: number
  is_enabled: boolean
  external_playout_id?: string | null
  logo?: string | null
  created_at: string
  updated_at: string
  grid_data: GridData | null
  editorial_line_data: EditorialLineData | null
  active_schedule_items: ScheduledMediaItem[]
  active_playout_id?: string | number | null
  latest_generation_report?: PlayoutGenerationReport | null
}

export interface TvChannelPayload {
  name: string
  description: string | null
  specification?: string | null
  catalog: string | number
  programming_mode?: number
}

export const PROGRAMMING_MODE_CLASSIC = 1
export const PROGRAMMING_MODE_MARATHON = 2
export const GRID_MODE_FIXED = 1
export const GRID_MODE_FLEXIBLE = 2
export const GRID_MODE_MARATHON = 3

export interface FormOption { value: number; label: string }
export interface FillerPolicyOption { id: number; name: string; duration_seconds: number }
export interface FormOptions {
  categories: string[]
  natures: FormOption[]
  container_kinds: FormOption[]
  programming_roles: FormOption[]
  filler_policies: FillerPolicyOption[]
}

export type EditorialLinePayload = EditorialLineData
export type GridBlockPayload = Omit<GridBlock, 'id' | 'post_filler_policy_name'> & {grid_layout: string | number}
export interface GridPayload { post_filler_policy: string | number | null }
export interface FormSuggestionRequest {
  form_kind: 'editorial_line' | 'grid_block' | 'grid'
  user_context: string
  current_values: Record<string, unknown>
  grid_block_id?: string | number
}
export interface FormSuggestionResponse { values: Record<string, unknown> }
export interface GridWarningsResponse { warnings: string[] }
