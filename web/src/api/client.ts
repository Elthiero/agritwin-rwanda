import { staticGet } from './staticFallback'

export const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1'

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

/** Fetches from the live API; falls back to the static-data offline mirror (see
 * staticFallback.ts and web/CLAUDE.md's `public/static-data/`) whenever the response
 * isn't actually the real API answering: a network-level failure (fetch throws, e.g.
 * no network or the host is down), or a response that isn't JSON at all (e.g. a static
 * host's SPA-fallback `index.html` for an unmatched `/api/v1/...` path when no backend
 * is deployed alongside the web app, or a proxy's own plain-text/HTML error page).
 * A JSON *error* response (a real ApiError: a 404 for an unknown district, a 422 for a
 * bad query param) means the real API answered and something specific went wrong; that
 * is never silently replaced with offline data that might not reflect it. */
export async function apiGet<T>(
  path: string,
  params?: Record<string, string | number>,
): Promise<T> {
  const url = new URL(`${API_BASE}${path}`, window.location.origin)
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      url.searchParams.set(key, String(value))
    }
  }

  try {
    const response = await fetch(url)
    const isJson = (response.headers.get('content-type') ?? '').includes('application/json')
    if (response.ok && isJson) {
      return (await response.json()) as T
    }
    if (!response.ok && isJson) {
      throw new ApiError(response.status, `GET ${path} failed: ${response.status}`)
    }
    // ok-but-not-JSON, or a non-JSON error page: not really the API responding.
  } catch (err) {
    if (err instanceof ApiError) throw err
    // fetch itself threw (network-level failure): fall through to the offline mirror.
  }
  return staticGet<T>(path, params)
}
