/**
 * AI Call Analytics — Escalation Risk API Service.
 */

import { apiClient } from './client'
import type { EscalationRiskResponse } from './types'

export async function getEscalationRisk(callId: string): Promise<EscalationRiskResponse> {
  return apiClient<EscalationRiskResponse>(`/api/v1/calls/${callId}/risk`)
}
