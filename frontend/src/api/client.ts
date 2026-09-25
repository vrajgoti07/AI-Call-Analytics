/**
 * AI Call Analytics — Centralized Resilient HTTP Client.
 *
 * Implements:
 * - Environment base URL resolution
 * - Typed generic responses
 * - URL query parameter serialization
 * - Configurable request timeout with AbortController
 * - Structured ApiError parsing (supports backend AppException, validation errors, HTTP errors)
 * - Request ID tracking for error tracing
 * - Multipart FormData upload support
 */

import { API_BASE_URL } from '../lib/constants'

export class ApiError extends Error {
  status: number
  code?: string
  requestId?: string
  details?: unknown

  constructor(
    status: number,
    message: string,
    code?: string,
    requestId?: string,
    details?: unknown,
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.requestId = requestId
    this.details = details
  }

  get isNotFound(): boolean {
    return this.status === 404
  }

  get isValidationError(): boolean {
    return this.status === 422 || this.code === 'VALIDATION_ERROR'
  }

  get isNetworkError(): boolean {
    return this.status === 0 || this.code === 'NETWORK_ERROR'
  }

  get isTimeout(): boolean {
    return this.code === 'TIMEOUT_ERROR' || this.status === 408 || this.status === 504
  }

  get isServerError(): boolean {
    return this.status >= 500
  }
}

export interface RequestOptions extends RequestInit {
  params?: Record<string, string | number | boolean | null | undefined>
  timeoutMs?: number
}

const DEFAULT_TIMEOUT_MS = 30000

export async function apiClient<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { params, headers, timeoutMs = DEFAULT_TIMEOUT_MS, signal: externalSignal, ...restOptions } = options

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

  const defaultHeaders: Record<string, string> = {
    Accept: 'application/json',
  }

  if (!(restOptions.body instanceof FormData)) {
    defaultHeaders['Content-Type'] = 'application/json'
  }

  // Setup timeout abort controller
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs)

  // Link external signal if provided
  if (externalSignal) {
    externalSignal.addEventListener('abort', () => controller.abort())
  }

  try {
    const response = await fetch(url, {
      ...restOptions,
      headers: {
        ...defaultHeaders,
        ...(headers as Record<string, string>),
      },
      signal: controller.signal,
    })

    clearTimeout(timeoutId)

    if (response.status === 204) {
      return undefined as unknown as T
    }

    const contentType = response.headers.get('content-type')
    const isJson = contentType && contentType.includes('application/json')
    const data = isJson ? await response.json() : await response.text()
    const headerRequestId = response.headers.get('x-request-id') || response.headers.get('request-id') || undefined

    if (!response.ok) {
      let message = `Request failed with status ${response.status}`
      let code: string | undefined = undefined
      let requestId = headerRequestId
      let details: unknown = data

      if (typeof data === 'object' && data !== null) {
        // Backend standardized AppException format: { error: { code, message, request_id, details } }
        if ('error' in data && typeof (data as { error: unknown }).error === 'object' && (data as { error: Record<string, unknown> }).error !== null) {
          const errObj = (data as { error: Record<string, unknown> }).error
          if (errObj.message) message = String(errObj.message)
          if (errObj.code) code = String(errObj.code)
          if (errObj.request_id) requestId = String(errObj.request_id)
          if (errObj.details !== undefined) details = errObj.details
        } else if ('detail' in data) {
          // FastAPI default HTTPException / 422 RequestValidationError
          const detail = (data as { detail: unknown }).detail
          if (typeof detail === 'string') {
            message = detail
          } else if (Array.isArray(detail)) {
            // Join validation error messages
            message = detail
              .map((d: { msg?: string; loc?: string[] }) => d.msg ? `${d.loc?.join('.') || 'field'}: ${d.msg}` : JSON.stringify(d))
              .join('; ')
          }
        } else {
          if ('code' in data) code = String((data as { code: unknown }).code)
          if ('message' in data) message = String((data as { message: unknown }).message)
        }
      }

      // Friendly fallback messages for standard HTTP codes
      if (!code && response.status === 404) code = 'NOT_FOUND'
      if (!code && response.status === 401) code = 'UNAUTHORIZED'
      if (!code && response.status === 403) code = 'FORBIDDEN'
      if (!code && response.status === 409) code = 'CONFLICT'
      if (!code && response.status === 413) code = 'PAYLOAD_TOO_LARGE'
      if (!code && response.status === 422) code = 'VALIDATION_ERROR'
      if (!code && response.status === 429) code = 'RATE_LIMITED'
      if (!code && response.status >= 500) code = 'SERVER_ERROR'

      throw new ApiError(response.status, message, code, requestId, details)
    }

    return data as T
  } catch (error) {
    clearTimeout(timeoutId)

    if (error instanceof ApiError) {
      throw error
    }

    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiError(
        408,
        `Request to ${endpoint} timed out after ${timeoutMs}ms.`,
        'TIMEOUT_ERROR',
      )
    }

    throw new ApiError(
      0,
      error instanceof Error ? error.message : 'Network request failed. Is the backend server online?',
      'NETWORK_ERROR',
      undefined,
      error,
    )
  }
}
