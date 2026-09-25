/**
 * AI Call Analytics — Transcript API Service.
 */

import { apiClient } from './client'
import type { TranscriptResponse, TranscriptTurnListResponse } from './types'

export async function getTranscript(callId: string): Promise<TranscriptResponse> {
  return apiClient<TranscriptResponse>(`/api/v1/calls/${callId}/transcript`)
}

export async function getTranscriptTurns(
  callId: string,
  page = 1,
  pageSize = 100,
): Promise<TranscriptTurnListResponse> {
  return apiClient<TranscriptTurnListResponse>(`/api/v1/calls/${callId}/transcript/turns`, {
    params: { page, page_size: pageSize },
  })
}
