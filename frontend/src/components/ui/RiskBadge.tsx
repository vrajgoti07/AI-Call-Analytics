import React from 'react'
import { RISK_CONFIG } from '../../lib/constants'
import { cn } from '../../lib/utils'

export interface RiskBadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  level: string | null | undefined
  score?: number | null
}

export function RiskBadge({ level, score, className, ...props }: RiskBadgeProps) {
  if (!level && (score === null || score === undefined)) {
    return <span className="text-xs text-slate-500 font-mono">--</span>
  }

  // Infer level if only score is provided
  let normLevel = level ? level.toLowerCase() : 'low'
  if (!level && score !== null && score !== undefined) {
    if (score >= 70) normLevel = 'high'
    else if (score >= 40) normLevel = 'medium'
    else normLevel = 'low'
  }

  const config = RISK_CONFIG[normLevel] ?? {
    label: (level ?? 'RISK').toUpperCase(),
    symbol: '▲',
    bgClass: 'bg-neutral-100',
    textClass: 'text-neutral-700',
    borderClass: 'border-neutral-200',
  }

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-xs font-semibold border font-mono tracking-wide select-none',
        config.bgClass,
        config.textClass,
        config.borderClass,
        className,
      )}
      {...props}
    >
      <span aria-hidden="true" className="text-[10px]">
        {config.symbol}
      </span>
      <span>{config.label}</span>
      {score !== undefined && score !== null && (
        <span className="font-bold text-current ml-0.5 tabular-nums">{Math.round(score)}</span>
      )}
    </span>
  )
}
