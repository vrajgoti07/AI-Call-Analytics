import { useState } from 'react'
import {
  ArrowRight,
  Clock,
  Cpu,
  Layers,
  Loader2,
  RefreshCw,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { MetricCard } from '../components/ui/MetricCard'
import { Button } from '../components/ui/Button'
import { StatusBadge } from '../components/ui/StatusBadge'
import { EmptyState } from '../components/ui/EmptyState'
import { ErrorAlert } from '../components/ui/ErrorAlert'
import { TableSkeleton } from '../components/ui/LoadingSkeleton'
import { useJobs } from '../hooks/useJobs'
import { formatDateTime } from '../lib/utils'

export function JobsPage() {
  const [page, setPage] = useState(1)
  const { data, isLoading, isError, error, refetch } = useJobs(undefined, page, 15)

  if (isError) {
    return (
      <div className="space-y-4">
        <h2 className="text-xl font-bold tracking-tight text-[#17181C]">Processing Jobs</h2>
        <ErrorAlert
          title="Failed to load job tasks"
          message={(error as Error).message}
          onRetry={() => refetch()}
        />
      </div>
    )
  }

  const jobs = data?.items ?? []
  const totalJobs = data?.pagination?.total ?? jobs.length
  const activeJobs = jobs.filter(
    (j) => j.status === 'PROCESSING' || j.status === 'STARTED' || j.status === 'PENDING',
  )
  const completedJobs = jobs.filter((j) => j.status === 'SUCCESS' || j.status === 'COMPLETED')
  const failedJobs = jobs.filter((j) => j.status === 'FAILURE' || j.status === 'FAILED')

  return (
    <div className="space-y-6 animate-in fade-in duration-150">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-[#E5E5E2]">
        <div>
          <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-[#17181C] flex items-center gap-2">
            <Cpu className="h-5 w-5 text-[#6D5AE6]" />
            Background Processing Jobs
          </h2>
          <p className="mt-1 text-xs sm:text-sm text-[#60636B]">
            Real-time Celery worker execution, asynchronous task tracking, and pipeline stage progress
          </p>
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={() => refetch()}
          leftIcon={<RefreshCw className="h-3.5 w-3.5" />}
        >
          Refresh Tasks
        </Button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <MetricCard
          title="Active Processing"
          value={activeJobs.length}
          subtext="Tasks currently running on Celery workers"
          icon={<Loader2 className="h-4 w-4 text-amber-600 animate-spin" />}
          loading={isLoading}
        />
        <MetricCard
          title="Completed Jobs"
          value={completedJobs.length}
          subtext="Successfully finished pipeline tasks"
          icon={<Clock className="h-4 w-4 text-emerald-600" />}
          loading={isLoading}
        />
        <MetricCard
          title="Total Registered Tasks"
          value={totalJobs}
          subtext={`${failedJobs.length} historical failures`}
          icon={<Layers className="h-4 w-4 text-[#6D5AE6]" />}
          loading={isLoading}
        />
      </div>

      {/* Pipeline Stages Legend */}
      <div className="p-4 rounded-xl border border-[#E5E5E2] bg-white shadow-xs flex flex-wrap items-center gap-2 text-xs">
        <span className="text-[#17181C] font-semibold mr-2">Pipeline Execution Sequence:</span>
        <span className="px-2 py-0.5 rounded bg-[#FAFAF9] text-[#17181C] border border-[#E5E5E2] font-mono">1. Preprocess</span>
        <span className="text-[#60636B]">→</span>
        <span className="px-2 py-0.5 rounded bg-[#FAFAF9] text-[#17181C] border border-[#E5E5E2] font-mono">2. Whisper ASR</span>
        <span className="text-[#60636B]">→</span>
        <span className="px-2 py-0.5 rounded bg-[#FAFAF9] text-[#17181C] border border-[#E5E5E2] font-mono">3. Diarization</span>
        <span className="text-[#60636B]">→</span>
        <span className="px-2 py-0.5 rounded bg-[#FAFAF9] text-[#17181C] border border-[#E5E5E2] font-mono">4. NLP Enrichment</span>
        <span className="text-[#60636B]">→</span>
        <span className="px-2 py-0.5 rounded bg-[#FAFAF9] text-[#17181C] border border-[#E5E5E2] font-mono">5. Vector Embeddings</span>
        <span className="text-[#60636B]">→</span>
        <span className="px-2 py-0.5 rounded bg-[#FAFAF9] text-[#17181C] border border-[#E5E5E2] font-mono">6. Escalation Risk</span>
      </div>

      {/* Jobs Table */}
      <div className="rounded-xl border border-[#E5E5E2] bg-white p-5 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-[#17181C]">
            Task Execution Queue
          </h3>
          <span className="text-xs text-[#60636B] font-mono tabular-nums">{jobs.length} jobs shown</span>
        </div>

        {isLoading ? (
          <TableSkeleton rows={6} cols={6} />
        ) : jobs.length > 0 ? (
          <>
            <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="border-b border-[#E5E5E2] bg-[#FAFAF9] text-[#60636B] text-[11px]">
                <tr>
                  <th className="py-2.5 px-3 font-semibold">Job ID</th>
                  <th className="py-2.5 px-3 font-semibold">Call Reference</th>
                  <th className="py-2.5 px-3 font-semibold">Stage / Progress</th>
                  <th className="py-2.5 px-3 font-semibold">Status</th>
                  <th className="py-2.5 px-3 font-semibold font-sans">Created</th>
                  <th className="py-2.5 px-3 text-right font-semibold font-sans">Call Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#EFEFEC]">
                {jobs.map((job) => (
                  <tr key={job.id} className="hover:bg-[#FAFAF9] transition-colors">
                    <td className="py-3.5 px-3 font-semibold text-[#17181C]">
                      {job.id.slice(0, 8)}...
                    </td>
                    <td className="py-3.5 px-3 text-[#6D5AE6]">
                      <Link to={`/calls/${job.call_id}`} className="hover:underline">
                        Call #{job.call_id.slice(0, 8)}
                      </Link>
                    </td>
                    <td className="py-3.5 px-3">
                      <div className="space-y-1">
                        <div className="flex justify-between text-[11px] text-[#17181C]">
                          <span>{job.current_stage || job.job_type}</span>
                          <span className="font-bold tabular-nums">{job.progress}%</span>
                        </div>
                        <div className="w-36 h-1.5 bg-[#EFEFEC] rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all ${
                              job.status === 'FAILURE' || job.status === 'FAILED'
                                ? 'bg-rose-500'
                                : job.status === 'SUCCESS' || job.status === 'COMPLETED'
                                ? 'bg-emerald-500'
                                : 'bg-[#6D5AE6]'
                            }`}
                            style={{ width: `${Math.max(5, job.progress)}%` }}
                          />
                        </div>
                      </div>
                    </td>
                    <td className="py-3.5 px-3">
                      <StatusBadge status={job.status} />
                    </td>
                    <td className="py-3.5 px-3 text-[#60636B] font-sans">
                      {formatDateTime(job.created_at)}
                    </td>
                    <td className="py-3.5 px-3 text-right font-sans">
                      <Link
                        to={`/calls/${job.call_id}`}
                        className="inline-flex items-center gap-1 text-xs text-[#6D5AE6] hover:text-[#5844D6] font-semibold transition-colors"
                      >
                        Inspect Call <ArrowRight className="h-3 w-3" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {data?.pagination && data.pagination.total_pages > 1 && (
            <div className="flex items-center justify-between pt-3 border-t border-[#E5E5E2] font-mono">
              <span className="text-xs text-[#60636B] tabular-nums">
                Page {page} of {data.pagination.total_pages}
              </span>
              <div className="flex gap-2 font-sans">
                <Button
                  size="sm"
                  variant="outline"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                >
                  Previous
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={page >= data.pagination.total_pages}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </>
      ) : (
        <EmptyState
          title="No processing tasks found"
          description="Background Celery tasks will appear here as audio files are uploaded and analyzed."
        />
      )}
      </div>
    </div>
  )
}
