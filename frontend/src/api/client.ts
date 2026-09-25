/**
 * AI Call Analytics — Centralized HTTP Client.
 * Standardizes fetch calls, error classification, and response parsing.
 */

import { API_BASE_URL } from '../lib/constants'

export class ApiError extends Error {
  status: number
  code?: string
  details?: unknown

  constructor(status: number, message: string, code?: string, details?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
  }
}

interface RequestOptions extends RequestInit {
  params?: Record<string, string | number | boolean | null | undefined>
}

export async function apiClient<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { params, headers, ...restOptions } = options

  let url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}`

  if (params) {
    const query = new URLSearchParams()
    for (const [key, value] of Object.entries(params)) {
      if (value !== null && value !== undefined && value !== '') {
        query.append(key, String(value))
      }
    }
    const queryString = query.toString()
    if (queryString) {
      url += (url.includes('?') ? '&' : '?') + queryString
    }
  }

  const defaultHeaders: HeadersInit = {
    Accept: 'application/json',
  }

  if (!(restOptions.body instanceof FormData)) {
    defaultHeaders['Content-Type'] = 'application/json'
  }

  try {
    const response = await fetch(url, {
      ...restOptions,
      headers: {
        ...defaultHeaders,
        ...headers,
      },
    })

    if (response.status === 204) {
      return undefined as unknown as T
    }

    const contentType = response.headers.get('content-type')
    const isJson = contentType && contentType.includes('application/json')
    const data = isJson ? await response.json() : await response.text()

    if (!response.ok) {
      const message =
        typeof data === 'object' && data !== null && 'message' in data
          ? String((data as { message: unknown }).message)
          : typeof data === 'object' && data !== null && 'detail' in data
            ? String((data as { detail: unknown }).detail)
            : `HTTP ${response.status}: ${response.statusText}`

      const code =
        typeof data === 'object' && data !== null && 'code' in data
          ? String((data as { code: unknown }).code)
          : undefined

      throw new ApiError(response.status, message, code, data)
    }

    return data as T
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    throw new ApiError(
      0,
      error instanceof Error ? error.message : 'Network request failed. Is backend online?',
      'NETWORK_ERROR',
      error,
    )
  }
}
