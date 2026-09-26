/**
 * AI Call Analytics — Ingestion Batches API Service.
 */

import { apiClient } from './client'
import type {
  BatchListParams,
  BatchListResponse,
  CallListParams,
  CallListResponse,
  IngestionBatchDetailResponse,
  ReportListResponse,
  ReportResponse,
} from './types'

export async function listBatches(params: BatchListParams = {}): Promise<BatchListResponse> {
  const queryParams: Record<string, string | number | undefined> = {
    page: params.page ?? 1,
    page_size: params.page_size ?? 20,
    status: params.status,
    search: params.search,
  }
  return apiClient<BatchListResponse>('/api/v1/batches', { params: queryParams })
}

export async function getBatch(batchId: string): Promise<IngestionBatchDetailResponse> {
  return apiClient<IngestionBatchDetailResponse>(`/api/v1/batches/${batchId}`)
}

export async function listBatchCalls(
  batchId: string,
  params: CallListParams = {},
): Promise<CallListResponse> {
  const queryParams: Record<string, string | number | undefined> = {
    page: params.page ?? 1,
    page_size: params.page_size ?? 20,
    status: params.status,
  }
  return apiClient<CallListResponse>(`/api/v1/batches/${batchId}/calls`, { params: queryParams })
}

export async function analyzeBatch(
  batchId: string,
): Promise<{ batch_id: string; total_calls: number; queued_calls: number; message: string }> {
  return apiClient<{ batch_id: string; total_calls: number; queued_calls: number; message: string }>(
    `/api/v1/batches/${batchId}/analyze`,
    { method: 'POST' },
  )
}

export async function generateBatchReport(
  batchId: string,
  title?: string,
): Promise<ReportResponse> {
  return apiClient<ReportResponse>(`/api/v1/batches/${batchId}/reports`, {
    method: 'POST',
    body: JSON.stringify({ title, report_type: 'BATCH_ANALYTICS', batch_id: batchId }),
  })
}

export async function listBatchReports(
  batchId: string,
  page: number = 1,
  pageSize: number = 20,
): Promise<ReportListResponse> {
  return apiClient<ReportListResponse>(`/api/v1/batches/${batchId}/reports`, {
    params: { page, page_size: pageSize },
  })
}
