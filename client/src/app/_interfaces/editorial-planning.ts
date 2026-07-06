export interface EditorialSegmentPathElement {
  id: string | number
  segment: string | number
  segment_name: string
  position: number
  role: string
  reason: string
  transition_from_previous_score: number
}

export interface EditorialSegmentPath {
  id: string | number
  is_loop: boolean
  global_score: number
  diagnostics: Record<string, unknown>
  elements: EditorialSegmentPathElement[]
}

export interface EditorialSegment {
  id: string | number
  segment_key: string
  name: string
  description: string
  profile: Record<string, unknown>
  programmable_score: number
  cohesion_score: number
  separation_score: number
  format_consistency_score: number
  volume_score: number
  labelability_score: number
  acceptance_threshold: number
  media_count: number
}

export interface EditorialSegmentMembership {
  id: string | number
  segment: string | number
  media_container: string | number
  media_container_title: string
  media_container_categories: string[]
  score: number
  is_primary: boolean
  status: string
  decision_reason: string
  updated_at: string
}

export interface EditorialFlowRun {
  id: string | number
  catalog: string | number
  status: string | number
  is_active: boolean
  algorithm_version: string
  source_media_count: number
  segment_count: number
  channel_candidate_count: number
  started_at: string | null
  completed_at: string | null
  created_at: string
  updated_at: string
}

export interface EditorialChannelCandidate {
  id: string | number
  channel_key: string
  tv_channel: string | number | null
  tv_channel_name?: string | null
  name: string
  description: string
  viability_score: number
  status: string
  profile: Record<string, unknown>
  diagnostics: Record<string, unknown>
  segment_path?: EditorialSegmentPath | null
  created_at: string
  updated_at: string
}
