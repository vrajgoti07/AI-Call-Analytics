/**
 * AI Call Analytics — Reports API Service.
 */

import { apiClient } from './client'
import { API_BASE_URL } from '../lib/constants'
import type {
  ReportGenerateRequest,
  ReportListParams,
  ReportListResponse,
  ReportResponse,
} from './types'

export async function generateReport(
  payload: ReportGenerateRequest,
): Promise<ReportResponse> {
  return apiClient<ReportResponse>('/api/v1/reports/generate', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function getReport(reportId: string): Promise<ReportResponse> {
  return apiClient<ReportResponse>(`/api/v1/reports/${reportId}`)
}

export async function listReports(
  params: ReportListParams = {},
): Promise<ReportListResponse> {
  const queryParams: Record<string, string | number | undefined> = {
    page: params.page ?? 1,
    page_size: params.page_size ?? 20,
    call_id: params.call_id,
    report_type: params.report_type,
  }
  return apiClient<ReportListResponse>('/api/v1/reports', { params: queryParams })
}

export async function getCallReport(callId: string): Promise<ReportResponse> {
  return apiClient<ReportResponse>(`/api/v1/calls/${callId}/report`)
}

export async function downloadReportFile(
  reportId: string,
  format: 'pdf' | 'json' | 'csv' = 'pdf',
  fallbackFilename?: string,
): Promise<void> {
  const token = localStorage.getItem('ai_call_token')
  const url = `${API_BASE_URL}/api/v1/reports/${reportId}/download?format=${format}`

  const response = await fetch(url, {
    method: 'GET',
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  })

  if (!response.ok) {
    let errMessage = 'Failed to download report'
    try {
      const errJson = await response.json()
      errMessage = errJson.message || errMessage
    } catch {
      // ignore
    }
    throw new Error(errMessage)
  }

  // Extract filename from Content-Disposition header if available
  const disposition = response.headers.get('Content-Disposition')
  let filename = fallbackFilename || `report-${reportId.slice(0, 8)}.${format}`
  if (disposition && disposition.includes('filename=')) {
    const match = disposition.match(/filename="?([^";]+)"?/)
    if (match && match[1]) {
      filename = match[1].trim()
    }
  }

  const blob = await response.blob()
  const downloadUrl = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = downloadUrl
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  window.URL.revokeObjectURL(downloadUrl)
}
