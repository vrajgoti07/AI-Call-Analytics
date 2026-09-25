
export interface ChartTooltipProps {
  active?: boolean
  payload?: Array<{
    name: string
    value: number | string
    color?: string
    payload?: Record<string, unknown>
  }>
  label?: string
  formatter?: (value: number | string) => string
}

export function ChartTooltip({ active, payload, label, formatter }: ChartTooltipProps) {
  if (!active || !payload || payload.length === 0) {
    return null
  }

  return (
    <div className="rounded-lg border border-[#E5E5E2] bg-white p-2.5 shadow-sm text-xs space-y-1.5 min-w-[120px]">
      {label && <div className="font-semibold text-[#17181C]">{label}</div>}
      {payload.map((entry, index) => {
        const displayValue = formatter ? formatter(entry.value) : entry.value
        return (
          <div key={`item-${index}`} className="flex items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-1.5">
              {entry.color && (
                <span
                  className="h-2 w-2 rounded-full shrink-0"
                  style={{ backgroundColor: entry.color }}
                />
              )}
              <span className="text-[#60636B]">{entry.name}</span>
            </div>
            <span className="font-mono font-semibold text-[#17181C] tabular-nums">
              {displayValue}
            </span>
          </div>
        )
      })}
    </div>
  )
}
