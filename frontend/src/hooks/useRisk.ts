/**
 * AI Call Analytics — Escalation Risk Query Hook.
 */

import { useQuery } from '@tanstack/react-query'
import { getEscalationRisk } from '../api/risk'
import type { EscalationRiskResponse } from '../api/types'

export function useRisk(callId: string | undefined) {
  return useQuery<EscalationRiskResponse>({
    queryKey: ['risk', callId],
    queryFn: () => {
      if (!callId) throw new Error('Call ID required')
      return getEscalationRisk(callId)
    },
    enabled: Boolean(callId),
    staleTime: 60_000,
  })
}
