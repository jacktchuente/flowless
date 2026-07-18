export type ChannelImageEntityType = "studio" | "person" | "theme"
export type ChannelImageQuerySource = "axes" | "llm" | "user"

export interface ChannelImageSuggestion {
  id: string | number
  position: number
  provider: string
  thumbnail: string | null
  width: number | null
  height: number | null
  attribution: string
  is_chosen: boolean
}

export interface ChannelImageSuggestionRun {
  id: string | number
  tv_channel: string | number
  tv_channel_name: string
  kind: number
  status: number
  entity_type: ChannelImageEntityType | ""
  query: string
  query_source: ChannelImageQuerySource | ""
  diagnostics: { warnings?: string[] }
  created_at: string
  updated_at: string
  suggestions: ChannelImageSuggestion[]
}

export interface ChannelImageRunPayload {
  tv_channel: string | number
  kind?: number
  query?: string
  entity_type?: ChannelImageEntityType
}

export interface ChannelImageQueryPreview {
  entity_type: ChannelImageEntityType | null
  query: string | null
  source: ChannelImageQuerySource | null
}
