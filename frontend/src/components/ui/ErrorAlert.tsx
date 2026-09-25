import React from 'react'
import { AlertCircle, RefreshCw } from 'lucide-react'
import { Button } from './Button'
import { cn } from '../../lib/utils'

export interface ErrorAlertProps {
  title?: string
  message: string
  details?: unknown
  onRetry?: () => void
  className?: string
}

export function ErrorAlert({
  title = 'An error occurred',
  message,
  details,
  onRetry,
  className,
}: ErrorAlertProps) {
  const [showDetails, setShowDetails] = React.useState(false)

  return (
    <div
      className={cn(
        'rounded-xl border border-rose-200 bg-rose-50/70 p-4 text-[#17181C] shadow-xs',
        className,
      )}
    >
      <div className="flex items-start gap-3">
        <AlertCircle className="h-5 w-5 text-rose-600 shrink-0 mt-0.5" />
        <div className="flex-1 space-y-1">
          <h4 className="text-sm font-semibold text-rose-800">{title}</h4>
          <p className="text-xs text-rose-700 leading-relaxed">{message}</p>

          {Boolean(details) && (
            <div className="pt-2">
              <button
                type="button"
                onClick={() => setShowDetails(!showDetails)}
                className="text-xs text-rose-600 underline hover:text-rose-800 cursor-pointer font-medium"
              >
                {showDetails ? 'Hide technical details' : 'Show technical details'}
              </button>
              {showDetails && (
                <pre className="mt-2 max-h-40 overflow-auto rounded bg-white p-2.5 text-[11px] text-neutral-800 font-mono border border-rose-200">
                  {typeof details === 'string'
                    ? details
                    : JSON.stringify(details, null, 2)}
                </pre>
              )}
            </div>
          )}
        </div>

        {onRetry && (
          <Button
            size="sm"
            variant="outline"
            onClick={onRetry}
            leftIcon={<RefreshCw className="h-3.5 w-3.5" />}
            className="border-rose-300 text-rose-700 hover:bg-rose-100/60 bg-white"
          >
            Retry
          </Button>
        )}
      </div>
    </div>
  )
}
