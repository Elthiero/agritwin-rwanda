const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1'

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

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
  const response = await fetch(url)
  if (!response.ok) {
    throw new ApiError(response.status, `GET ${path} failed: ${response.status}`)
  }
  return response.json() as Promise<T>
}
