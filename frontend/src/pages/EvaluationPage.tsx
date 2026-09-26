import { Activity } from 'lucide-react'
import { Badge } from '../components/ui/Badge'
import { EmptyState } from '../components/ui/EmptyState'
import { ErrorAlert } from '../components/ui/ErrorAlert'
import { TableSkeleton } from '../components/ui/LoadingSkeleton'
import { useEvaluation } from '../hooks/useEvaluation'
import { formatDateTime, formatPercentage } from '../lib/utils'

export function EvaluationPage() {
  const { data, isLoading, isError, error, refetch } = useEvaluation()

  if (isError) {
    return (
      <div className="space-y-4">
        <h2 className="text-xl font-bold tracking-tight text-[#17181C]">AI Model Evaluation</h2>
        <ErrorAlert
          title="Failed to load evaluation benchmark results"
          message={(error as Error).message}
          onRetry={() => refetch()}
        />
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h2 className="text-xl font-bold tracking-tight text-[#17181C]">AI Model Evaluation</h2>
        <TableSkeleton rows={6} cols={4} />
      </div>
    )
  }

  if (!data || !data.components || Object.keys(data.components).length === 0) {
    return (
      <EmptyState
        icon={<Activity className="h-10 w-10 text-[#60636B]" />}
        title="No evaluation run available"
        description="No model benchmark runs have been generated yet. When evaluation runs are executed, quality metrics will be displayed here."
      />
    )
  }

  const comps = data.components
  const asr = comps.asr
  const diarization = comps.diarization
  const intent = comps.intent
  const dataset = comps.dataset

  const intentPerClass = (intent?.details?.per_class as Record<string, { precision: number; recall: number; f1: number; support: number }>) || {}
  const totalIntentSupport = Object.values(intentPerClass).reduce((acc, c) => acc + (c.support || 0), 0)
  const intentClassCount = Object.keys(intentPerClass).length

  return (
    <div className="space-y-6 animate-in fade-in duration-150">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-[#E5E5E2]">
        <div>
          <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-[#17181C] flex items-center gap-2">
            <Activity className="h-5 w-5 text-[#6D5AE6]" />
            AI Model Evaluation & Quality Benchmarks
          </h2>
          <p className="mt-1 text-xs sm:text-sm text-[#60636B]">
            Validated accuracy, error rates, and confusion diagnostics across all speech and NLP pipeline stages
          </p>
        </div>

        <div className="text-right text-xs font-mono text-[#60636B]">
          <div>Run ID: {data.evaluation_id ? data.evaluation_id.slice(0, 8) + '...' : '--'}</div>
          <div>Audited: {data.timestamp ? formatDateTime(data.timestamp) : '--'}</div>
        </div>
      </div>

      {/* Component Quality Scorecards Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* ASR Scorecard */}
        {asr && (
          <div className="p-4 rounded-xl border border-[#E5E5E2] bg-white space-y-2 shadow-xs">
            <div className="flex items-center justify-between text-xs">
              <span className="text-[#60636B] font-semibold">ASR (Whisper)</span>
              <Badge variant={asr.status === 'PASSED' ? 'success' : 'warning'}>{asr.status}</Badge>
            </div>
            <div className="text-2xl font-bold font-mono text-[#17181C] tabular-nums">
              WER: {formatPercentage(asr.metrics.wer as number)}
            </div>
            <div className="text-[11px] text-[#60636B] font-mono tabular-nums">
              CER: {formatPercentage(asr.metrics.cer as number)} • {asr.model_name}
            </div>
          </div>
        )}

        {/* Diarization Scorecard */}
        {diarization && (
          <div className="p-4 rounded-xl border border-[#E5E5E2] bg-white space-y-2 shadow-xs">
            <div className="flex items-center justify-between text-xs">
              <span className="text-[#60636B] font-semibold">Diarization</span>
              <Badge variant={diarization.status === 'PASSED' ? 'success' : 'warning'}>{diarization.status}</Badge>
            </div>
            <div className="text-2xl font-bold font-mono text-[#17181C] tabular-nums">
              Coverage: {formatPercentage(diarization.metrics.average_alignment_coverage as number)}
            </div>
            <div className="text-[11px] text-[#60636B] font-mono">
              {diarization.model_name}
            </div>
          </div>
        )}

        {/* Intent Scorecard */}
        {intent && (
          <div className="p-4 rounded-xl border border-[#E5E5E2] bg-white space-y-2 shadow-xs">
            <div className="flex items-center justify-between text-xs">
              <span className="text-[#60636B] font-semibold">Intent Classifier</span>
              <Badge variant={intent.status === 'PASSED' ? 'success' : 'warning'}>{intent.status}</Badge>
            </div>
            <div className="text-2xl font-bold font-mono text-[#17181C] tabular-nums">
              F1: {formatPercentage(intent.metrics.macro_f1 as number)}
            </div>
            <div className="text-[11px] text-[#60636B] font-mono tabular-nums">
              Acc: {formatPercentage(intent.metrics.accuracy as number)} • Top-3: {formatPercentage(intent.metrics.top3_accuracy as number)}
            </div>
          </div>
        )}

        {/* Dataset Audit Scorecard */}
        {dataset && (
          <div className="p-4 rounded-xl border border-[#E5E5E2] bg-white space-y-2 shadow-xs">
            <div className="flex items-center justify-between text-xs">
              <span className="text-[#60636B] font-semibold">Dataset Audit</span>
              <Badge variant={dataset.status === 'PASSED' ? 'success' : 'warning'}>{dataset.status}</Badge>
            </div>
            <div className="text-2xl font-bold font-mono text-[#17181C] tabular-nums">
              {dataset.sample_count} Samples
            </div>
            <div className="text-[11px] text-[#60636B] font-mono">
              {dataset.dataset_name}
            </div>
          </div>
        )}
      </div>

      {/* Per-Class Intent Breakdown Table */}
      {Object.keys(intentPerClass).length > 0 && (
        <div className="p-5 rounded-xl border border-[#E5E5E2] bg-white space-y-4 shadow-xs">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-[#17181C]">
              {dataset?.dataset_name ? `${dataset.dataset_name} ` : ''}Intent Classification Performance ({totalIntentSupport > 0 ? totalIntentSupport : dataset?.sample_count ?? 0} Test Samples)
            </h3>
            <span className="text-xs text-[#6D5AE6] font-mono tabular-nums font-semibold">{intentClassCount} Distinct Classes</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="border-b border-[#E5E5E2] bg-[#FAFAF9] text-[#60636B] text-[11px]">
                <tr>
                  <th className="py-2.5 px-3 font-semibold font-sans">Class Name</th>
                  <th className="py-2.5 px-3 font-semibold">Precision</th>
                  <th className="py-2.5 px-3 font-semibold">Recall</th>
                  <th className="py-2.5 px-3 font-semibold">F1 Score</th>
                  <th className="py-2.5 px-3 text-right font-semibold">Support</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#EFEFEC]">
                {Object.entries(intentPerClass).map(([className, metrics]) => (
                  <tr key={className} className="hover:bg-[#FAFAF9] transition-colors">
                    <td className="py-2.5 px-3 font-semibold text-[#17181C] font-sans">{className}</td>
                    <td className="py-2.5 px-3 text-emerald-700 tabular-nums">{formatPercentage(metrics.precision)}</td>
                    <td className="py-2.5 px-3 text-sky-700 tabular-nums">{formatPercentage(metrics.recall)}</td>
                    <td className="py-2.5 px-3 text-[#5844D6] font-bold tabular-nums">{formatPercentage(metrics.f1)}</td>
                    <td className="py-2.5 px-3 text-right text-[#60636B] tabular-nums">{metrics.support}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
