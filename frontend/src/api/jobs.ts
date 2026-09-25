/**
 * AI Call Analytics — Processing Jobs API Service.
 */

import { apiClient } from './client'
import type { JobListResponse, JobResponse } from './types'

export async function listJobs(callId?: string, page = 1, pageSize = 20): Promise<JobListResponse> {
  return apiClient<JobListResponse>('/api/v1/jobs', {
    params: {
      call_id: callId,
      page,
      page_size: pageSize,
    },
  })
}

export async function getJob(jobId: string): Promise<JobResponse> {
  return apiClient<JobResponse>(`/api/v1/jobs/${jobId}`)
}
