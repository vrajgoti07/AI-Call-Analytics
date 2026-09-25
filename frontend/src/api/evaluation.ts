/**
 * AI Call Analytics — Evaluation Benchmarks API Service.
 */

import { apiClient } from './client'
import type { EvaluationResponse } from './types'

export async function getEvaluationResults(): Promise<EvaluationResponse> {
  return apiClient<EvaluationResponse>('/api/v1/evaluation')
}
