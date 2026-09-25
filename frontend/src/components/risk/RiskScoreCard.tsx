import { AlertTriangle, Info, ShieldCheck } from 'lucide-react'
import { RiskBadge } from '../ui/RiskBadge'
import type { EscalationRiskResponse } from '../../api/types'

export interface RiskScoreCardProps {
  risk: EscalationRiskResponse | null | undefined
  isLoading?: boolean
}

export function RiskScoreCard({ risk, isLoading = false }: RiskScoreCardProps) {
  if (isLoading) {
    return (
      <div className="animate-pulse p-5 rounded-xl border border-[#E5E5E2] bg-white space-y-3 shadow-xs">
        <div className="h-4 bg-[#F2F2F0] rounded w-1/3" />
        <div className="h-10 bg-[#F2F2F0] rounded w-1/2" />
        <div className="h-16 bg-[#F2F2F0] rounded w-full" />
      </div>
    )
  }

  if (!risk) {
    return (
      <div className="p-5 rounded-xl border border-[#E5E5E2] bg-white text-center space-y-2 shadow-xs">
        <ShieldCheck className="h-8 w-8 text-[#8A8D95] mx-auto" />
        <h4 className="text-sm font-semibold text-[#17181C]">Risk Assessment Pending</h4>
        <p className="text-xs text-[#60636B]">
          Escalation risk analysis has not completed for this call yet.
        </p>
      </div>
    )
  }

  const isHighRisk = (risk.risk_level || '').toLowerCase() === 'high' || risk.risk_score >= 70

  return (
    <div
      className={`p-5 rounded-xl border transition-all shadow-xs ${
        isHighRisk
          ? 'border-rose-200 bg-rose-50/40'
          : 'border-[#E5E5E2] bg-white'
      }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-[#E5E5E2]">
        <div className="flex items-center gap-2">
          <AlertTriangle
            className={`h-4 w-4 ${isHighRisk ? 'text-rose-600' : 'text-[#8A8D95]'}`}
          />
          <h4 className="text-xs font-semibold text-[#17181C]">
            Escalation Risk Assessment
          </h4>
        </div>
        <RiskBadge level={risk.risk_level} score={risk.risk_score} />
      </div>

      {/* Main Score Metrics */}
      <div className="py-4 flex items-baseline justify-between">
        <div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-bold font-mono text-[#17181C] tabular-nums">
              {Math.round(risk.risk_score)}
            </span>
            <span className="text-sm font-mono text-[#8A8D95]">/ 100</span>
          </div>
          <p className="text-xs text-[#60636B] mt-1 tabular-nums">
            Probability: {(risk.risk_probability * 100).toFixed(1)}%
          </p>
        </div>

        <div className="text-right">
          <span className="text-[11px] text-[#8A8D95] uppercase block font-medium">Model Engine</span>
          <span className="text-xs font-mono text-[#5844D6] font-medium">
            {risk.model_name || risk.model_type} v{risk.model_version}
          </span>
        </div>
      </div>

      {/* Explainable AI Explanation Box */}
      {risk.explanation && (
        <div className="p-3 rounded-lg bg-[#FAFAF9] border border-[#E5E5E2] text-xs text-[#17181C] leading-relaxed mb-4">
          <div className="flex items-center gap-1.5 text-[#5844D6] font-semibold mb-1">
            <Info className="h-3.5 w-3.5 text-[#6D5AE6]" />
            <span>Diagnosis Summary:</span>
          </div>
          {risk.explanation}
        </div>
      )}

      {/* Top Contributing Factors Waterfall */}
      {risk.top_factors && risk.top_factors.length > 0 && (
        <div className="space-y-2 pt-2 border-t border-[#E5E5E2]">
          <span className="text-xs font-semibold text-[#17181C] block">
            Top Driving Risk Factors:
          </span>
          <div className="space-y-1.5">
            {risk.top_factors.map((factor, index) => {
              const rawName = factor.display_name || factor.feature || factor.factor || factor.name || `Factor ${index + 1}`
              const name = String(rawName)
              const impact = factor.contribution ?? factor.score ?? 0
              const impactPercent = typeof impact === 'number' ? Math.round(impact * 100) : 0

              return (
                <div
                  key={index}
                  className="flex flex-col gap-1 p-2 rounded-lg bg-[#FAFAF9] border border-[#E5E5E2]"
                >
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-[#17181C] font-medium truncate max-w-[220px]">
                      • {name.replace(/_/g, ' ')}
                    </span>
                    {impactPercent > 0 && (
                      <span className="font-mono text-rose-600 font-semibold text-[11px] tabular-nums">
                        +{impactPercent}%
                      </span>
                    )}
                  </div>
                  {factor.description && (
                    <p className="text-[11px] text-[#60636B] pl-2 leading-tight">
                      {factor.description}
                    </p>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
