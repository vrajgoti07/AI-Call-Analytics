import React from 'react'
import { cn } from '../../lib/utils'

export interface MetricCardProps {
  title: string
  value: string | number
  subtext?: string
  trend?: {
    value: string
    isPositive?: boolean
  }
  icon?: React.ReactNode
  className?: string
  loading?: boolean
}

export function MetricCard({
  title,
  value,
  subtext,
  trend,
  icon,
  className,
  loading = false,
}: MetricCardProps) {
  if (loading) {
    return (
      <div
        className={cn(
          'p-5 rounded-xl border border-[#E5E5E2] bg-white animate-pulse space-y-3 shadow-xs',
          className,
        )}
      >
        <div className="h-4 bg-[#F2F2F0] rounded w-2/3" />
        <div className="h-8 bg-[#F2F2F0] rounded w-1/2" />
        <div className="h-3 bg-[#F2F2F0] rounded w-1/3" />
      </div>
    )
  }

  return (
    <div
      className={cn(
        'p-5 rounded-xl border border-[#E5E5E2] bg-white shadow-xs transition-all hover:border-[#D1D1CD] hover:shadow-sm',
        className,
      )}
    >
      <div className="flex items-center justify-between text-[#60636B] text-sm font-medium">
        <span>{title}</span>
        {icon && <div className="shrink-0">{icon}</div>}
      </div>

      <div className="mt-3 flex items-baseline gap-2">
        <span className="text-2xl sm:text-3xl font-bold tracking-tight text-[#17181C] tabular-nums">
          {value}
        </span>
        {trend && (
          <span
            className={cn(
              'text-xs font-semibold px-2 py-0.5 rounded tabular-nums border',
              trend.isPositive
                ? 'text-emerald-700 bg-emerald-50 border-emerald-200'
                : 'text-rose-700 bg-rose-50 border-rose-200',
            )}
          >
            {trend.value}
          </span>
        )}
      </div>

      {subtext && (
        <p className="mt-1.5 text-xs text-[#60636B] leading-relaxed">{subtext}</p>
      )}
    </div>
  )
}
