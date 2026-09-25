/**
 * AI Call Analytics — System Health & Diagnostics Query Hook.
 */

import { useQuery } from '@tanstack/react-query'
import { getSystemHealth, getSystemReadiness, type HealthResponse, type ReadinessResponse } from '../api/system'

export function useSystemHealth() {
  return useQuery<HealthResponse>({
    queryKey: ['system-health'],
    queryFn: getSystemHealth,
    staleTime: 30_000,
  })
}

export function useSystemReadiness() {
  return useQuery<ReadinessResponse>({
    queryKey: ['system-readiness'],
    queryFn: getSystemReadiness,
    staleTime: 15_000,
    refetchInterval: 30_000,
  })
}
