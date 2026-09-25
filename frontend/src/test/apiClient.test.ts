import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, apiClient } from '../api/client'

describe('apiClient', () => {
  const originalFetch = globalThis.fetch

  beforeEach(() => {
    vi.restoreAllMocks()
  })

  afterEach(() => {
    globalThis.fetch = originalFetch
  })

  it('successfully fetches and parses JSON responses', async () => {
    const mockData = { status: 'ok', service: 'backend' }
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => mockData,
    })

    const result = await apiClient<{ status: string }>('/health')
    expect(result).toEqual(mockData)
  })

  it('constructs query strings properly from params object', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({ items: [] }),
    })

    await apiClient('/api/v1/calls', {
      params: { page: 2, status: 'COMPLETED', empty: null },
    })

    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/calls?page=2&status=COMPLETED'),
      expect.any(Object),
    )
  })

  it('throws ApiError with status and message on HTTP failure', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      statusText: 'Not Found',
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({ code: 'CALL_NOT_FOUND', message: "Call 'abc' not found" }),
    })

    await expect(apiClient('/api/v1/calls/abc')).rejects.toThrow(ApiError)

    try {
      await apiClient('/api/v1/calls/abc')
    } catch (err) {
      const apiErr = err as ApiError
      expect(apiErr.status).toBe(404)
      expect(apiErr.code).toBe('CALL_NOT_FOUND')
      expect(apiErr.message).toBe("Call 'abc' not found")
    }
  })
})
