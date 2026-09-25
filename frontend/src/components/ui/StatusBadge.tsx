import React from 'react'
import { STATUS_CONFIG } from '../../lib/constants'
import { cn } from '../../lib/utils'

export interface StatusBadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  status: string | null | undefined
}

export function StatusBadge({ status, className, ...props }: StatusBadgeProps) {
  const normStatus = (status ?? 'QUEUED').toUpperCase()
  const config = STATUS_CONFIG[normStatus] ?? {
    label: normStatus,
    icon: '●',
    bgClass: 'bg-neutral-100',
    textClass: 'text-neutral-700',
    borderClass: 'border-neutral-200',
  }

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border font-mono tracking-wide',
        config.bgClass,
        config.textClass,
        config.borderClass,
        className,
      )}
      {...props}
    >
      <span className="text-[10px]" aria-hidden="true">
        {config.icon}
      </span>
      <span>{config.label}</span>
    </span>
  )
}
