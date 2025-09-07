// API client with resolved base URL and helper functions

export interface RequestOptions extends RequestInit {
  timeout?: number
}

export interface JobFile {
  kind: string
  path: string
  url?: string | null
}

export interface Job {
  job_id: string
  source: string
  created_at: number
  updated_at: number
  files: JobFile[]
}

export interface RootInfo {
  path: string
  exists: boolean
  file_count: number
  latest_mtime: number | null
}

export interface Roots {
  inputs: RootInfo
  outputs: RootInfo
  comfy: RootInfo
}

// Resolve API base URL
function getAPIBase(): string {
  // 1. Check meta tag
  const metaTag = document.querySelector('meta[name="api-base"]')
  if (metaTag) {
    const content = metaTag.getAttribute('content')
    if (content) {
      console.log('[api] base =', content, '(from meta tag)')
      return content
    }
  }

  // 2. Check env variable
  const envBase = import.meta.env.VITE_API_BASE
  if (envBase) {
    console.log('[api] base =', envBase, '(from VITE_API_BASE)')
    return envBase
  }

  // 3. Fallback to origin
  const origin = window.