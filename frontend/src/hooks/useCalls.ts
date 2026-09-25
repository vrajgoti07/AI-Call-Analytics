/**
 * AI Call Analytics — Calls Query & Mutation Hooks.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createCall, deleteCall, listCalls, uploadAudio } from '../api/calls'
import type { CallCreate, CallListParams, CallListResponse } from '../api/types'

export const CALLS_QUERY_KEY = ['calls']

export function useCalls(params: CallListParams = {}) {
  return useQuery<CallListResponse>({
    queryKey: [...CALLS_QUERY_KEY, params],
    queryFn: () => listCalls(params),
    staleTime: 15_000,
  })
}

export function useCreateCall() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: CallCreate) => createCall(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CALLS_QUERY_KEY })
    },
  })
}

export function useUploadAudio() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ callId, file }: { callId: string; file: File }) =>
      uploadAudio(callId, file),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: CALLS_QUERY_KEY })
      queryClient.invalidateQueries({ queryKey: ['call', variables.callId] })
    },
  })
}

export function useDeleteCall() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (callId: string) => deleteCall(callId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CALLS_QUERY_KEY })
    },
  })
}
