import { useState } from 'react'
import {
  AlertCircle,
  ArrowLeft,
  Calendar,
  CheckCircle2,
  Clock,
  Download,
  FileArchive,
  FileCode,
  FileSpreadsheet,
  FileText,
  Globe,
  Loader2,
  PlayCircle,
  RefreshCw,
} from 'lucide-react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { AudioPlayerDock } from '../components/audio/AudioPlayerDock'
import { TranscriptViewer } from '../components/transcript/TranscriptViewer'
import { RiskScoreCard } from '../components/risk/RiskScoreCard'
import { StatusBadge } from '../components/ui/StatusBadge'
import { SentimentBadge } from '../components/ui/SentimentBadge'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { ErrorAlert } from '../components/ui/ErrorAlert'
import { useCall } from '../hooks/useCall'
import { useTranscript, useTranscriptTurns } from '../hooks/useTranscript'
import { useAnalysisStatus, useAnalysisSummary, useStartAnalysis } from '../hooks/useAnalysis'
import { useRisk } from '../hooks/useRisk'
import { useCallReport, useDownloadReport, useGenerateReport } from '../hooks/useReports'
import { getAudioStreamUrl } from '../api/calls'
import { formatDateTime, formatDuration } from '../lib/utils'

export function CallDetailPage() {
  const { callId } = useParams<{ callId: string }>()
  const [searchParams] = useSearchParams()
  const timestampParam = searchParams.get('timestamp') || searchParams.get('t')
  const initialTimestamp = timestampParam ? parseFloat(timestampParam) : null

  // Real backend queries
  const { data: call, isError: callError, error, refetch: refetchCall } = useCall(callId)
  const { data: transcript, isLoading: transcriptLoading } = useTranscript(callId)
  const { data: turnsData, isLoading: turnsLoading } = useTranscriptTurns(callId, 1, 100)
  const { data: risk, isLoading: riskLoading, refetch: refetchRisk } = useRisk(callId)
  const { data: summary, isLoading: summaryLoading } = useAnalysisSummary(callId)
  const { data: analysisStatus } = useAnalysisStatus(callId)
  const startAnalysisMutation = useStartAnalysis()

  const { data: callReport, refetch: refetchReport } = useCallReport(callId)
  const generateReportMutation = useGenerateReport()
  const downloadReportMutation = useDownloadReport()
  const [downloadingFormat, setDownloadingFormat] = useState<string | null>(null)
  const [reportError, setReportError] = useState<string | null>(null)

  const handleGenerateReport = async () => {
    if (!callId) return
    setReportError(null)
    try {
      await generateReportMutation.mutateAsync({
        report_type: 'INDIVIDUAL_CALL',
        call_id: callId,
      })
      refetchReport()
    } catch (err) {
      setReportError(err instanceof Error ? err.message : 'Report generation failed')
    }
  }

  const handleDownload = async (format: 'pdf' | 'json' | 'csv') => {
    if (!callReport?.id) return
    setDownloadingFormat(format)
    try {
      await downloadReportMutation.mutateAsync({
        reportId: callReport.id,
        format,
        fallbackFilename: `call-${call?.external_id || callId?.slice(0, 8)}-report.${format}`,
      })
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Download failed')
    } finally {
      setDownloadingFormat(null)
    }
  }

  const isReportReady = callReport?.status === 'COMPLETED'
  const isReportGenerating =
    generateReportMutation.isPending ||
    callReport?.status === 'GENERATING' ||
    callReport?.status === 'PENDING'
  const isReportFailed = callReport?.status === 'FAILED'

  if (callError) {
    return (
      <div className="space-y-4">
        <Link to="/calls" className="inline-flex items-center gap-1 text-xs text-[#60636B] hover:text-[#17181C]">
          <ArrowLeft className="h-4 w-4" /> Back to Calls
        </Link>
        <ErrorAlert
          title="Failed to load call details"
          message={(error as Error).message}
          onRetry={() => refetchCall()}
        />
      </div>
    )
  }

  const handleReprocess = async () => {
    if (!callId) return
    try {
      await startAnalysisMutation.mutateAsync({ callId, payload: { force_reprocess: true } })
      refetchCall()
      refetchRisk()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to trigger reprocess')
    }
  }

  const turns = turnsData?.items ?? []
  const audioUrl = callId ? getAudioStreamUrl(callId) : ''
  const hasAudio = Boolean(call?.audio_file)
  const isPipelineRunning =
    analysisStatus?.status === 'PROCESSING' || analysisStatus?.status === 'QUEUED' || call?.status === 'PROCESSING'

  return (
    <div className="space-y-6 animate-in fade-in duration-150">
      {/* Top Breadcrumb & Actions Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-[#E5E5E2]">
        <div className="flex items-center gap-3">
          <Link
            to="/calls"
            className="p-2 rounded-lg border border-[#E5E5E2] bg-white text-[#60636B] hover:text-[#17181C] hover:bg-[#FAFAF9] shadow-xs transition-colors"
            title="Back to calls"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-[#17181C] font-mono">
                {call?.external_id ? `Call #${call.external_id}` : `Call #${callId?.slice(0, 8)}`}
              </h2>
              {call && <StatusBadge status={call.status} />}
            </div>
            <div className="flex flex-wrap items-center gap-4 mt-1 text-xs text-[#60636B]">
              <span className="flex items-center gap-1">
                <Clock className="h-3.5 w-3.5" />
                {formatDuration(call?.duration ?? call?.audio_file?.duration)}
              </span>
              <span className="flex items-center gap-1">
                <Calendar className="h-3.5 w-3.5" />
                {formatDateTime(call?.created_at)}
              </span>
              <span className="flex items-center gap-1">
                <Globe className="h-3.5 w-3.5" />
                {(call?.language || 'en').toUpperCase()}
              </span>
              {call?.batch_id && (
                <Link
                  to={`/batches/${call.batch_id}`}
                  className="inline-flex items-center gap-1 text-[#6D5AE6] hover:underline font-medium"
                >
                  <FileArchive className="h-3.5 w-3.5" />
                  <span>Batch: {call.batch_name || call.batch_filename || 'ZIP Archive'}</span>
                </Link>
              )}
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {summary?.dominant_sentiment && (
            <SentimentBadge sentiment={summary.dominant_sentiment} />
          )}

          {/* Report Actions */}
          {isReportReady && (
            <div className="flex items-center gap-1.5 p-1 rounded-lg bg-emerald-50 border border-emerald-200">
              <span className="text-[11px] font-medium text-emerald-800 px-2 flex items-center gap-1 font-mono">
                <CheckCircle2 className="h-3 w-3 text-emerald-600" />
                Report Ready
              </span>

              <button
                type="button"
                onClick={() => handleDownload('pdf')}
                disabled={downloadingFormat === 'pdf'}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-[#6D5AE6] hover:bg-[#5844D6] text-white text-xs font-medium cursor-pointer transition-colors shadow-2xs"
                title="Download PDF Report"
              >
                {downloadingFormat === 'pdf' ? (
                  <Loader2 className="h-3 w-3 animate-spin" />
                ) : (
                  <Download className="h-3 w-3" />
                )}
                <span>Download PDF</span>
              </button>

              <button
                type="button"
                onClick={() => handleDownload('json')}
                disabled={downloadingFormat === 'json'}
                className="inline-flex items-center gap-1 px-2 py-1 rounded bg-white hover:bg-neutral-100 text-neutral-700 text-xs font-medium border border-neutral-200 cursor-pointer transition-colors"
                title="Download JSON Telemetry"
              >
                <FileCode className="h-3 w-3 text-neutral-500" />
                <span>JSON</span>
              </button>

              <button
                type="button"
                onClick={() => handleDownload('csv')}
                disabled={downloadingFormat === 'csv'}
                className="inline-flex items-center gap-1 px-2 py-1 rounded bg-white hover:bg-neutral-100 text-neutral-700 text-xs font-medium border border-neutral-200 cursor-pointer transition-colors"
                title="Download CSV Transcript"
              >
                <FileSpreadsheet className="h-3 w-3 text-neutral-500" />
                <span>CSV</span>
              </button>

              <button
                type="button"
                onClick={handleGenerateReport}
                disabled={isReportGenerating}
                className="p-1 text-neutral-400 hover:text-neutral-700 rounded transition-colors"
                title="Re-generate report"
              >
                <RefreshCw className="h-3 w-3" />
              </button>
            </div>
          )}

          {isReportGenerating && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-amber-50 border border-amber-200 text-amber-800 text-xs font-medium">
              <Loader2 className="h-3.5 w-3.5 animate-spin text-amber-600" />
              <span>Generating Report...</span>
            </div>
          )}

          {isReportFailed && (
            <div className="flex items-center gap-2 px-2 py-1 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs">
              <span className="flex items-center gap-1 text-[11px]">
                <AlertCircle className="h-3 w-3 text-rose-600" /> Report Failed
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={handleGenerateReport}
                leftIcon={<RefreshCw className="h-3 w-3" />}
              >
                Retry
              </Button>
            </div>
          )}

          {!isReportReady && !isReportGenerating && !isReportFailed && (
            <Button
              size="sm"
              onClick={handleGenerateReport}
              isLoading={generateReportMutation.isPending}
              leftIcon={<FileText className="h-3.5 w-3.5" />}
            >
              Generate Report
            </Button>
          )}

          <Button
            variant="outline"
            size="sm"
            onClick={handleReprocess}
            isLoading={startAnalysisMutation.isPending}
            leftIcon={<RefreshCw className="h-3.5 w-3.5" />}
          >
            Reprocess
          </Button>
        </div>
      </div>

      {reportError && (
        <ErrorAlert
          title="Report Generation Alert"
          message={reportError}
          onRetry={handleGenerateReport}
        />
      )}

      {/* Real-time Pipeline Progress Tracker (if active) */}
      {isPipelineRunning && (
        <div className="p-4 rounded-xl border border-amber-200 bg-amber-50 text-amber-900 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <Loader2 className="h-4 w-4 animate-spin text-amber-600" />
            <span>
              Background AI Pipeline is currently analyzing call audio...{' '}
              {analysisStatus?.current_stage && (
                <strong className="font-mono text-amber-800">[{analysisStatus.current_stage}]</strong>
              )}
            </span>
          </div>
          <span className="font-mono font-bold">{analysisStatus?.progress ?? 0}%</span>
        </div>
      )}

      {/* Audio Playback Scrubber (Synchronized with Transcript) */}
      {hasAudio && (
        <AudioPlayerDock
          callId={callId!}
          audioUrl={audioUrl}
          audioFilename={call?.audio_file?.filename}
          totalDuration={call?.duration ?? call?.audio_file?.duration}
        />
      )}

      {/* Main Analytical Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left 8 Cols: Transcript Workspace */}
        <div className="lg:col-span-8 rounded-xl border border-[#E5E5E2] bg-white p-4 sm:p-5 shadow-xs flex flex-col min-h-[580px]">
          <div className="flex items-center justify-between pb-3 mb-3 border-b border-[#E5E5E2]">
            <div className="flex items-center gap-2">
              <PlayCircle className="h-4 w-4 text-[#6D5AE6]" />
              <h3 className="text-sm font-semibold text-[#17181C]">
                Speaker Transcript & NLP Turn Annotations
              </h3>
            </div>
            {transcript && (
              <span className="text-xs text-[#60636B] font-mono">
                Model: {transcript.model} v{transcript.model_version} • {transcript.turn_count} turns
              </span>
            )}
          </div>

          <div className="flex-1">
            <TranscriptViewer
              turns={turns}
              isLoading={transcriptLoading || turnsLoading}
              highlightTimestamp={initialTimestamp}
            />
          </div>
        </div>

        {/* Right 4 Cols: AI Intelligence Rail (Risk, Intents, Themes, Metrics) */}
        <div className="lg:col-span-4 space-y-5">
          {/* Explainable Escalation Risk Card */}
          <RiskScoreCard risk={risk} isLoading={riskLoading} />

          {/* Conversational Rollup Metrics Card */}
          <div className="p-5 rounded-xl border border-[#E5E5E2] bg-white shadow-xs space-y-4">
            <h4 className="text-xs font-semibold text-[#17181C]">
              Conversational Summary
            </h4>

            {summaryLoading ? (
              <div className="animate-pulse space-y-2">
                <div className="h-4 bg-[#F2F2F0] rounded w-1/2" />
                <div className="h-4 bg-[#F2F2F0] rounded w-3/4" />
              </div>
            ) : (
              <div className="space-y-3 text-xs">
                <div className="flex justify-between items-center py-1.5 border-b border-[#E5E5E2]">
                  <span className="text-[#60636B]">Speaker Count</span>
                  <span className="font-mono text-[#17181C] font-semibold">
                    {summary?.speaker_count ?? '--'} speakers
                  </span>
                </div>

                <div className="flex justify-between items-center py-1.5 border-b border-[#E5E5E2]">
                  <span className="text-[#60636B]">Dominant Sentiment</span>
                  {summary?.dominant_sentiment ? (
                    <SentimentBadge sentiment={summary.dominant_sentiment} />
                  ) : (
                    <span className="text-[#60636B] font-mono">--</span>
                  )}
                </div>

                <div className="flex justify-between items-center py-1.5 border-b border-[#E5E5E2]">
                  <span className="text-[#60636B]">Primary Intent</span>
                  {summary?.primary_intent ? (
                    <Badge variant="info">{summary.primary_intent}</Badge>
                  ) : (
                    <span className="text-[#60636B] font-mono">--</span>
                  )}
                </div>

                {transcript?.text && (
                  <div className="pt-2">
                    <span className="text-[#60636B] text-[11px] font-medium block mb-1">
                      Full Text Snippet:
                    </span>
                    <p className="text-[#17181C] italic text-[11px] leading-relaxed line-clamp-4 bg-[#FAFAF9] p-2.5 rounded border border-[#E5E5E2]">
                      "{transcript.text}"
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
