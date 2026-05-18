export interface MediaCredentials {
  application_url: string
  username: string
  password: string
}

export interface MediaSource {
  id: string | number
  name: string
  credentials: MediaCredentials
  source_type: number
  analyzed_at: string | null
  analyze_status: number
  is_active: boolean
}

export interface MediaSourcePayload {
  name: string
  credentials: MediaCredentials
  source_type: number
}

export interface MediaSourceVerifyResponse {
  is_ok: boolean
  credentials?: string[]
}
