export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface MediaContainerListItem {
  id: string | number
  title: string
  analyzed_at: string | null
  analyze_status: number
  item_count: number | null
  is_missing: boolean
  nature: number | null
  container_kind: number | null
}

export interface MediaContainerDetail extends MediaContainerListItem {
  original_data_hash: string
  external_id: string
  description: string | null
  media_source: string | number
  media_collection: string | number
  categories: string[]
  duration_min_seconds: number | null
  duration_max_seconds: number | null
  total_duration_seconds: number | null
  min_video_width: number | null
  min_video_height: number | null
  min_age: number | null
  max_age: number | null
  release_date: string | null
  countries: string[]
  audio_languages: string[]
  subtitle_languages: string[]
  audio_languages_any: string[]
  subtitle_languages_any: string[]
  overall_rating_score: number | null
  tags: string[]
  genres: string[]
}
