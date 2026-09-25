/**
 * AI Call Analytics — Calls API Service.
 */

import { apiClient } from './client'
import { API_BASE_URL } from '../lib/constants'
import type { CallCreate, CallDetailResponse, CallListParams, CallListResponse, CallResponse } from './types'

export async function listCalls(params: CallListParams = {}): Promise<CallListResponse> {
  const queryParams: Record<string, string | number | undefined> = {
    page: params.page ?? 1,
    page_size: params.page_size ?? 20,
    status: params.status,
    language: params.language,
    date_from: params.date_from,
    date_to: params.date_to,
  }
  return apiClient<CallListResponse>('/api/v1/calls', { params: queryParams })
}

export async function getCall(callId: string): Promise<CallDetailResponse> {
  return apiClient<CallDetailResponse>(`/api/v1/calls/${callId}`)
}

export async function createCall(payload: CallCreate): Promise<CallResponse> {
  return apiClient<CallResponse>('/api/v1/calls', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function uploadAudio(callId: string, file: File): Promise<CallResponse> {
  const formData = new FormData()
  formData.append('file', file)

  return apiClient<CallResponse>(`/api/v1/calls/${callId}/upload`, {
    method: 'POST',
    body: formData,
  })
}

export async function deleteCall(callId: string): Promise<void> {
  return apiClient<void>(`/api/v1/calls/${callId}`, {
    method: 'DELETE',
  })
}

export function getAudioStreamUrl(callId: string): string {
  return `${API_BASE_URL}/api/v1/calls/${callId}/audio`
}
