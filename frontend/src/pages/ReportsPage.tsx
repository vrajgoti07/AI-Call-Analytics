import { useState } from 'react'
import {
  AlertCircle,
  Building2,
  CheckCircle2,
  Download,
  FileCode,
  FileSpreadsheet,
  FileText,
  Loader2,
  Plus,
  RefreshCw,
} from 'lucide-react'
import { Button } from '../components/ui/Button'
import { Modal } from '../components/ui/Modal'
import { Input } from '../components/ui/Input'
import { ErrorAlert } from '../components/ui/ErrorAlert'
import { EmptyState } from '../components/ui/EmptyState'
import { TableSkeleton } from '../components/ui/LoadingSkeleton'
import { useAuthStore } from '../stores/authStore'
import { useDownloadReport, useGenerateReport, useReports } from '../hooks/useReports'
import { formatDateTime } from '../lib/utils'

export function ReportsPage() {
  const { user } = useAuthStore()
  const [page, setPage] = useState(1)
  const [isGenerateModalOpen, setIsGenerateModalOpen] = useState(false)
  const [reportType, setReportType] = useState('COMPANY_ANALYTICS')
  const [customTitle, setCustomTitle] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [downloadingId, setDownloadingId] = useState<string | null>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  const { data, isLoading, isError, error, refetch } = useReports({
    page,
    page_size: 15,
  })

  const generateReportMutation = useGenerateReport()
  const downloadReportMutation = useDownloadReport()

  const handleGenerateSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setErrorMsg(null)

    try {
      await generateReportMutation.mutateAsync({
        report_type: reportType,
        title: customTitle.trim() || undefined,
        date_from: dateFrom ? new Date(dateFrom).toISOString() : undefined,
        date_to: dateTo ? new Date(dateTo).toISOString() : undefined,
      })
      setIsGenerateModalOpen(false)
      setCustomTitle('')
      setDateFrom('')
      setDateTo('')
      refetch()
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Report generation failed')
    }
  }

  const handleDownload = async (reportId: string, format: 'pdf' | 'json' | 'csv') => {
    const key = `${reportId}-${format}`
    setDownloadingId(key)
    try {
      await downloadReportMutation.mutateAsync({ reportId, format })
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Download failed')
    } finally {
      setDownloadingId(null)
    }
  }

  const reports = data?.items ?? []
  const pagination = data?.pagination
  const companyName = user?.company?.name || 'Workspace'

  return (
    <div className="space-y-6 animate-in fade-in duration-150">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-[#E5E5E2]">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-[#17181C]">
              Intelligence Reports & Analytics
            </h2>
            <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-[#F2F0FD] border border-[#DDD6FE] text-[#5844D6] text-xs font-semibold">
              <Building2 className="h-3 w-3" />
              <span>{companyName}</span>
            </div>
          </div>
          <p className="mt-1 text-xs sm:text-sm text-[#60636B]">
            Generate and export company executive summaries and individual call reports
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            leftIcon={<RefreshCw className="h-3.5 w-3.5" />}
          >
            Refresh
          </Button>
          <Button
            size="sm"
            onClick={() => setIsGenerateModalOpen(true)}
            leftIcon={<Plus className="h-4 w-4" />}
          >
            Generate Report
          </Button>
        </div>
      </div>

      {/* Error state */}
      {isError && (
        <ErrorAlert
          title="Error loading report history"
          message={(error as Error).message}
          onRetry={() => refetch()}
        />
      )}

      {/* Loading state */}
      {isLoading && <TableSkeleton rows={6} cols={5} />}

      {/* Reports Table */}
      {!isLoading && !isError && reports.length > 0 && (
        <div className="rounded-xl border border-[#E5E5E2] bg-white overflow-hidden shadow-xs">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-[#E5E5E2] bg-[#FAFAF9] text-[#60636B] text-[11px] font-semibold">
                <tr>
                  <th className="py-3 px-4">Report Title</th>
                  <th className="py-3 px-4">Scope</th>
                  <th className="py-3 px-4">Generated At</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Download Formats</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#EFEFEC]">
                {reports.map((report) => {
                  const isCompleted = report.status === 'COMPLETED'
                  const isGenerating = report.status === 'GENERATING' || report.status === 'PENDING'
                  const isFailed = report.status === 'FAILED'

                  return (
                    <tr key={report.id} className="hover:bg-[#FAFAF9] transition-colors">
                      <td className="py-3.5 px-4 font-semibold text-[#17181C]">
                        <div className="flex items-center gap-2">
                          <FileText className="h-4 w-4 text-[#6D5AE6] shrink-0" />
                          <span className="truncate max-w-[280px]">{report.title}</span>
                        </div>
                      </td>
                      <td className="py-3.5 px-4 text-[#60636B]">
                        <span className="px-2 py-0.5 rounded-full bg-neutral-100 text-[10px] font-mono font-medium uppercase text-neutral-700">
                          {report.report_type.replace('_', ' ')}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-[#60636B]">
                        {formatDateTime(report.created_at)}
                      </td>
                      <td className="py-3.5 px-4">
                        {isCompleted && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 text-[10px] font-medium font-mono">
                            <CheckCircle2 className="h-3 w-3" /> Ready
                          </span>
                        )}
                        {isGenerating && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200 text-[10px] font-medium font-mono animate-pulse">
                            <Loader2 className="h-3 w-3 animate-spin" /> Generating
                          </span>
                        )}
                        {isFailed && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-rose-50 text-rose-700 border border-rose-200 text-[10px] font-medium font-mono">
                            <AlertCircle className="h-3 w-3" /> Failed
                          </span>
                        )}
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        {isCompleted ? (
                          <div className="inline-flex items-center gap-1.5">
                            <button
                              type="button"
                              onClick={() => handleDownload(report.id, 'pdf')}
                              disabled={downloadingId === `${report.id}-pdf`}
                              className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-[#6D5AE6] text-white hover:bg-[#5844D6] text-xs font-medium cursor-pointer transition-colors shadow-2xs"
                              title="Download PDF format"
                            >
                              {downloadingId === `${report.id}-pdf` ? (
                                <Loader2 className="h-3 w-3 animate-spin" />
                              ) : (
                                <Download className="h-3 w-3" />
                              )}
                              <span>PDF</span>
                            </button>

                            <button
                              type="button"
                              onClick={() => handleDownload(report.id, 'json')}
                              disabled={downloadingId === `${report.id}-json`}
                              className="inline-flex items-center gap-1 px-2 py-1 rounded bg-neutral-100 text-neutral-700 hover:bg-neutral-200 text-xs font-medium cursor-pointer transition-colors"
                              title="Download JSON telemetry"
                            >
                              <FileCode className="h-3 w-3 text-neutral-500" />
                              <span>JSON</span>
                            </button>

                            <button
                              type="button"
                              onClick={() => handleDownload(report.id, 'csv')}
                              disabled={downloadingId === `${report.id}-csv`}
                              className="inline-flex items-center gap-1 px-2 py-1 rounded bg-neutral-100 text-neutral-700 hover:bg-neutral-200 text-xs font-medium cursor-pointer transition-colors"
                              title="Download CSV spreadsheet"
                            >
                              <FileSpreadsheet className="h-3 w-3 text-neutral-500" />
                              <span>CSV</span>
                            </button>
                          </div>
                        ) : (
                          <span className="text-xs text-neutral-400 italic">Processing</span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination Controls */}
          {pagination && pagination.total_pages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-[#E5E5E2] bg-[#FAFAF9]">
              <span className="text-xs text-[#60636B] font-mono">
                Page {pagination.page} of {pagination.total_pages}
              </span>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page >= pagination.total_pages}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Zero Reports Empty State */}
      {!isLoading && !isError && reports.length === 0 && (
        <EmptyState
          icon={<FileText className="h-10 w-10 text-[#60636B]" />}
          title="No reports generated yet"
          description={`Compile and export call intelligence reports for ${companyName} in PDF, JSON, or CSV.`}
          action={
            <Button size="sm" onClick={() => setIsGenerateModalOpen(true)}>
              Generate Company Report
            </Button>
          }
        />
      )}

      {/* Generation Modal */}
      <Modal
        isOpen={isGenerateModalOpen}
        onClose={() => setIsGenerateModalOpen(false)}
        title="Generate Intelligence Report"
      >
        <form onSubmit={handleGenerateSubmit} className="space-y-4">
          <div className="p-3 rounded-lg bg-[#F2F0FD] border border-[#DDD6FE] text-xs text-[#5844D6] flex items-center gap-2">
            <Building2 className="h-4 w-4 shrink-0" />
            <span>Generating report for workspace: <strong>{companyName}</strong></span>
          </div>

          <div>
            <label className="block text-xs font-medium text-[#17181C] mb-1">
              Report Scope
            </label>
            <select
              value={reportType}
              onChange={(e) => setReportType(e.target.value)}
              className="w-full rounded-lg border border-[#E5E5E2] bg-white px-3 py-2 text-xs text-[#17181C] focus:outline-none focus:border-[#6D5AE6] focus:ring-1 focus:ring-[#6D5AE6] cursor-pointer"
            >
              <option value="COMPANY_ANALYTICS">Executive Summary & All Calls</option>
              <option value="DATE_RANGE">Date-Range Filtered Analysis</option>
            </select>
          </div>

          <Input
            label="Report Title (Optional)"
            placeholder={`e.g. ${companyName} Q3 Operational Intelligence Review`}
            value={customTitle}
            onChange={(e) => setCustomTitle(e.target.value)}
            helperText="Leave empty for an automatic date-stamped title."
          />

          {reportType === 'DATE_RANGE' && (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-[#17181C] mb-1">
                  From Date
                </label>
                <input
                  type="date"
                  value={dateFrom}
                  onChange={(e) => setDateFrom(e.target.value)}
                  className="w-full rounded-lg border border-[#E5E5E2] bg-white px-3 py-1.5 text-xs text-[#17181C] focus:outline-none focus:border-[#6D5AE6]"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-[#17181C] mb-1">
                  To Date
                </label>
                <input
                  type="date"
                  value={dateTo}
                  onChange={(e) => setDateTo(e.target.value)}
                  className="w-full rounded-lg border border-[#E5E5E2] bg-white px-3 py-1.5 text-xs text-[#17181C] focus:outline-none focus:border-[#6D5AE6]"
                />
              </div>
            </div>
          )}

          {errorMsg && <p className="text-xs text-rose-600 font-mono">{errorMsg}</p>}

          <div className="flex justify-end gap-3 pt-3 border-t border-[#E5E5E2]">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => setIsGenerateModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              size="sm"
              isLoading={generateReportMutation.isPending}
            >
              Compile & Generate
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
