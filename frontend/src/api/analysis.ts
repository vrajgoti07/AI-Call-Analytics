/**
 * AI Call Analytics — Analysis API Service.
 */

import { apiClient } from './client'
import type {
  AnalysisStatusResponse,
  AnalysisSummaryResponse,
  StartAnalysisRequest,
} from './types'

export async function startAnalysis(
  callId: string,
  payload: StartAnalysisRequest = {},
): Promise<AnalysisStatusResponse> {
  return apiClient<AnalysisStatusResponse>(`/api/v1/calls/${callId}/analyze`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function getAnalysisStatus(callId: string): Promise<AnalysisStatusResponse> {
  return apiClient<AnalysisStatusResponse>(`/api/v1/calls/${callId}/analysis/status`)
}

export async function getAnalysisSummary(callId: string): Promise<AnalysisSummaryResponse> {
  return apiClient<AnalysisSummaryResponse>(`/api/v1/calls/${callId}/analysis`)
}
