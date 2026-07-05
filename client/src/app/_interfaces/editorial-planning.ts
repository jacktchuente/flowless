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
