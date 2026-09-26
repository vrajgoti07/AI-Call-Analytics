import React, { useState } from 'react'
import {
  AlertTriangle,
  ArrowRight,
  Building2,
  CheckCircle2,
  FileArchive,
  FileText,
  Filter,
  Layers,
  Loader2,
  Play,
  Plus,
  RefreshCw,
  Search,
  UploadCloud,
} from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { Button } from '../components/ui/Button'
import { StatusBadge } from '../components/ui/StatusBadge'
import { Modal } from '../components/ui/Modal'
import { ErrorAlert } from '../components/ui/ErrorAlert'
import { EmptyState } from '../components/ui/EmptyState'
import { TableSkeleton } from '../components/ui/LoadingSkeleton'
import {
  useAnalyzeBatch,
  useBatches,
  useGenerateBatchReport,
} from '../hooks/useBatches'
import { useUploadZip } from '../hooks/useCalls'
import { useAuthStore } from '../stores/authStore'
import type { BulkIngestResponse } from '../api/types'
import { formatBytes, formatDateTime } from '../lib/utils'

export function BatchesPage() {
  const { user } = useAuthStore()
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [searchQuery, setSearchQuery] = useState('')
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [autoAnalyze, setAutoAnalyze] = useState(true)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [uploadSuccess, setUploadSuccess] = useState<BulkIngestResponse | null>(null)
  const [actionMessage, setActionMessage] = useState<string | null>(null)

  const { data, isLoading, isError, error, refetch } = useBatches({
    page,
    page_size: 15,
    status: statusFilter || undefined,
    search: searchQuery.trim() || undefined,
  })

  const uploadZipMutation = useUploadZip()
  const analyzeBatchMutation = useAnalyzeBatch()
  const generateReportMutation = useGenerateBatchReport()

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedFile) {
      setUploadError('Please choose a ZIP archive to upload.')
      return
    }
    if (!selectedFile.name.toLowerCase().endsWith('.zip')) {
      setUploadError('Only ZIP archives (.zip) are supported for batch ingestion.')
      return
    }
    setUploadError(null)

    try {
      const result = await uploadZipMutation.mutateAsync({
        file: selectedFile,
        autoAnalyze,
      })
      setUploadSuccess(result)
      setSelectedFile(null)
      refetch()
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : 'ZIP upload failed.')
    }
  }

  const handleAnalyzeBatch = async (batchId: string, batchName: string) => {
    try {
      const res = await analyzeBatchMutation.mutateAsync(batchId)
      setActionMessage(`Queued ${res.queued_calls} calls in batch "${batchName}" for processing.`)
      setTimeout(() => setActionMessage(null), 5000)
      refetch()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to trigger batch analysis.')
    }
  }

  const handleGenerateReport = async (batchId: string, batchName: string) => {
    try {
      await generateReportMutation.mutateAsync({
        batchId,
        title: `Batch Report — ${batchName}`,
      })
      setActionMessage(`Generated analytics report for batch "${batchName}".`)
      setTimeout(() => setActionMessage(null), 5000)
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to generate batch report.')
    }
  }

  const batches = data?.items ?? []
  const pagination = data?.pagination
  const companyName = user?.company?.name || 'Workspace'

  // Summary Metrics
  const totalBatches = pagination?.total ?? batches.length
  const totalCallsIngested = batches.reduce((acc, b) => acc + (b.processed_count || 0), 0)
  const activeBatchesCount = batches.filter(
    (b) => b.status === 'PROCESSING' || b.status === 'UPLOADING',
  ).length
  const completedBatchesCount = batches.filter((b) => b.status === 'COMPLETED').length

  return (
    <div className="space-y-6 animate-in fade-in duration-150">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-[#E5E5E2]">
        <div>
          <div className="flex items-center gap-2.5">
            <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-[#17181C]">
              ZIP Ingestion Batches
            </h2>
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#F2F0FD] border border-[#DDD6FE] text-[#5844D6] text-xs font-semibold">
              <Building2 className="h-3.5 w-3.5" />
              <span>{companyName}</span>
            </div>
          </div>
          <p className="mt-1 text-xs sm:text-sm text-[#60636B]">
            Independent datasets partitioned per ZIP upload with batch-specific metrics and reporting
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
            onClick={() => {
              setUploadSuccess(null)
              setUploadError(null)
              setIsUploadModalOpen(true)
            }}
            leftIcon={<Plus className="h-4 w-4" />}
          >
            Upload New ZIP
          </Button>
        </div>
      </div>

      {/* Action Notification Toast */}
      {actionMessage && (
        <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-medium flex items-center justify-between animate-in fade-in">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
            <span>{actionMessage}</span>
          </div>
          <button
            onClick={() => setActionMessage(null)}
            className="text-emerald-700 hover:text-emerald-900 text-xs font-bold"
          >
            ✕
          </button>
        </div>
      )}

      {/* KPI Cards Overview */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl border border-[#E5E5E2] bg-white shadow-xs">
          <div className="flex items-center justify-between text-[#60636B]">
            <span className="text-xs font-medium">Total Batches</span>
            <FileArchive className="h-4 w-4 text-[#6D5AE6]" />
          </div>
          <div className="mt-2 text-2xl font-bold tracking-tight text-[#17181C]">
            {totalBatches}
          </div>
          <div className="mt-1 text-[11px] text-[#8A8D95]">Independent ZIP archives</div>
        </div>

        <div className="p-4 rounded-xl border border-[#E5E5E2] bg-white shadow-xs">
          <div className="flex items-center justify-between text-[#60636B]">
            <span className="text-xs font-medium">Total Calls Ingested</span>
            <Layers className="h-4 w-4 text-blue-600" />
          </div>
          <div className="mt-2 text-2xl font-bold tracking-tight text-[#17181C]">
            {totalCallsIngested}
          </div>
          <div className="mt-1 text-[11px] text-[#8A8D95]">Extracted call recordings</div>
        </div>

        <div className="p-4 rounded-xl border border-[#E5E5E2] bg-white shadow-xs">
          <div className="flex items-center justify-between text-[#60636B]">
            <span className="text-xs font-medium">Active Processing</span>
            <Loader2 className={`h-4 w-4 text-amber-500 ${activeBatchesCount > 0 ? 'animate-spin' : ''}`} />
          </div>
          <div className="mt-2 text-2xl font-bold tracking-tight text-[#17181C]">
            {activeBatchesCount}
          </div>
          <div className="mt-1 text-[11px] text-[#8A8D95]">Batches being transcribed</div>
        </div>

        <div className="p-4 rounded-xl border border-[#E5E5E2] bg-white shadow-xs">
          <div className="flex items-center justify-between text-[#60636B]">
            <span className="text-xs font-medium">Completed Batches</span>
            <CheckCircle2 className="h-4 w-4 text-emerald-600" />
          </div>
          <div className="mt-2 text-2xl font-bold tracking-tight text-[#17181C]">
            {completedBatchesCount}
          </div>
          <div className="mt-1 text-[11px] text-[#8A8D95]">Ready for analysis & reports</div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="p-4 rounded-xl border border-[#E5E5E2] bg-white shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3">
          {/* Search */}
          <div className="relative min-w-[240px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-[#8A8D95]" />
            <input
              type="text"
              placeholder="Search by filename or batch name..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value)
                setPage(1)
              }}
              className="w-full pl-9 pr-3 py-1.5 rounded-lg border border-[#E5E5E2] bg-white text-xs text-[#17181C] placeholder:text-[#8A8D95] focus:outline-none focus:border-[#6D5AE6] focus:ring-1 focus:ring-[#6D5AE6]"
            />
          </div>

          {/* Status Filter */}
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-[#60636B]" />
            <span className="text-xs font-semibold text-[#17181C]">Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value)
                setPage(1)
              }}
              aria-label="Filter batches by status"
              className="rounded-lg border border-[#E5E5E2] bg-white px-3 py-1.5 text-xs text-[#17181C] focus:outline-none focus:border-[#6D5AE6] focus:ring-1 focus:ring-[#6D5AE6] cursor-pointer"
            >
              <option value="">All Statuses</option>
              <option value="COMPLETED">Completed</option>
              <option value="PROCESSING">Processing</option>
              <option value="PARTIAL">Partial</option>
              <option value="UPLOADING">Uploading</option>
              <option value="FAILED">Failed</option>
            </select>
          </div>
        </div>

        {pagination && (
          <span className="text-xs text-[#60636B] font-mono">
            Showing {(pagination.page - 1) * pagination.page_size + 1} -{' '}
            {Math.min(pagination.page * pagination.page_size, pagination.total)} of{' '}
            {pagination.total} batches
          </span>
        )}
      </div>

      {/* Error state */}
      {isError && (
        <ErrorAlert
          title="Error loading batch archives"
          message={(error as Error).message}
          onRetry={() => refetch()}
        />
      )}

      {/* Loading state */}
      {isLoading && <TableSkeleton rows={6} cols={6} />}

      {/* Batches Table / Grid */}
      {!isLoading && !isError && batches.length > 0 && (
        <div className="rounded-xl border border-[#E5E5E2] bg-white overflow-hidden shadow-xs">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-[#E5E5E2] bg-[#FAFAF9] text-[#60636B] text-[11px] font-semibold">
                <tr>
                  <th className="py-3 px-4">Batch / Archive Name</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Files Extracted</th>
                  <th className="py-3 px-4">Skipped / Failed</th>
                  <th className="py-3 px-4">Uploaded Date</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#EFEFEC]">
                {batches.map((batch) => {
                  const isProcessing = batch.status === 'PROCESSING' || batch.status === 'UPLOADING'
                  return (
                    <tr key={batch.id} className="hover:bg-[#FAFAF9] transition-colors">
                      <td className="py-3.5 px-4 font-semibold text-[#17181C]">
                        <div className="flex items-center gap-2.5">
                          <div className="p-2 rounded-lg bg-[#F2F0FD] text-[#6D5AE6] shrink-0">
                            <FileArchive className="h-4 w-4" />
                          </div>
                          <div className="min-w-0">
                            <Link
                              to={`/batches/${batch.id}`}
                              className="font-medium text-sm text-[#17181C] hover:text-[#6D5AE6] hover:underline truncate block"
                            >
                              {batch.display_name}
                            </Link>
                            <span className="text-[11px] text-[#8A8D95] font-mono flex items-center gap-2">
                              <span>{batch.original_filename}</span>
                              {batch.archive_size && (
                                <span>• {formatBytes(batch.archive_size)}</span>
                              )}
                            </span>
                          </div>
                        </div>
                      </td>
                      <td className="py-3.5 px-4">
                        <StatusBadge status={batch.status} />
                      </td>
                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-[#17181C] text-sm">
                            {batch.processed_count}
                          </span>
                          <span className="text-[11px] text-[#8A8D95]">
                            / {batch.total_files} audio calls
                          </span>
                        </div>
                      </td>
                      <td className="py-3.5 px-4 text-[#8A8D95]">
                        {batch.skipped_count > 0 || batch.failed_count > 0 ? (
                          <span className="text-amber-700 bg-amber-50 px-2 py-0.5 rounded text-[11px] font-medium border border-amber-200">
                            {batch.skipped_count} skipped, {batch.failed_count} failed
                          </span>
                        ) : (
                          <span className="text-emerald-700 text-[11px]">0 skipped</span>
                        )}
                      </td>
                      <td className="py-3.5 px-4 text-[#60636B]">
                        {formatDateTime(batch.created_at)}
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Link to={`/batches/${batch.id}`}>
                            <Button variant="outline" size="sm" rightIcon={<ArrowRight className="h-3 w-3" />}>
                              View Folder
                            </Button>
                          </Link>
                          <Button
                            variant="ghost"
                            size="sm"
                            title="Generate Batch Report"
                            onClick={() => handleGenerateReport(batch.id, batch.display_name)}
                            leftIcon={<FileText className="h-3.5 w-3.5 text-blue-600" />}
                          >
                            Report
                          </Button>
                          {isProcessing && (
                            <Button
                              variant="ghost"
                              size="sm"
                              title="Process Calls"
                              onClick={() => handleAnalyzeBatch(batch.id, batch.display_name)}
                              leftIcon={<Play className="h-3.5 w-3.5 text-emerald-600" />}
                            >
                              Run
                            </Button>
                          )}
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination Controls */}
          {pagination && pagination.total_pages > 1 && (
            <div className="p-3 border-t border-[#E5E5E2] bg-white flex items-center justify-between">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                Previous
              </Button>
              <span className="text-xs text-[#60636B]">
                Page {pagination.page} of {pagination.total_pages}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= pagination.total_pages}
                onClick={() => setPage((p) => Math.min(pagination.total_pages, p + 1))}
              >
                Next
              </Button>
            </div>
          )}
        </div>
      )}

      {/* Empty State */}
      {!isLoading && !isError && batches.length === 0 && (
        <EmptyState
          icon={<FileArchive className="h-10 w-10 text-[#60636B]" />}
          title="No ingestion batches found"
          description={
            statusFilter || searchQuery
              ? 'No batches match your selected search or filter criteria.'
              : 'Upload your first call recordings ZIP archive to organize calls into an independent dataset batch.'
          }
          action={
            <Button
              onClick={() => setIsUploadModalOpen(true)}
              leftIcon={<Plus className="h-4 w-4" />}
            >
              Upload First ZIP Archive
            </Button>
          }
        />
      )}

      {/* Upload ZIP Modal */}
      <Modal
        isOpen={isUploadModalOpen}
        onClose={() => {
          setIsUploadModalOpen(false)
          setSelectedFile(null)
          setUploadSuccess(null)
          setUploadError(null)
        }}
        title="Upload Audio ZIP Archive"
      >
        {uploadSuccess ? (
          <div className="space-y-4 py-2">
            <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-900">
              <div className="flex items-center gap-2 font-semibold">
                <CheckCircle2 className="h-5 w-5 text-emerald-600" />
                <span>ZIP Ingestion Successful</span>
              </div>
              <p className="mt-1 text-xs text-emerald-800">
                Created new logical batch: <b>{uploadSuccess.batch_name || 'Upload Batch'}</b>
              </p>
              <div className="mt-3 grid grid-cols-2 gap-2 text-xs border-t border-emerald-200 pt-3">
                <div>
                  <span className="text-emerald-700">Processed Calls:</span>{' '}
                  <span className="font-bold">{uploadSuccess.processed_count}</span>
                </div>
                <div>
                  <span className="text-emerald-700">Skipped Files:</span>{' '}
                  <span className="font-bold">{uploadSuccess.skipped_files.length}</span>
                </div>
              </div>
            </div>

            {uploadSuccess.skipped_files.length > 0 && (
              <div className="p-3 rounded-lg bg-amber-50 border border-amber-200 text-xs text-amber-900 space-y-1 max-h-32 overflow-y-auto">
                <div className="font-semibold flex items-center gap-1.5 text-amber-800">
                  <AlertTriangle className="h-3.5 w-3.5" />
                  <span>Skipped Non-Audio / Duplicate Files:</span>
                </div>
                {uploadSuccess.skipped_files.map((s, idx) => (
                  <div key={idx} className="font-mono text-[11px] text-amber-700">
                    • {s.filename}: {s.reason}
                  </div>
                ))}
              </div>
            )}

            <div className="flex justify-end gap-3 pt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setIsUploadModalOpen(false)
                  setUploadSuccess(null)
                }}
              >
                Close
              </Button>
              {uploadSuccess.batch_id && (
                <Button
                  size="sm"
                  onClick={() => {
                    setIsUploadModalOpen(false)
                    navigate(`/batches/${uploadSuccess.batch_id}`)
                  }}
                  rightIcon={<ArrowRight className="h-3.5 w-3.5" />}
                >
                  View Ingestion Batch
                </Button>
              )}
            </div>
          </div>
        ) : (
          <form onSubmit={handleUploadSubmit} className="space-y-4">
            {uploadError && <ErrorAlert title="Upload Error" message={uploadError} />}

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-[#17181C]">
                ZIP Archive (.zip) <span className="text-red-500">*</span>
              </label>
              <div className="border-2 border-dashed border-[#E5E5E2] rounded-xl p-6 text-center hover:border-[#6D5AE6] transition-colors bg-[#FAFAF9]">
                <UploadCloud className="h-8 w-8 mx-auto text-[#8A8D95] mb-2" />
                <input
                  type="file"
                  accept=".zip"
                  onChange={(e) => {
                    const f = e.target.files?.[0]
                    setSelectedFile(f || null)
                    setUploadError(null)
                  }}
                  className="block w-full text-xs text-[#60636B] file:mr-4 file:py-1.5 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-[#F2F0FD] file:text-[#6D5AE6] hover:file:bg-[#EAE6FC] cursor-pointer"
                />
                <p className="mt-2 text-[11px] text-[#8A8D95]">
                  Accepts ZIP archives containing .wav, .mp3, or .flac call recordings (max 250MB).
                </p>
              </div>
              {selectedFile && (
                <div className="flex items-center gap-2 p-2 rounded-lg bg-white border border-[#E5E5E2] text-xs font-mono">
                  <FileArchive className="h-4 w-4 text-[#6D5AE6]" />
                  <span className="truncate font-medium">{selectedFile.name}</span>
                  <span className="text-[#8A8D95] ml-auto">({formatBytes(selectedFile.size)})</span>
                </div>
              )}
            </div>

            <div className="flex items-center gap-2 pt-1">
              <input
                type="checkbox"
                id="batchAutoAnalyze"
                checked={autoAnalyze}
                onChange={(e) => setAutoAnalyze(e.target.checked)}
                className="h-4 w-4 rounded border-[#E5E5E2] text-[#6D5AE6] focus:ring-[#6D5AE6]"
              />
              <label htmlFor="batchAutoAnalyze" className="text-xs text-[#17181C] cursor-pointer">
                Automatically run AI analysis pipeline (transcription, diarization, risk) for all extracted calls
              </label>
            </div>

            <div className="flex justify-end gap-3 pt-3 border-t border-[#E5E5E2]">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => {
                  setIsUploadModalOpen(false)
                  setSelectedFile(null)
                  setUploadError(null)
                }}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                size="sm"
                disabled={!selectedFile || uploadZipMutation.isPending}
                leftIcon={
                  uploadZipMutation.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <UploadCloud className="h-4 w-4" />
                  )
                }
              >
                {uploadZipMutation.isPending ? 'Ingesting ZIP...' : 'Upload & Extract Batch'}
              </Button>
            </div>
          </form>
        )}
      </Modal>
    </div>
  )
}
