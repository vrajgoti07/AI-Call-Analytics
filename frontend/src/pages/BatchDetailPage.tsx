import { useState } from 'react'
import {
  ArrowLeft,
  Building2,
  CheckCircle2,
  Download,
  FileArchive,
  FileCode,
  FileSpreadsheet,
  FileText,
  Loader2,
  PhoneCall,
  Play,
  Plus,
  RefreshCw,
  Trash2,
} from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { Button } from '../components/ui/Button'
import { StatusBadge } from '../components/ui/StatusBadge'
import { ErrorAlert } from '../components/ui/ErrorAlert'
import { EmptyState } from '../components/ui/EmptyState'
import { TableSkeleton } from '../components/ui/LoadingSkeleton'
import {
  useAnalyzeBatch,
  useBatch,
  useBatchCalls,
  useBatchReports,
  useGenerateBatchReport,
} from '../hooks/useBatches'
import { useDownloadReport } from '../hooks/useReports'
import { useDeleteCall } from '../hooks/useCalls'
import { useAuthStore } from '../stores/authStore'
import { formatBytes, formatDateTime, formatDuration } from '../lib/utils'

export function BatchDetailPage() {
  const { batchId } = useParams<{ batchId: string }>()
  const { user } = useAuthStore()
  const [activeTab, setActiveTab] = useState<'calls' | 'reports'>('calls')
  const [callPage, setCallPage] = useState(1)
  const [callStatusFilter, setCallStatusFilter] = useState('')
  const [downloadingId, setDownloadingId] = useState<string | null>(null)
  const [notificationMsg, setNotificationMsg] = useState<string | null>(null)

  const {
    data: batch,
    isLoading: isBatchLoading,
    isError: isBatchError,
    error: batchError,
    refetch: refetchBatch,
  } = useBatch(batchId)

  const {
    data: callsData,
    isLoading: isCallsLoading,
    refetch: refetchCalls,
  } = useBatchCalls(batchId, {
    page: callPage,
    page_size: 20,
    status: callStatusFilter || undefined,
  })

  const {
    data: reportsData,
    isLoading: isReportsLoading,
    refetch: refetchReports,
  } = useBatchReports(batchId)

  const analyzeBatchMutation = useAnalyzeBatch()
  const generateReportMutation = useGenerateBatchReport()
  const downloadReportMutation = useDownloadReport()
  const deleteCallMutation = useDeleteCall()

  const handleAnalyze = async () => {
    if (!batchId) return
    try {
      const res = await analyzeBatchMutation.mutateAsync(batchId)
      setNotificationMsg(`Queued ${res.queued_calls} calls for analysis.`)
      setTimeout(() => setNotificationMsg(null), 5000)
      refetchBatch()
      refetchCalls()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to queue batch analysis.')
    }
  }

  const handleGenerateReport = async () => {
    if (!batchId || !batch) return
    try {
      await generateReportMutation.mutateAsync({
        batchId,
        title: `Batch Report — ${batch.display_name}`,
      })
      setNotificationMsg(`Generated report for batch "${batch.display_name}".`)
      setTimeout(() => setNotificationMsg(null), 5000)
      refetchReports()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to generate batch report.')
    }
  }

  const handleDownload = async (reportId: string, format: 'pdf' | 'json' | 'csv') => {
    const key = `${reportId}-${format}`
    setDownloadingId(key)
    try {
      await downloadReportMutation.mutateAsync({ reportId, format })
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Download failed.')
    } finally {
      setDownloadingId(null)
    }
  }

  const handleDeleteCall = async (callId: string) => {
    if (window.confirm(`Delete call ${callId}?`)) {
      try {
        await deleteCallMutation.mutateAsync(callId)
        refetchCalls()
        refetchBatch()
      } catch (err) {
        alert(err instanceof Error ? err.message : 'Failed to delete call.')
      }
    }
  }

  if (isBatchLoading) {
    return (
      <div className="space-y-6">
        <div className="h-8 w-1/3 bg-[#F2F2F0] rounded animate-pulse" />
        <TableSkeleton rows={6} cols={5} />
      </div>
    )
  }

  if (isBatchError || !batch) {
    return (
      <div className="space-y-4">
        <Link to="/batches">
          <Button variant="outline" size="sm" leftIcon={<ArrowLeft className="h-4 w-4" />}>
            Back to Batches
          </Button>
        </Link>
        <ErrorAlert
          title="Batch not found"
          message={(batchError as Error)?.message || 'The requested batch could not be found.'}
          onRetry={() => refetchBatch()}
        />
      </div>
    )
  }

  const calls = callsData?.items ?? []
  const callsPagination = callsData?.pagination
  const reports = reportsData?.items ?? []
  const companyName = user?.company?.name || 'Workspace'

  return (
    <div className="space-y-6 animate-in fade-in duration-150">
      {/* Navigation Breadcrumb / Back */}
      <div className="flex items-center justify-between">
        <Link to="/batches">
          <Button variant="ghost" size="sm" leftIcon={<ArrowLeft className="h-4 w-4" />}>
            Back to All Batches
          </Button>
        </Link>
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#F2F0FD] border border-[#DDD6FE] text-[#5844D6] text-xs font-semibold">
          <Building2 className="h-3.5 w-3.5" />
          <span>{companyName}</span>
        </div>
      </div>

      {/* Notification Toast */}
      {notificationMsg && (
        <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-medium flex items-center justify-between animate-in fade-in">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
            <span>{notificationMsg}</span>
          </div>
          <button onClick={() => setNotificationMsg(null)} className="text-emerald-700 font-bold">
            ✕
          </button>
        </div>
      )}

      {/* Batch Header Card */}
      <div className="p-6 rounded-xl border border-[#E5E5E2] bg-white shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-xl bg-[#F2F0FD] text-[#6D5AE6] shrink-0">
              <FileArchive className="h-6 w-6" />
            </div>
            <div>
              <div className="flex items-center gap-2.5">
                <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-[#17181C]">
                  {batch.display_name}
                </h1>
                <StatusBadge status={batch.status} />
              </div>
              <p className="mt-1 text-xs text-[#8A8D95] font-mono">
                ZIP Source: {batch.original_filename} • Uploaded {formatDateTime(batch.created_at)}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                refetchBatch()
                refetchCalls()
                refetchReports()
              }}
              leftIcon={<RefreshCw className="h-3.5 w-3.5" />}
            >
              Refresh
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleAnalyze}
              disabled={analyzeBatchMutation.isPending}
              leftIcon={
                analyzeBatchMutation.isPending ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Play className="h-3.5 w-3.5 text-emerald-600" />
                )
              }
            >
              Run Batch Analysis
            </Button>
            <Button
              size="sm"
              onClick={handleGenerateReport}
              disabled={generateReportMutation.isPending}
              leftIcon={
                generateReportMutation.isPending ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <FileText className="h-3.5 w-3.5" />
                )
              }
            >
              Generate Batch Report
            </Button>
          </div>
        </div>

        {/* Batch KPI Counters */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-4 border-t border-[#EFEFEC]">
          <div>
            <span className="text-[11px] text-[#8A8D95] uppercase font-semibold">Total Calls</span>
            <div className="mt-1 text-xl font-bold text-[#17181C] font-mono">
              {batch.processed_count}
              <span className="text-xs text-[#8A8D95] font-normal"> / {batch.total_files} files</span>
            </div>
          </div>

          <div>
            <span className="text-[11px] text-[#8A8D95] uppercase font-semibold">Avg Duration</span>
            <div className="mt-1 text-xl font-bold text-[#17181C] font-mono tabular-nums">
              {formatDuration(batch.average_duration)}
            </div>
          </div>

          <div>
            <span className="text-[11px] text-[#8A8D95] uppercase font-semibold">Skipped / Failed</span>
            <div className="mt-1 text-xl font-bold text-[#17181C] font-mono">
              {batch.skipped_count} <span className="text-xs text-[#8A8D95] font-normal">skipped</span>
            </div>
          </div>

          <div>
            <span className="text-[11px] text-[#8A8D95] uppercase font-semibold">Archive Size</span>
            <div className="mt-1 text-xl font-bold text-[#17181C] font-mono">
              {batch.archive_size ? formatBytes(batch.archive_size) : '--'}
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-[#E5E5E2] flex items-center gap-6">
        <button
          onClick={() => setActiveTab('calls')}
          className={`pb-3 text-xs font-semibold flex items-center gap-2 border-b-2 transition-colors ${
            activeTab === 'calls'
              ? 'border-[#6D5AE6] text-[#6D5AE6]'
              : 'border-transparent text-[#60636B] hover:text-[#17181C]'
          }`}
        >
          <PhoneCall className="h-4 w-4" />
          <span>Extracted Calls ({batch.processed_count})</span>
        </button>

        <button
          onClick={() => setActiveTab('reports')}
          className={`pb-3 text-xs font-semibold flex items-center gap-2 border-b-2 transition-colors ${
            activeTab === 'reports'
              ? 'border-[#6D5AE6] text-[#6D5AE6]'
              : 'border-transparent text-[#60636B] hover:text-[#17181C]'
          }`}
        >
          <FileText className="h-4 w-4" />
          <span>Batch Reports ({reports.length})</span>
        </button>
      </div>

      {/* Tab 1: Extracted Calls */}
      {activeTab === 'calls' && (
        <div className="space-y-4">
          {/* Calls Filter */}
          <div className="p-3.5 rounded-xl border border-[#E5E5E2] bg-white shadow-xs flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-[#17181C]">Filter Call Status:</span>
              <select
                value={callStatusFilter}
                onChange={(e) => {
                  setCallStatusFilter(e.target.value)
                  setCallPage(1)
                }}
                className="rounded-lg border border-[#E5E5E2] bg-white px-2.5 py-1 text-xs text-[#17181C] focus:outline-none focus:border-[#6D5AE6]"
              >
                <option value="">All Statuses</option>
                <option value="COMPLETED">Completed</option>
                <option value="PROCESSING">Processing</option>
                <option value="QUEUED">Queued</option>
                <option value="UPLOADED">Uploaded</option>
                <option value="FAILED">Failed</option>
              </select>
            </div>
            {callsPagination && (
              <span className="text-[#8A8D95] font-mono text-[11px]">
                Showing {calls.length} of {callsPagination.total} batch calls
              </span>
            )}
          </div>

          {isCallsLoading ? (
            <TableSkeleton rows={5} cols={5} />
          ) : calls.length > 0 ? (
            <div className="rounded-xl border border-[#E5E5E2] bg-white overflow-hidden shadow-xs">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-[#E5E5E2] bg-[#FAFAF9] text-[#60636B] text-[11px] font-semibold">
                    <tr>
                      <th className="py-3 px-4">Call ID</th>
                      <th className="py-3 px-4">Audio File</th>
                      <th className="py-3 px-4">Duration</th>
                      <th className="py-3 px-4">Status</th>
                      <th className="py-3 px-4">Created</th>
                      <th className="py-3 px-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#EFEFEC]">
                    {calls.map((call) => (
                      <tr key={call.id} className="hover:bg-[#FAFAF9] transition-colors">
                        <td className="py-3 px-4 font-semibold text-[#6D5AE6] font-mono">
                          <Link to={`/calls/${call.id}`} className="hover:underline">
                            {call.external_id || call.id.slice(0, 8)}
                          </Link>
                        </td>
                        <td className="py-3 px-4 text-[#17181C]">
                          <span className="font-medium truncate block max-w-[220px]">
                            {call.audio_file?.filename || call.external_id || 'Recording'}
                          </span>
                        </td>
                        <td className="py-3 px-4 font-mono tabular-nums text-[#17181C]">
                          {formatDuration(call.duration ?? call.audio_file?.duration)}
                        </td>
                        <td className="py-3 px-4">
                          <StatusBadge status={call.status} />
                        </td>
                        <td className="py-3 px-4 text-[#8A8D95]">
                          {formatDateTime(call.created_at)}
                        </td>
                        <td className="py-3 px-4 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <Link to={`/calls/${call.id}`}>
                              <Button variant="outline" size="sm">
                                View Intelligence
                              </Button>
                            </Link>
                            <Button
                              variant="ghost"
                              size="sm"
                              title="Delete Call"
                              onClick={() => handleDeleteCall(call.id)}
                            >
                              <Trash2 className="h-3.5 w-3.5 text-red-500 hover:text-red-700" />
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {callsPagination && callsPagination.total_pages > 1 && (
                <div className="p-3 border-t border-[#E5E5E2] bg-white flex items-center justify-between text-xs">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={callPage <= 1}
                    onClick={() => setCallPage((p) => Math.max(1, p - 1))}
                  >
                    Previous
                  </Button>
                  <span className="text-[#60636B]">
                    Page {callsPagination.page} of {callsPagination.total_pages}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={callPage >= callsPagination.total_pages}
                    onClick={() => setCallPage((p) => Math.min(callsPagination.total_pages, p + 1))}
                  >
                    Next
                  </Button>
                </div>
              )}
            </div>
          ) : (
            <EmptyState
              icon={<PhoneCall className="h-10 w-10 text-[#60636B]" />}
              title="No calls in this batch"
              description="No call recordings match the status filter for this batch."
            />
          )}
        </div>
      )}

      {/* Tab 2: Batch Reports */}
      {activeTab === 'reports' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between p-4 rounded-xl border border-[#E5E5E2] bg-white shadow-xs">
            <div>
              <h3 className="text-sm font-bold text-[#17181C]">Batch Intelligence Artifacts</h3>
              <p className="text-xs text-[#60636B]">
                Downloadable executive analytics compiled strictly for the {batch.processed_count} calls in this ZIP.
              </p>
            </div>
            <Button
              size="sm"
              onClick={handleGenerateReport}
              disabled={generateReportMutation.isPending}
              leftIcon={<Plus className="h-4 w-4" />}
            >
              Generate New Batch Report
            </Button>
          </div>

          {isReportsLoading ? (
            <TableSkeleton rows={4} cols={4} />
          ) : reports.length > 0 ? (
            <div className="rounded-xl border border-[#E5E5E2] bg-white overflow-hidden shadow-xs">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-[#E5E5E2] bg-[#FAFAF9] text-[#60636B] text-[11px] font-semibold">
                    <tr>
                      <th className="py-3 px-4">Report Title</th>
                      <th className="py-3 px-4">Type</th>
                      <th className="py-3 px-4">Status</th>
                      <th className="py-3 px-4">Generated At</th>
                      <th className="py-3 px-4 text-right">Download Formats</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#EFEFEC]">
                    {reports.map((report) => (
                      <tr key={report.id} className="hover:bg-[#FAFAF9] transition-colors">
                        <td className="py-3.5 px-4 font-semibold text-[#17181C]">
                          <div className="flex items-center gap-2">
                            <FileText className="h-4 w-4 text-[#6D5AE6] shrink-0" />
                            <span>{report.title}</span>
                          </div>
                        </td>
                        <td className="py-3.5 px-4 text-[#60636B] font-mono text-[11px]">
                          {report.report_type}
                        </td>
                        <td className="py-3.5 px-4">
                          <StatusBadge status={report.status} />
                        </td>
                        <td className="py-3.5 px-4 text-[#8A8D95]">
                          {formatDateTime(report.created_at)}
                        </td>
                        <td className="py-3.5 px-4 text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            <Button
                              variant="outline"
                              size="sm"
                              disabled={downloadingId === `${report.id}-pdf`}
                              onClick={() => handleDownload(report.id, 'pdf')}
                              leftIcon={<Download className="h-3 w-3" />}
                            >
                              PDF
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              disabled={downloadingId === `${report.id}-csv`}
                              onClick={() => handleDownload(report.id, 'csv')}
                              leftIcon={<FileSpreadsheet className="h-3 w-3 text-emerald-600" />}
                            >
                              CSV
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              disabled={downloadingId === `${report.id}-json`}
                              onClick={() => handleDownload(report.id, 'json')}
                              leftIcon={<FileCode className="h-3 w-3 text-amber-600" />}
                            >
                              JSON
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <EmptyState
              icon={<FileText className="h-10 w-10 text-[#60636B]" />}
              title="No reports generated yet"
              description="Generate a batch-level PDF, CSV, and JSON report specifically analyzing this ZIP archive."
              action={
                <Button size="sm" onClick={handleGenerateReport}>
                  Generate First Batch Report
                </Button>
              }
            />
          )}
        </div>
      )}
    </div>
  )
}
