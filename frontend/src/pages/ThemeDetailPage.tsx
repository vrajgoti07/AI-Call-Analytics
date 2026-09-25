import { ArrowLeft, Layers, MessageSquare, Sparkles } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { MetricCard } from '../components/ui/MetricCard'
import { ErrorAlert } from '../components/ui/ErrorAlert'
import { useTheme } from '../hooks/useThemes'

export function ThemeDetailPage() {
  const { themeId } = useParams<{ themeId: string }>()
  const { data: theme, isLoading, isError, error, refetch } = useTheme(themeId)

  if (isError) {
    return (
      <div className="space-y-4">
        <Link to="/themes" className="inline-flex items-center gap-1 text-xs text-[#60636B] hover:text-[#17181C]">
          <ArrowLeft className="h-4 w-4" /> Back to Themes
        </Link>
        <ErrorAlert
          title="Theme cluster not found"
          message={(error as Error).message}
          onRetry={() => refetch()}
        />
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-150">
      {/* Header */}
      <div className="flex items-center gap-3 pb-4 border-b border-[#E5E5E2]">
        <Link
          to="/themes"
          className="p-2 rounded-lg border border-[#E5E5E2] bg-white text-[#60636B] hover:text-[#17181C] hover:bg-[#FAFAF9] shadow-xs transition-colors"
          title="Back to themes"
        >
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-[#F2F0FD] text-[#5844D6] border border-[#DDD6FE]">
              Cluster #{theme?.cluster_id ?? '--'}
            </span>
            <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-[#17181C]">
              {theme?.title ?? 'Theme Details'}
            </h2>
          </div>
          <p className="mt-1 text-xs sm:text-sm text-[#60636B] max-w-2xl">
            {theme?.summary}
          </p>
        </div>
      </div>

      {/* Cluster Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <MetricCard
          title="Cluster Size (Dialogue Turns)"
          value={theme?.size ?? 0}
          subtext="Total conversational excerpts classified into this cluster"
          icon={<Layers className="h-4 w-4 text-[#6D5AE6]" />}
          loading={isLoading}
        />
        <MetricCard
          title="Representative Turns Count"
          value={theme?.exemplar_turn_ids.length ?? 0}
          subtext="Exemplar centroid turns defining cluster boundary"
          icon={<MessageSquare className="h-4 w-4 text-[#60636B]" />}
          loading={isLoading}
        />
      </div>

      {/* Keywords Table / Tags */}
      <div className="p-5 rounded-xl border border-[#E5E5E2] bg-white shadow-xs space-y-3">
        <div className="flex items-center gap-2 text-[#17181C] font-semibold text-xs">
          <Sparkles className="h-4 w-4 text-[#6D5AE6]" />
          <span>c-TF-IDF Descriptive Keywords</span>
        </div>
        <p className="text-xs text-[#60636B]">
          The following terms distinguish this cluster most strongly from other customer support topics:
        </p>

        <div className="flex flex-wrap gap-2 pt-2">
          {theme?.top_keywords.map((kw, i) => (
            <span
              key={i}
              className="px-3 py-1.5 rounded-lg text-xs font-mono bg-[#FAFAF9] text-[#17181C] border border-[#E5E5E2] font-medium"
            >
              #{kw}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}
