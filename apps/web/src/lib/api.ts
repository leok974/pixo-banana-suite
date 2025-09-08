// apps/web/src/lib/api.ts
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
  // 1) Meta tag (index.html controls this)
  const metaTag = document.querySelector('meta[name="api-base"]')
  if (metaTag) {
    const content = metaTag.getAttribute('content')
    if (content) {
      console.log('[api] base =', content, '(from meta tag)')
      return content
    }
  }

  // 2) Env (Vite)
  const envBase = import.meta.env.VITE_API_BASE
  if (envBase) {
    console.log('[api] base =', envBase, '(from VITE_API_BASE)')
    return envBase
  }

  // 3) Fallback to current origin
  const origin = window.location.origin
  console.log('[api] base =', origin, '(from window.origin fallback)')
  return origin
}

const API_BASE = getAPIBase()

async function request<T = any>(
  path: string,
  opts: RequestOptions = {}
): Promise<T> {
  const { timeout = 12_000, headers, ...rest } = opts
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeout)

  try {
    const res = await fetch(`${API_BASE}${path}`, {
      headers: { 'Content-Type': 'application/json', ...(headers || {}) },
      signal: controller.signal,
      ...rest,
    })
    if (!res.ok) {
      const text = await res.text().catch(() => '')
      throw new Error(`${res.status} ${res.statusText}: ${text || '(no body)'}`)
    }
    const ct = res.headers.get('content-type') || ''
    return (ct.includes('application/json') ? (await res.json()) : (await res.text())) as T
  } finally {
    clearTimeout(timer)
  }
}

export function pingAPI() {
  return request('/pipeline/ping')
}

export function fetchRoots(): Promise<Roots> {
  return request('/pipeline/roots')
}

export function fetchJobs(params?: { limit?: number; resolve_urls?: boolean }) {
  const q = new URLSearchParams()
  if (params?.limit != null) q.set('limit', String(params.limit))
  if (params?.resolve_urls != null) q.set('resolve_urls', String(params.resolve_urls))
  const qs = q.toString()
  return request(`/pipeline/status${qs ? `?${qs}` : ''}`)
}

export function postEdit(body: {
  items: Array<{ image_path: string; instruction: string }>
}) {
  return request('/edit', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function postAnimate(body: {
  items: Array<{ frames: string[]; basename: string; fps?: number; sheet_cols?: number }>
}) {
  return request('/animate', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function postPoses(payload: {
  image_path: string
  instruction?: string
  poses: { name: string }[]
  fps?: number
  sheet_cols?: number
  out_dir?: string
  basename?: string
}) {
  const base = getAPIBase()
  const res = await fetch(`${base}/pipeline/poses`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error(`/pipeline/poses ${res.status}`)
  return res.json()
}

export async function agentChat(payload: {
  messages: { role: 'user' | 'assistant' | 'system'; content: string }[]
  intent?: 'auto' | 'edit' | 'animate' | 'poses'
}) {
  return request('/agent/chat', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
