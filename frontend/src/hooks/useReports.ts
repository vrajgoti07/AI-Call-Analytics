/**
 * AI Call Analytics — Reports Query & Mutation Hooks.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  downloadReportFile,
  generateReport,
  getCallReport,
  getReport,
  listReports,
} from '../api/reports'
import type {
  ReportGenerateRequest,
  ReportListParams,
  ReportListResponse,
  ReportResponse,
} from '../api/types'

export const REPORTS_QUERY_KEY = ['reports']

export function useReports(params: ReportListParams = {}) {
  return useQuery<ReportListResponse>({
    queryKey: [...REPORTS_QUERY_KEY, params],
    queryFn: () => listReports(params),
    staleTime: 10_000,
  })
}

export function useReport(reportId?: string) {
  return useQuery<ReportResponse>({
    queryKey: ['report', reportId],
    queryFn: () => getReport(reportId!),
    enabled: Boolean(reportId),
    refetchInterval: (query) => {
      const data = query.state.data
      if (data && (data.status === 'GENERATING' || data.status === 'PENDING')) {
        return 2_000
      }
      return false
    },
  })
}

export function useCallReport(callId?: string) {
  return useQuery<ReportResponse>({
    queryKey: ['callReport', callId],
    queryFn: () => getCallReport(callId!),
    enabled: Boolean(callId),
    retry: false,
    refetchInterval: (query) => {
      const data = query.state.data
      if (data && (data.status === 'GENERATING' || data.status === 'PENDING')) {
        return 2_000
      }
      return false
    },
  })
}

export function useGenerateReport() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: ReportGenerateRequest) => generateReport(payload),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: REPORTS_QUERY_KEY })
      if (data.call_id) {
        queryClient.invalidateQueries({ queryKey: ['callReport', data.call_id] })
      }
      queryClient.setQueryData(['report', data.id], data)
    },
  })
}

export function useDownloadReport() {
  return useMutation({
    mutationFn: ({
      reportId,
      format,
      fallbackFilename,
    }: {
      reportId: string
      format?: 'pdf' | 'json' | 'csv'
      fallbackFilename?: string
    }) => downloadReportFile(reportId, format, fallbackFilename),
  })
}
