import { getAccessToken } from '../store/authStore'

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1'

async function parseResponse(response) {
  const contentType = response.headers.get('content-type') || ''

  if (contentType.includes('text/csv') || contentType.includes('text/plain')) {
    const text = await response.text()
    return { raw: text }
  }

  const json = await response.json()
  return json
}

export async function apiRequest(path, options = {}) {
  const {
    method = 'GET',
    body,
    headers = {},
    auth = true,
  } = options

  const requestHeaders = { ...headers }
  if (auth) {
    const token = getAccessToken()
    if (token) {
      requestHeaders.Authorization = `Bearer ${token}`
    }
  }

  const isFormData = body instanceof FormData
  if (body && !isFormData) {
    requestHeaders['Content-Type'] = 'application/json'
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers: requestHeaders,
    body: body ? (isFormData ? body : JSON.stringify(body)) : undefined,
  })

  const payload = await parseResponse(response)

  if (!response.ok) {
    const message = payload?.error?.message || `Request failed with status ${response.status}`
    throw new Error(message)
  }

  if (payload && payload.success === false) {
    throw new Error(payload.error?.message || 'Unexpected API error')
  }

  return payload
}
