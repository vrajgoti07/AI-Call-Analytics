import {
  AlertTriangle,
  ArrowRight,
  Info,
  PhoneCall,
  ShieldAlert,
  ShieldCheck,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { MetricCard } from '../components/ui/MetricCard'
import { EmptyState } from '../components/ui/EmptyState'
import { ErrorAlert } from '../components/ui/ErrorAlert'
import { TableSkeleton } from '../components/ui/LoadingSkeleton'
import { useCalls } from '../hooks/useCalls'
import { formatDateTime, formatDuration } from '../lib/utils'

export function RiskPage() {
  const { data, isLoading, isError, error, refetch } = useCalls({
    page: 1,
    page_size: 50,
  })

  if (isError) {
    return (
      <div className="space-y-4">
        <h2 className="text-xl font-bold tracking-tight text-[#17181C]">Escalation Risk Console</h2>
        <ErrorAlert
          title="Failed to load risk evaluations"
          message={(error as Error).message}
          onRetry={() => refetch()}
        />
      </div>
    )
  }

  const calls = data?.items ?? []
  const completedCalls = calls.filter((c) => c.status === 'COMPLETED')

  return (
    <div className="space-y-6 animate-in fade-in duration-150">
      {/* Header */}
      <div className="pb-4 border-b border-[#E5E5E2]">
        <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-[#17181C] flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-amber-600" />
          Escalation Risk Intelligence
        </h2>
        <p className="mt-1 text-xs sm:text-sm text-[#60636B]">
          Predictive early detection of caller dissatisfaction and supervisor escalation triggers (Phase 8 Multi-Modal Engine)
        </p>
      </div>

      {/* Model Transparency Banner */}
      <div className="p-4 rounded-xl border border-sky-200 bg-sky-50 text-sky-900 text-xs flex items-start gap-3">
        <Info className="h-4 w-4 text-sky-600 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <span className="font-semibold text-sky-950">Model Engine Provenance:</span>
          <p className="text-sky-900 leading-relaxed">
            Escalation detection is evaluated through our Phase 8 multi-modal model (combining acoustic turn duration, temporal sentiment deterioration, and repeated issue intent signals).
          </p>
        </div>
      </div>

      {/* Risk Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <MetricCard
          title="Monitored Conversations"
          value={calls.length}
          subtext="Active call recordings analyzed for escalation signals"
          icon={<PhoneCall className="h-4 w-4 text-[#6D5AE6]" />}
          loading={isLoading}
        />
        <MetricCard
          title="Completed Evaluations"
          value={completedCalls.length}
          subtext="Conversations with fully generated risk assessments"
          icon={<ShieldCheck className="h-4 w-4 text-emerald-600" />}
          loading={isLoading}
        />
        <MetricCard
          title="Escalation Thresholds"
          value="High >= 70"
          subtext="Medium: 40-69 • Low: 0-39 score points"
          icon={<ShieldAlert className="h-4 w-4 text-rose-600" />}
          loading={isLoading}
        />
      </div>

      {/* Calls Escalation Queue Table */}
      <div className="rounded-xl border border-[#E5E5E2] bg-white p-5 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-[#17181C]">
            Calls Queue & Escalation Investigation
          </h3>
          <span className="text-xs text-[#60636B] font-mono tabular-nums">{calls.length} records</span>
        </div>

        {isLoading ? (
          <TableSkeleton rows={6} cols={5} />
        ) : calls.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-[#E5E5E2] bg-[#FAFAF9] text-[#60636B] text-[11px] font-semibold">
                <tr>
                  <th className="py-2.5 px-3">Call Reference</th>
                  <th className="py-2.5 px-3">Audio Filename</th>
                  <th className="py-2.5 px-3">Duration</th>
                  <th className="py-2.5 px-3">Created</th>
                  <th className="py-2.5 px-3 text-right">Risk Drilldown</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#EFEFEC]">
                {calls.map((call) => (
                  <tr key={call.id} className="hover:bg-[#FAFAF9] transition-colors">
                    <td className="py-3 px-3 font-semibold text-[#6D5AE6] font-mono">
                      <Link to={`/calls/${call.id}`} className="hover:underline">
                        {call.external_id || call.id.slice(0, 8)}
                      </Link>
                    </td>
                    <td className="py-3 px-3 text-[#17181C]">
                      {call.audio_file?.filename || '--'}
                    </td>
                    <td className="py-3 px-3 text-[#17181C] font-mono tabular-nums">
                      {formatDuration(call.duration ?? call.audio_file?.duration)}
                    </td>
                    <td className="py-3 px-3 text-[#60636B]">
                      {formatDateTime(call.created_at)}
                    </td>
                    <td className="py-3 px-3 text-right">
                      <Link
                        to={`/calls/${call.id}`}
                        className="inline-flex items-center gap-1 text-xs text-[#6D5AE6] hover:text-[#5844D6] font-semibold transition-colors"
                      >
                        Inspect Risk Factors <ArrowRight className="h-3.5 w-3.5" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            icon={<ShieldCheck className="h-10 w-10 text-[#60636B]" />}
            title="No calls available for escalation analysis"
            description="Ingest call audio in the Calls tab to initiate automatic escalation risk estimation."
          />
        )}
      </div>
    </div>
  )
}
