import React from 'react'
import { cn } from '../../lib/utils'

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string
  error?: string
  options?: Array<{ label: string; value: string | number }>
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, label, error, options, children, id, ...props }, ref) => {
    const selectId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined)

    return (
      <div className="w-full space-y-1.5">
        {label && (
          <label htmlFor={selectId} className="block text-xs font-medium text-[#17181C]">
            {label}
          </label>
        )}
        <select
          id={selectId}
          ref={ref}
          className={cn(
            'w-full rounded-lg border border-[#E5E5E2] bg-white px-3 py-2 text-sm text-[#17181C] shadow-xs transition-colors focus:border-[#6D5AE6] focus:outline-none focus:ring-1 focus:ring-[#6D5AE6] disabled:opacity-50 disabled:bg-[#F2F2F0] cursor-pointer',
            error && 'border-rose-500',
            className,
          )}
          {...props}
        >
          {options
            ? options.map((opt) => (
                <option key={opt.value} value={opt.value} className="bg-white text-[#17181C]">
                  {opt.label}
                </option>
              ))
            : children}
        </select>
        {error && <p className="text-xs text-rose-600 font-medium">{error}</p>}
      </div>
    )
  },
)

Select.displayName = 'Select'
