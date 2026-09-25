/**
 * AI Call Analytics — Transcript Queries Hook.
 */

import { useQuery } from '@tanstack/react-query'
import { getTranscript, getTranscriptTurns } from '../api/transcript'
import type { TranscriptResponse, TranscriptTurnListResponse } from '../api/types'

export function useTranscript(callId: string | undefined) {
  return useQuery<TranscriptResponse>({
    queryKey: ['transcript', callId],
    queryFn: () => {
      if (!callId) throw new Error('Call ID is required')
      return getTranscript(callId)
    },
    enabled: Boolean(callId),
    staleTime: 60_000,
  })
}

export function useTranscriptTurns(callId: string | undefined, page = 1, pageSize = 100) {
  return useQuery<TranscriptTurnListResponse>({
    queryKey: ['transcript-turns', callId, page, pageSize],
    queryFn: () => {
      if (!callId) throw new Error('Call ID is required')
      return getTranscriptTurns(callId, page, pageSize)
    },
    enabled: Boolean(callId),
    staleTime: 60_000,
  })
}
