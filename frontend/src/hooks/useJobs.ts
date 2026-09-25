/**
 * AI Call Analytics — Processing Jobs Query Hooks.
 */

import { useQuery } from '@tanstack/react-query'
import { getJob, listJobs } from '../api/jobs'
import type { JobListResponse, JobResponse } from '../api/types'

export function useJobs(callId?: string, page = 1, pageSize = 20) {
  return useQuery<JobListResponse>({
    queryKey: ['jobs', callId, page, pageSize],
    queryFn: () => listJobs(callId, page, pageSize),
    staleTime: 5_000,
    refetchInterval: 5_000, // Background updates for jobs
  })
}

export function useJob(jobId: string | undefined) {
  return useQuery<JobResponse>({
    queryKey: ['job', jobId],
    queryFn: () => {
      if (!jobId) throw new Error('Job ID required')
      return getJob(jobId)
    },
    enabled: Boolean(jobId),
    refetchInterval: (query) => {
      const data = query.state.data
      if (data && (data.status === 'PROCESSING' || data.status === 'PENDING' || data.status === 'STARTED')) {
        return 2000
      }
      return false
    },
  })
}
