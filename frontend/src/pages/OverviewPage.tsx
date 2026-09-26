import {
  ArrowRight,
  CheckCircle2,
  Clock,
  FileArchive,
  PhoneCall,
  Sparkles,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { MetricCard } from '../components/ui/MetricCard'
import { StatusBadge } from '../components/ui/StatusBadge'
import { Button } from '../components/ui/Button'
import { ErrorAlert } from '../components/ui/ErrorAlert'
import { EmptyState } from '../components/ui/EmptyState'
import { ChartTooltip } from '../components/ui/ChartTooltip'
import { useCalls } from '../hooks/useCalls'
import { useThemes } from '../hooks/useThemes'
import { formatDateTime, formatDuration } from '../lib/utils'
import { CHART_PALETTE, RECHARTS_TOOLTIP_STYLE } from '../lib/constants'

export function OverviewPage() {
  const { data: callsData, isLoading: callsLoading, isError: callsError, error, refetch } = useCalls({
    page: 1,
    page_size: 100,
  })

  const { data: themesData, isLoading: themesLoading } = useThemes()

  if (callsError) {
    return (
      <div className="space-y-6">
        <h2 className="text-xl font-bold tracking-tight text-[#17181C]">Executive Operations Overview</h2>
        <ErrorAlert
          title="Failed to load overview data from backend"
          message={(error as Error).message}
          onRetry={() => refetch()}
        />
      </div>
    )
  }

  const calls = callsData?.items ?? []
  const totalCalls = callsData?.pagination?.total ?? calls.length
  const completedCalls = calls.filter((c) => c.status === 'COMPLETED').length
  const processingCalls = calls.filter((c) => c.status === 'PROCESSING').length
  const queuedCalls = calls.filter((c) => c.status === 'QUEUED').length
  const failedCalls = calls.filter((c) => c.status === 'FAILED').length
  const uploadedCalls = calls.filter((c) => c.status === 'UPLOADED').length

  // Calculate average duration across calls with duration
  const durations = calls.map((c) => c.duration).filter((d): d is number => d !== null && d !== undefined)
  const avgDuration =
    durations.length > 0 ? durations.reduce((a, b) => a + b, 0) / durations.length : 0

  // Status breakdown using deliberate semantic status palette
  const statusDistribution = [
    { name: 'Completed', value: completedCalls, color: CHART_PALETTE.status.completed },
    { name: 'Processing', value: processingCalls, color: CHART_PALETTE.status.processing },
    { name: 'Queued', value: queuedCalls, color: CHART_PALETTE.status.queued },
    { name: 'Failed', value: failedCalls, color: CHART_PALETTE.status.failed },
    { name: 'Uploaded', value: uploadedCalls, color: CHART_PALETTE.status.uploaded },
  ].filter((d) => d.value > 0)

  // Recent 5 calls for quick queue
  const recentCalls = calls.slice(0, 5)

  // Top themes
  const topThemes = (themesData?.themes ?? []).slice(0, 4)

  return (
    <div className="space-y-6 animate-in fade-in duration-150">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-[#E5E5E2]">
        <div>
          <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-[#17181C]">
            Executive Operations Overview
          </h2>
          <p className="mt-1 text-xs sm:text-sm text-[#60636B]">
            Real-time pipeline ingestion health, conversational metrics, and audio insights
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link to="/batches">
            <Button variant="outline" size="sm" leftIcon={<FileArchive className="h-3.5 w-3.5" />}>
              ZIP Batches
            </Button>
          </Link>
          <Link to="/calls">
            <Button size="sm" leftIcon={<PhoneCall className="h-3.5 w-3.5" />}>
              Ingest Audio Call
            </Button>
          </Link>
        </div>
      </div>

      {/* Top 4 KPI Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5">
        <MetricCard
          title="Total Ingested Calls"
          value={totalCalls}
          subtext="Processed via MInDS-14 or uploaded"
          icon={<PhoneCall className="h-4 w-4 text-[#6D5AE6]" />}
          loading={callsLoading}
        />
        <MetricCard
          title="Completed Analyses"
          value={completedCalls}
          subtext={totalCalls > 0 ? `${Math.round((completedCalls / totalCalls) * 100)}% completion rate` : '0%'}
          icon={<CheckCircle2 className="h-4 w-4 text-emerald-600" />}
          loading={callsLoading}
        />
        <MetricCard
          title="Active Processing"
          value={processingCalls}
          subtext="In Celery pipeline stages"
          icon={<Clock className="h-4 w-4 text-amber-600" />}
          loading={callsLoading}
        />
        <MetricCard
          title="Average Call Duration"
          value={formatDuration(avgDuration)}
          subtext="Computed from acoustic audio headers"
          icon={<Clock className="h-4 w-4 text-[#60636B]" />}
          loading={callsLoading}
        />
      </div>

      {/* Middle Analytical Row (Chart + Discovered Themes) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Pipeline Execution Breakdown Chart */}
        <div className="lg:col-span-6 rounded-xl border border-[#E5E5E2] bg-white p-5 shadow-xs flex flex-col justify-between">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-[#17181C]">
              Pipeline Execution Status Breakdown
            </h3>
            <span className="text-xs text-[#60636B] font-mono tabular-nums">{totalCalls} total</span>
          </div>

          {statusDistribution.length > 1 ? (
            <div className="h-56 flex items-center justify-center">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={statusDistribution}
                    innerRadius={55}
                    outerRadius={80}
                    paddingAngle={4}
                    dataKey="value"
                  >
                    {statusDistribution.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip content={<ChartTooltip />} contentStyle={RECHARTS_TOOLTIP_STYLE} />
                </PieChart>
              </ResponsiveContainer>
              <div className="flex flex-col gap-2 pl-4 border-l border-[#E5E5E2]">
                {statusDistribution.map((item) => (
                  <div key={item.name} className="flex items-center gap-2 text-xs">
                    <span
                      className="h-2.5 w-2.5 rounded-full"
                      style={{ backgroundColor: item.color }}
                    />
                    <span className="text-[#60636B]">{item.name}:</span>
                    <span className="font-mono font-semibold text-[#17181C] tabular-nums">{item.value}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : statusDistribution.length === 1 ? (
            <div className="h-56 flex flex-col justify-center gap-4 px-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span
                    className="h-3 w-3 rounded-full"
                    style={{ backgroundColor: statusDistribution[0].color }}
                  />
                  <span className="text-sm font-semibold text-[#17181C]">
                    {statusDistribution[0].name} ({statusDistribution[0].value} of {totalCalls})
                  </span>
                </div>
                <span className="text-xs font-mono font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                  100% Pipeline Health
                </span>
              </div>
              <div className="w-full h-3 bg-[#F2F2F0] rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: '100%',
                    backgroundColor: statusDistribution[0].color,
                  }}
                />
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 text-xs">
                <div className="p-2 rounded border border-[#E5E5E2] bg-[#FAFAF9]">
                  <span className="text-[#60636B] block text-[11px]">Completed</span>
                  <span className="font-mono font-bold text-[#17181C] tabular-nums">{completedCalls}</span>
                </div>
                <div className="p-2 rounded border border-[#E5E5E2] bg-[#FAFAF9]">
                  <span className="text-[#60636B] block text-[11px]">Processing</span>
                  <span className="font-mono font-bold text-[#17181C] tabular-nums">{processingCalls}</span>
                </div>
                <div className="p-2 rounded border border-[#E5E5E2] bg-[#FAFAF9]">
                  <span className="text-[#60636B] block text-[11px]">Failed</span>
                  <span className="font-mono font-bold text-[#17181C] tabular-nums">{failedCalls}</span>
                </div>
                <div className="p-2 rounded border border-[#E5E5E2] bg-[#FAFAF9]">
                  <span className="text-[#60636B] block text-[11px]">Queued</span>
                  <span className="font-mono font-bold text-[#17181C] tabular-nums">{queuedCalls}</span>
                </div>
              </div>
            </div>
          ) : (
            <div className="h-56 flex items-center justify-center text-xs text-[#60636B]">
              No processing metrics available yet.
            </div>
          )}
        </div>

        {/* Discovered Themes Rollup */}
        <div className="lg:col-span-6 rounded-xl border border-[#E5E5E2] bg-white p-5 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-[#6D5AE6]" />
              <h3 className="text-sm font-semibold text-[#17181C]">
                Top Discovered Themes
              </h3>
            </div>
            <Link
              to="/themes"
              className="text-xs text-[#6D5AE6] hover:text-[#5844D6] flex items-center gap-1 font-medium transition-colors"
            >
              View all <ArrowRight className="h-3 w-3" />
            </Link>
          </div>

          {themesLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="animate-pulse h-12 bg-[#F2F2F0] rounded-lg" />
              ))}
            </div>
          ) : topThemes.length > 0 ? (
            <div className="space-y-2.5">
              {topThemes.map((theme) => (
                <div
                  key={theme.id}
                  className="p-3 rounded-lg border border-[#E5E5E2] bg-[#FAFAF9] hover:bg-[#F5F5F3] transition-colors flex items-center justify-between"
                >
                  <div className="space-y-1">
                    <h4 className="text-xs font-semibold text-[#17181C]">{theme.title}</h4>
                    <div className="flex flex-wrap gap-1">
                      {theme.top_keywords.slice(0, 3).map((kw, idx) => (
                        <span
                          key={idx}
                          className="px-1.5 py-0.5 rounded bg-white text-[10px] font-mono text-[#60636B] border border-[#E5E5E2]"
                        >
                          {kw}
                        </span>
                      ))}
                    </div>
                  </div>
                  <span className="text-xs font-mono font-semibold px-2 py-0.5 rounded bg-[#F2F0FD] text-[#5844D6] border border-[#DDD6FE] tabular-nums">
                    {theme.size} chunks
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              title="No theme clusters discovered"
              description="Execute Phase 7 UMAP/HDBSCAN clustering to reveal caller topic patterns."
              className="py-6"
            />
          )}
        </div>
      </div>

      {/* Recent Ingested Calls Table */}
      <div className="rounded-xl border border-[#E5E5E2] bg-white p-5 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-[#17181C]">
            Recent Ingested Calls Queue
          </h3>
          <Link
            to="/calls"
            className="text-xs text-[#6D5AE6] hover:text-[#5844D6] flex items-center gap-1 font-medium transition-colors"
          >
            All calls <ArrowRight className="h-3 w-3" />
          </Link>
        </div>

        {recentCalls.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-[#E5E5E2] bg-[#FAFAF9] text-[#60636B] text-[11px] font-medium">
                <tr>
                  <th className="py-2.5 px-3 font-semibold">Call ID</th>
                  <th className="py-2.5 px-3 font-semibold">Audio Filename</th>
                  <th className="py-2.5 px-3 font-semibold">Duration</th>
                  <th className="py-2.5 px-3 font-semibold">Created At</th>
                  <th className="py-2.5 px-3 font-semibold">Status</th>
                  <th className="py-2.5 px-3 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#EFEFEC]">
                {recentCalls.map((call) => (
                  <tr key={call.id} className="hover:bg-[#FAFAF9] transition-colors">
                    <td className="py-3 px-3 text-[#17181C] font-mono font-semibold">
                      {call.external_id || call.id.slice(0, 8)}
                    </td>
                    <td className="py-3 px-3 text-[#60636B]">
                      {call.audio_file?.filename ?? '--'}
                    </td>
                    <td className="py-3 px-3 text-[#17181C] font-mono tabular-nums">
                      {formatDuration(call.duration ?? call.audio_file?.duration)}
                    </td>
                    <td className="py-3 px-3 text-[#60636B]">
                      {formatDateTime(call.created_at)}
                    </td>
                    <td className="py-3 px-3">
                      <StatusBadge status={call.status} />
                    </td>
                    <td className="py-3 px-3 text-right">
                      <Link
                        to={`/calls/${call.id}`}
                        className="inline-flex items-center gap-1 text-xs text-[#6D5AE6] hover:text-[#5844D6] font-medium transition-colors"
                      >
                        Inspect <ArrowRight className="h-3 w-3" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title="No calls ingested yet"
            description="Upload an audio recording (.wav, .mp3, .flac) to begin conversational analytics."
            action={
              <Link to="/calls">
                <Button size="sm">Go to Calls & Upload</Button>
              </Link>
            }
          />
        )}
      </div>
    </div>
  )
}
