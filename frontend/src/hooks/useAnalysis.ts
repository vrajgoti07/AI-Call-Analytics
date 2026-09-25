/**
 * AI Call Analytics — Analysis Status and Pipeline Trigger Hooks.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getAnalysisStatus, getAnalysisSummary, startAnalysis } from '../api/analysis'
import type {
  AnalysisStatusResponse,
  AnalysisSummaryResponse,
  StartAnalysisRequest,
} from '../api/types'

export function useAnalysisStatus(callId: string | undefined, enabled = true) {
  return useQuery<AnalysisStatusResponse>({
    queryKey: ['analysis-status', callId],
    queryFn: () => {
      if (!callId) throw new Error('Call ID required')
      return getAnalysisStatus(callId)
    },
    enabled: Boolean(callId) && enabled,
    refetchInterval: (query) => {
      const data = query.state.data
      if (!data) return 2000
      // Poll every 2 seconds while processing or queued, stop when COMPLETED or FAILED
      if (data.status === 'PROCESSING' || data.status === 'QUEUED' || data.status === 'STARTED') {
        return 2000
      }
      return false
    },
  })
}

export function useAnalysisSummary(callId: string | undefined) {
  return useQuery<AnalysisSummaryResponse>({
    queryKey: ['analysis-summary', callId],
    queryFn: () => {
      if (!callId) throw new Error('Call ID required')
      return getAnalysisSummary(callId)
    },
    enabled: Boolean(callId),
    staleTime: 30_000,
  })
}

export function useStartAnalysis() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ callId, payload }: { callId: string; payload?: StartAnalysisRequest }) =>
      startAnalysis(callId, payload),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['call', variables.callId] })
      queryClient.invalidateQueries({ queryKey: ['analysis-status', variables.callId] })
      queryClient.invalidateQueries({ queryKey: ['analysis-summary', variables.callId] })
      queryClient.invalidateQueries({ queryKey: ['calls'] })
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
    },
  })
}
