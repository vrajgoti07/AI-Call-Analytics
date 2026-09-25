import React, { useState } from 'react'
import {
  ArrowRight,
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
import { useCalls, useCreateCall, useDeleteCall, useUploadAudio } from '../hooks/useCalls'
import { useStartAnalysis } from '../hooks/useAnalysis'
import { formatBytes, formatDateTime, formatDuration } from '../lib/utils'

export function CallsPage() {
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false)
  const [externalId, setExternalId] = useState('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [autoAnalyze, setAutoAnalyze] = useState(true)
  const [uploadError, setUploadError] = useState<string | null>(null)

  const { data, isLoading, isError, error, refetch } = useCalls({
    page,
    page_size: 15,
    status: statusFilter || undefined,
  })

  const createCallMutation = useCreateCall()
  const uploadAudioMutation = useUploadAudio()
  const startAnalysisMutation = useStartAnalysis()
  const deleteCallMutation = useDeleteCall()

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedFile) {
      setUploadError('Please choose an audio file to upload')
      return
    }
    setUploadError(null)

    try {
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

  return (
    <div className="space-y-6 animate-in fade-in duration-150">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-[#E5E5E2]">
        <div>
          <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-[#17181C]">
            Call Recordings Management
          </h2>
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
            Upload Audio Call
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
          description="Upload an audio recording or clear your active status filters to view calls."
          action={
            <Button size="sm" onClick={() => setIsUploadModalOpen(true)}>
              Upload Audio Call
            </Button>
          }
        />
      )}

      {/* Audio Ingestion Modal */}
      <Modal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        title="Upload Audio Call for Analysis"
      >
        <form onSubmit={handleUploadSubmit} className="space-y-4">
          <Input
            label="External Call Reference (Optional)"
            placeholder="e.g. CRM-CALL-2024-9021"
            value={externalId}
            onChange={(e) => setExternalId(e.target.value)}
            helperText="Custom identifier from telephony or CRM system."
          />

          <div className="space-y-1.5">
            <label className="block text-xs font-medium text-[#17181C]">
              Audio Recording File (.wav, .mp3, .flac)
            </label>
            <div className="border-2 border-dashed border-[#E5E5E2] hover:border-[#6D5AE6] rounded-xl p-6 text-center transition-colors bg-[#FAFAF9]">
              <UploadCloud className="h-8 w-8 text-[#6D5AE6] mx-auto mb-2" />
              <p className="text-xs text-[#17181C] font-medium">
                {selectedFile ? selectedFile.name : 'Click to select or drag audio file here'}
              </p>
              <p className="text-[11px] text-[#60636B] mt-1">
                Max 50MB. 16kHz mono recommended for Whisper & Pyannote.
              </p>
              <input
                type="file"
                accept=".wav,.mp3,.flac,.m4a"
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
              Automatically trigger full AI analysis pipeline upon upload
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
              isLoading={createCallMutation.isPending || uploadAudioMutation.isPending}
            >
              Upload & Ingest
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
