import React, { useState } from 'react'
import {
  AlertTriangle,
  ArrowRight,
  Building2,
  CheckCircle2,
  FileArchive,
  FileText,
  Filter,
  PhoneCall,
  Plus,
  RefreshCw,
  Trash2,
  UploadCloud,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { Button } from '../components/ui/Button'
import { StatusBadge } from '../components/ui/StatusBadge'
import { Modal } from '../components/ui/Modal'
import { Input } from '../components/ui/Input'
import { ErrorAlert } from '../components/ui/ErrorAlert'
import { EmptyState } from '../components/ui/EmptyState'
import { TableSkeleton } from '../components/ui/LoadingSkeleton'
import { useCalls, useCreateCall, useDeleteCall, useUploadAudio, useUploadZip } from '../hooks/useCalls'
import { useStartAnalysis } from '../hooks/useAnalysis'
import { useAuthStore } from '../stores/authStore'
import type { BulkIngestResponse } from '../api/types'
import { formatBytes, formatDateTime, formatDuration } from '../lib/utils'

export function CallsPage() {
  const { user } = useAuthStore()
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false)
  const [externalId, setExternalId] = useState('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [autoAnalyze, setAutoAnalyze] = useState(true)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [zipResult, setZipResult] = useState<BulkIngestResponse | null>(null)

  const { data, isLoading, isError, error, refetch } = useCalls({
    page,
    page_size: 15,
    status: statusFilter || undefined,
  })

  const createCallMutation = useCreateCall()
  const uploadAudioMutation = useUploadAudio()
  const uploadZipMutation = useUploadZip()
  const startAnalysisMutation = useStartAnalysis()
  const deleteCallMutation = useDeleteCall()

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedFile) {
      setUploadError('Please choose an audio file or ZIP archive to upload')
      return
    }
    setUploadError(null)

    const isZip = selectedFile.name.toLowerCase().endsWith('.zip')

    try {
      if (isZip) {
        // Bulk ZIP upload
        const result = await uploadZipMutation.mutateAsync({
          file: selectedFile,
          autoAnalyze,
        })
        setZipResult(result)
        setIsUploadModalOpen(false)
        setSelectedFile(null)
        setExternalId('')
        refetch()
      } else {
        // Single Audio upload
        // 1. Create Call
        const call = await createCallMutation.mutateAsync({
          external_id: externalId.trim() || undefined,
          language: 'en',
        })

        // 2. Upload Audio File
        await uploadAudioMutation.mutateAsync({
          callId: call.id,
          file: selectedFile,
        })

        // 3. Trigger Analysis if enabled
        if (autoAnalyze) {
          await startAnalysisMutation.mutateAsync({ callId: call.id })
        }

        setIsUploadModalOpen(false)
        setSelectedFile(null)
        setExternalId('')
        refetch()
      }
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : 'Upload failed')
    }
  }

  const handleDelete = async (callId: string) => {
    if (window.confirm(`Are you sure you want to delete call ${callId}?`)) {
      try {
        await deleteCallMutation.mutateAsync(callId)
      } catch (err) {
        alert(err instanceof Error ? err.message : 'Delete failed')
      }
    }
  }

  const calls = data?.items ?? []
  const pagination = data?.pagination
  const companyName = user?.company?.name || 'Workspace'

  return (
    <div className="space-y-6 animate-in fade-in duration-150">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-[#E5E5E2]">
        <div>
          <div className="flex items-center gap-2.5">
            <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-[#17181C]">
              Call Recordings Management
            </h2>
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#F2F0FD] border border-[#DDD6FE] text-[#5844D6] text-xs font-semibold">
              <Building2 className="h-3.5 w-3.5" />
              <span>{companyName}</span>
            </div>
          </div>
          <p className="mt-1 text-xs sm:text-sm text-[#60636B]">
            Search, filter, and inspect transcribed call conversations and audio files
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
            onClick={() => setIsUploadModalOpen(true)}
            leftIcon={<Plus className="h-4 w-4" />}
          >
            Upload Audio / ZIP
          </Button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="p-4 rounded-xl border border-[#E5E5E2] bg-white shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-[#60636B]" />
          <span className="text-xs font-semibold text-[#17181C]">
            Filter Status:
          </span>
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value)
              setPage(1)
            }}
            aria-label="Filter calls by status"
            className="rounded-lg border border-[#E5E5E2] bg-white px-3 py-1.5 text-xs text-[#17181C] focus:outline-none focus:border-[#6D5AE6] focus:ring-1 focus:ring-[#6D5AE6] cursor-pointer"
          >
            <option value="">All Statuses</option>
            <option value="COMPLETED">Completed</option>
            <option value="PROCESSING">Processing</option>
            <option value="PARTIAL">Partial</option>
            <option value="UPLOADED">Uploaded</option>
            <option value="QUEUED">Queued</option>
            <option value="FAILED">Failed</option>
          </select>
        </div>

        {pagination && (
          <span className="text-xs text-[#60636B] font-mono">
            Showing {(pagination.page - 1) * pagination.page_size + 1} -{' '}
            {Math.min(pagination.page * pagination.page_size, pagination.total)} of{' '}
            {pagination.total} calls
          </span>
        )}
      </div>

      {/* Error state */}
      {isError && (
        <ErrorAlert
          title="Error loading call records"
          message={(error as Error).message}
          onRetry={() => refetch()}
        />
      )}

      {/* Loading state */}
      {isLoading && <TableSkeleton rows={8} cols={6} />}

      {/* Calls Table */}
      {!isLoading && !isError && calls.length > 0 && (
        <div className="rounded-xl border border-[#E5E5E2] bg-white overflow-hidden shadow-xs">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-[#E5E5E2] bg-[#FAFAF9] text-[#60636B] text-[11px] font-semibold">
                <tr>
                  <th className="py-3 px-4">Call ID</th>
                  <th className="py-3 px-4">Audio Filename</th>
                  <th className="py-3 px-4">Duration</th>
                  <th className="py-3 px-4">Language</th>
                  <th className="py-3 px-4">Created At</th>
                  <th className="py-3 px-4">Pipeline Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#EFEFEC]">
                {calls.map((call) => (
                  <tr key={call.id} className="hover:bg-[#FAFAF9] transition-colors">
                    <td className="py-3.5 px-4 font-semibold text-[#6D5AE6] font-mono">
                      <Link to={`/calls/${call.id}`} className="hover:underline">
                        {call.external_id || call.id.slice(0, 8)}
                      </Link>
                    </td>
                    <td className="py-3.5 px-4 text-[#17181C]">
                      {call.audio_file ? (
                        <div className="space-y-0.5">
                          <span className="block truncate max-w-[200px] text-[#17181C] font-medium">
                            {call.audio_file.filename}
                          </span>
                          <span className="text-[10px] text-[#60636B]">
                            {formatBytes(call.audio_file.size)} • {call.audio_file.sample_rate}Hz
                          </span>
                        </div>
                      ) : (
                        <span className="text-[#60636B] italic">No audio uploaded</span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-[#17181C] font-mono tabular-nums">
                      {formatDuration(call.duration ?? call.audio_file?.duration)}
                    </td>
                    <td className="py-3.5 px-4 text-[#60636B] uppercase font-mono">
                      {call.language || 'en'}
                    </td>
                    <td className="py-3.5 px-4 text-[#60636B]">
                      {formatDateTime(call.created_at)}
                    </td>
                    <td className="py-3.5 px-4">
                      <StatusBadge status={call.status} />
                    </td>
                    <td className="py-3.5 px-4 text-right space-x-2">
                      <Link
                        to={`/calls/${call.id}`}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-[#F2F0FD] hover:bg-[#EAE6FD] text-xs text-[#5844D6] font-medium transition-colors"
                      >
                        Inspect <ArrowRight className="h-3 w-3" />
                      </Link>
                      <Link
                        to={`/calls/${call.id}`}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-[#F2F2F0] hover:bg-[#E5E5E2] text-xs text-[#17181C] font-medium transition-colors"
                        title="View & Download Report"
                      >
                        <FileText className="h-3 w-3 text-[#6D5AE6]" />
                        <span>Report</span>
                      </Link>
                      <button
                        type="button"
                        onClick={() => handleDelete(call.id)}
                        className="p-1 text-[#60636B] hover:text-rose-600 rounded hover:bg-rose-50 cursor-pointer transition-colors"
                        title="Delete call"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
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

      {/* Zero Calls Empty State */}
      {!isLoading && !isError && calls.length === 0 && (
        <EmptyState
          icon={<PhoneCall className="h-10 w-10 text-[#60636B]" />}
          title="No calls match your criteria"
          description="Upload an audio recording or ZIP archive to view calls."
          action={
            <Button size="sm" onClick={() => setIsUploadModalOpen(true)}>
              Upload Audio / ZIP
            </Button>
          }
        />
      )}

      {/* Audio / ZIP Ingestion Modal */}
      <Modal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        title="Upload Audio or ZIP Call Archive"
      >
        <form onSubmit={handleUploadSubmit} className="space-y-4">
          <div className="p-3 rounded-lg bg-[#F2F0FD] border border-[#DDD6FE] text-xs text-[#5844D6] flex items-center gap-2">
            <Building2 className="h-4 w-4 shrink-0" />
            <span>Workspace: <strong>{companyName}</strong></span>
          </div>

          <Input
            label="External Call Reference (Optional for single audio)"
            placeholder="e.g. CRM-CALL-2024-9021"
            value={externalId}
            onChange={(e) => setExternalId(e.target.value)}
            helperText="Ignored if uploading a ZIP archive with multiple calls."
          />

          <div className="space-y-1.5">
            <label className="block text-xs font-medium text-[#17181C]">
              Audio Recording (.wav, .mp3, .flac) or Bulk Archive (.zip)
            </label>
            <div className="border-2 border-dashed border-[#E5E5E2] hover:border-[#6D5AE6] rounded-xl p-6 text-center transition-colors bg-[#FAFAF9]">
              {selectedFile?.name.toLowerCase().endsWith('.zip') ? (
                <FileArchive className="h-8 w-8 text-[#6D5AE6] mx-auto mb-2" />
              ) : (
                <UploadCloud className="h-8 w-8 text-[#6D5AE6] mx-auto mb-2" />
              )}
              <p className="text-xs text-[#17181C] font-medium">
                {selectedFile ? selectedFile.name : 'Click to select or drag audio or ZIP archive here'}
              </p>
              <p className="text-[11px] text-[#60636B] mt-1">
                Max 50MB. Audio files will be deduplicated and associated with <strong>{companyName}</strong>.
              </p>
              <input
                type="file"
                accept=".wav,.mp3,.flac,.ogg,.m4a,.zip"
                onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                className="mt-3 text-xs text-[#60636B] file:mr-2 file:py-1 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-[#6D5AE6] file:text-white hover:file:bg-[#5844D6] cursor-pointer"
              />
            </div>
          </div>

          <label className="flex items-center gap-2 cursor-pointer pt-1">
            <input
              type="checkbox"
              checked={autoAnalyze}
              onChange={(e) => setAutoAnalyze(e.target.checked)}
              className="rounded border-[#E5E5E2] text-[#6D5AE6] focus:ring-[#6D5AE6]"
            />
            <span className="text-xs text-[#17181C]">
              Automatically trigger full AI analysis pipeline upon ingestion
            </span>
          </label>

          {uploadError && <p className="text-xs text-rose-600 font-mono">{uploadError}</p>}

          <div className="flex justify-end gap-3 pt-3 border-t border-[#E5E5E2]">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => setIsUploadModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              size="sm"
              isLoading={
                createCallMutation.isPending ||
                uploadAudioMutation.isPending ||
                uploadZipMutation.isPending
              }
            >
              {selectedFile?.name.toLowerCase().endsWith('.zip')
                ? 'Ingest ZIP Archive'
                : 'Upload & Ingest'}
            </Button>
          </div>
        </form>
      </Modal>

      {/* ZIP Ingestion Summary Results Modal */}
      {zipResult && (
        <Modal
          isOpen={true}
          onClose={() => setZipResult(null)}
          title="ZIP Archive Ingestion Summary"
        >
          <div className="space-y-4">
            <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
              <span>
                Ingestion complete: <strong>{zipResult.processed_count}</strong> of{' '}
                <strong>{zipResult.total_files}</strong> calls successfully added to{' '}
                <strong>{companyName}</strong>.
              </span>
            </div>

            {/* Ingested Calls List */}
            {zipResult.created_calls.length > 0 && (
              <div className="space-y-1">
                <span className="text-xs font-semibold text-[#17181C] block">
                  Ingested Calls ({zipResult.created_calls.length}):
                </span>
                <div className="max-h-36 overflow-y-auto rounded-lg border border-[#E5E5E2] p-2 bg-[#FAFAF9] divide-y divide-[#EFEFEC] text-xs">
                  {zipResult.created_calls.map((c) => (
                    <div key={c.id} className="py-1 flex items-center justify-between">
                      <span className="font-mono text-[#6D5AE6] font-medium truncate max-w-[200px]">
                        {c.external_id || c.id.slice(0, 8)}
                      </span>
                      <StatusBadge status={c.status} />
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Skipped / Duplicate Files List */}
            {zipResult.skipped_files.length > 0 && (
              <div className="space-y-1">
                <div className="flex items-center gap-1.5 text-xs font-semibold text-amber-800">
                  <AlertTriangle className="h-3.5 w-3.5 text-amber-600" />
                  <span>Skipped Files ({zipResult.skipped_files.length}):</span>
                </div>
                <div className="max-h-36 overflow-y-auto rounded-lg border border-amber-200 p-2 bg-amber-50/50 divide-y divide-amber-100 text-xs">
                  {zipResult.skipped_files.map((s, idx) => (
                    <div key={idx} className="py-1 flex items-start justify-between gap-2">
                      <span className="font-mono text-[#17181C] truncate max-w-[180px]">
                        {s.filename}
                      </span>
                      <span className="text-[11px] text-amber-700 italic text-right">
                        {s.reason}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="flex justify-end pt-3 border-t border-[#E5E5E2]">
              <Button size="sm" onClick={() => setZipResult(null)}>
                Done
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  )
}
