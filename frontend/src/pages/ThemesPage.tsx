import { ArrowRight, Layers, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'
import { MetricCard } from '../components/ui/MetricCard'
import { EmptyState } from '../components/ui/EmptyState'
import { ErrorAlert } from '../components/ui/ErrorAlert'
import { useThemes } from '../hooks/useThemes'
import { formatPercentage } from '../lib/utils'

export function ThemesPage() {
  const { data, isLoading, isError, error, refetch } = useThemes()

  if (isError) {
    return (
      <div className="space-y-4">
        <h2 className="text-xl font-bold tracking-tight text-[#17181C]">Discovered Themes</h2>
        <ErrorAlert
          title="Failed to load theme discovery clusters"
          message={(error as Error).message}
          onRetry={() => refetch()}
        />
      </div>
    )
  }

  const themes = data?.themes ?? []
  const totalThemes = data?.total_themes ?? themes.length
  const noisePercentage = data?.noise_percentage
  const silhouetteScore = data?.silhouette_score

  return (
    <div className="space-y-6 animate-in fade-in duration-150">
      {/* Header */}
      <div className="pb-4 border-b border-[#E5E5E2]">
        <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-[#17181C] flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-[#6D5AE6]" />
          Customer Conversation Themes
        </h2>
        <p className="mt-1 text-xs sm:text-sm text-[#60636B]">
          Unsupervised topic discovery across call embeddings using UMAP dimensionality reduction + HDBSCAN clustering
        </p>
      </div>

      {/* Cluster Diagnostics KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <MetricCard
          title="Discovered Themes"
          value={totalThemes}
          subtext="Discrete topic clusters discovered in Phase 7"
          icon={<Layers className="h-4 w-4 text-[#6D5AE6]" />}
          loading={isLoading}
        />
        <MetricCard
          title="Noise / Outliers Ratio"
          value={noisePercentage !== null && noisePercentage !== undefined ? formatPercentage(noisePercentage) : '--%'}
          subtext={`${data?.noise_count ?? 0} unclustered conversational chunks`}
          icon={<Sparkles className="h-4 w-4 text-amber-600" />}
          loading={isLoading}
        />
        <MetricCard
          title="Clustering Silhouette"
          value={silhouetteScore !== null && silhouetteScore !== undefined ? silhouetteScore.toFixed(3) : '--'}
          subtext="Cluster cohesion quality metric (-1.0 to +1.0)"
          icon={<Layers className="h-4 w-4 text-[#60636B]" />}
          loading={isLoading}
        />
      </div>

      {/* Theme Cards Grid */}
      {themes.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {themes.map((theme) => (
            <div
              key={theme.id}
              className="p-5 rounded-xl border border-[#E5E5E2] bg-white hover:border-[#D1D1CD] transition-all flex flex-col justify-between space-y-4 shadow-xs"
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-[#F2F0FD] text-[#5844D6] border border-[#DDD6FE]">
                    Cluster #{theme.cluster_id}
                  </span>
                  <span className="text-xs font-mono text-[#60636B] tabular-nums">
                    {theme.size} dialogue chunks
                  </span>
                </div>

                <h3 className="text-base font-bold text-[#17181C]">{theme.title}</h3>
                <p className="text-xs text-[#60636B] leading-relaxed line-clamp-3">
                  {theme.summary}
                </p>
              </div>

              <div className="space-y-3 pt-3 border-t border-[#E5E5E2]">
                {/* Keywords */}
                <div className="flex flex-wrap gap-1.5">
                  {theme.top_keywords.map((kw, i) => (
                    <span
                      key={i}
                      className="px-2 py-0.5 rounded text-[11px] font-mono bg-[#FAFAF9] text-[#17181C] border border-[#E5E5E2]"
                    >
                      {kw}
                    </span>
                  ))}
                </div>

                <div className="flex justify-end pt-1">
                  <Link
                    to={`/themes/${theme.id}`}
                    className="inline-flex items-center gap-1 text-xs text-[#6D5AE6] hover:text-[#5844D6] font-semibold transition-colors"
                  >
                    View cluster details <ArrowRight className="h-3.5 w-3.5" />
                  </Link>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState
          icon={<Sparkles className="h-10 w-10 text-[#60636B]" />}
          title="No theme discovery runs found"
          description="Execute Phase 7 UMAP/HDBSCAN clustering script in the AI service to persist customer topic clusters."
        />
      )}
    </div>
  )
}
