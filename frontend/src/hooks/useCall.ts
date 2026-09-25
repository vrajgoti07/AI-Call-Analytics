/**
 * AI Call Analytics — Call Detail Query Hook.
 */

import { useQuery } from '@tanstack/react-query'
import { getCall } from '../api/calls'
import type { CallDetailResponse } from '../api/types'

export function useCall(callId: string | undefined) {
  return useQuery<CallDetailResponse>({
    queryKey: ['call', callId],
    queryFn: () => {
      if (!callId) throw new Error('Call ID is required')
      return getCall(callId)
    },
    enabled: Boolean(callId),
    staleTime: 30_000,
  })
}
