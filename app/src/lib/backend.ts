const rawBaseUrl = import.meta.env.VITE_BACKEND_URL ?? ''

export const backendBaseUrl = rawBaseUrl.replace(/\/$/, '')

export function backendUrl(path: string): string {
  if (!backendBaseUrl) return path
  return `${backendBaseUrl}${path.startsWith('/') ? path : `/${path}`}`
}
