/**
 * AI Call Analytics — Ingestion Batches Query & Mutation Hooks.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  analyzeBatch,
  generateBatchReport,
  getBatch,
  listBatchCalls,
  listBatchReports,
  listBatches,
} from '../api/batches'
import type {
  BatchListParams,
  BatchListResponse,
  CallListParams,
  CallListResponse,
  IngestionBatchDetailResponse,
  ReportListResponse,
} from '../api/types'

export const BATCHES_QUERY_KEY = ['batches']

export function useBatches(params: BatchListParams = {}) {
  return useQuery<BatchListResponse>({
    queryKey: [...BATCHES_QUERY_KEY, params],
    queryFn: () => listBatches(params),
    staleTime: 10_000,
    refetchInterval: (query) => {
      // Auto-poll if any batch is uploading or processing
      const hasActive = query.state.data?.items.some(
        (b) => b.status === 'UPLOADING' || b.status === 'PROCESSING',
      )
      return hasActive ? 3000 : false
    },
  })
}

export function useBatch(batchId: string | undefined) {
  return useQuery<IngestionBatchDetailResponse>({
    queryKey: ['batch', batchId],
    queryFn: () => getBatch(batchId!),
    enabled: Boolean(batchId),
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status === 'UPLOADING' || status === 'PROCESSING' ? 3000 : false
    },
  })
}

export function useBatchCalls(batchId: string | undefined, params: CallListParams = {}) {
  return useQuery<CallListResponse>({
    queryKey: ['batch-calls', batchId, params],
    queryFn: () => listBatchCalls(batchId!, params),
    enabled: Boolean(batchId),
    refetchInterval: 5000,
  })
}

export function useAnalyzeBatch() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (batchId: string) => analyzeBatch(batchId),
    onSuccess: (_, batchId) => {
      queryClient.invalidateQueries({ queryKey: BATCHES_QUERY_KEY })
      queryClient.invalidateQueries({ queryKey: ['batch', batchId] })
      queryClient.invalidateQueries({ queryKey: ['batch-calls', batchId] })
      queryClient.invalidateQueries({ queryKey: ['calls'] })
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
    },
  })
}

export function useGenerateBatchReport() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ batchId, title }: { batchId: string; title?: string }) =>
      generateBatchReport(batchId, title),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['batch-reports', variables.batchId] })
      queryClient.invalidateQueries({ queryKey: ['reports'] })
    },
  })
}

export function useBatchReports(batchId: string | undefined, page: number = 1, pageSize: number = 20) {
  return useQuery<ReportListResponse>({
    queryKey: ['batch-reports', batchId, page, pageSize],
    queryFn: () => listBatchReports(batchId!, page, pageSize),
    enabled: Boolean(batchId),
    staleTime: 10_000,
  })
}
