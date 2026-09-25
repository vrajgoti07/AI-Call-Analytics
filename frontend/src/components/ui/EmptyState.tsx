import React from 'react'
import { Inbox } from 'lucide-react'
import { cn } from '../../lib/utils'

export interface EmptyStateProps {
  icon?: React.ReactNode
  title: string
  description?: string
  action?: React.ReactNode
  className?: string
}

export function EmptyState({
  icon = <Inbox className="h-5 w-5 text-neutral-400" />,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center p-6 text-center rounded-xl border border-dashed border-[#E5E5E2] bg-white',
        className,
      )}
    >
      <div className="mb-2.5 flex h-10 w-10 items-center justify-center rounded-lg bg-[#F7F7F5] text-neutral-400">
        {icon}
      </div>
      <h3 className="text-sm font-semibold text-[#17181C]">{title}</h3>
      {description && (
        <p className="mt-1 max-w-sm text-xs text-[#60636B] leading-relaxed">
          {description}
        </p>
      )}
      {action && <div className="mt-3.5">{action}</div>}
    </div>
  )
}
