/**
 * AI Call Analytics — System Health & Diagnostics API Service.
 */

import { apiClient } from './client'

export interface HealthResponse {
  status: string
  service: string
  environment: string
  version: string
}

export interface ReadinessResponse {
  status: 'ready' | 'not_ready'
  dependencies: {
    database?: string
    redis?: string
    [key: string]: string | undefined
  }
}

export async function getSystemHealth(): Promise<HealthResponse> {
  return apiClient<HealthResponse>('/health')
}

export async function getSystemReadiness(): Promise<ReadinessResponse> {
  return apiClient<ReadinessResponse>('/health/ready')
}
