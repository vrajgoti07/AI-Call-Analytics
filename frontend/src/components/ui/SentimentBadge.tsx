import React from 'react'
import { SENTIMENT_CONFIG } from '../../lib/constants'
import { cn } from '../../lib/utils'

export interface SentimentBadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  sentiment: string | null | undefined
  score?: number | null
}

export function SentimentBadge({ sentiment, score, className, ...props }: SentimentBadgeProps) {
  if (!sentiment) {
    return <span className="text-xs text-slate-500 font-mono">--</span>
  }

  const norm = sentiment.toLowerCase()
  const config = SENTIMENT_CONFIG[norm] ?? {
    label: sentiment.toUpperCase(),
    symbol: '―',
    bgClass: 'bg-neutral-100',
    textClass: 'text-neutral-700',
    borderClass: 'border-neutral-200',
  }

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-xs font-semibold border font-mono tracking-wide',
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
        <span className="opacity-75 text-[10px] tabular-nums">({score > 0 ? `+${score.toFixed(2)}` : score.toFixed(2)})</span>
      )}
    </span>
  )
}
