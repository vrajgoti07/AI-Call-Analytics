import React from 'react'
import { cn } from '../../lib/utils'

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  helperText?: string
  leftIcon?: React.ReactNode
  rightIcon?: React.ReactNode
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, helperText, leftIcon, rightIcon, id, ...props }, ref) => {
    const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined)

    return (
      <div className="w-full space-y-1.5">
        {label && (
          <label htmlFor={inputId} className="block text-xs font-medium text-[#17181C]">
            {label}
          </label>
        )}
        <div className="relative flex items-center">
          {leftIcon && (
            <div className="absolute left-3 text-[#8A8D95] pointer-events-none">{leftIcon}</div>
          )}
          <input
            id={inputId}
            ref={ref}
            className={cn(
              'w-full rounded-lg border border-[#E5E5E2] bg-white px-3.5 py-2 text-sm text-[#17181C] placeholder-[#8A8D95] shadow-xs transition-colors focus:border-[#6D5AE6] focus:outline-none focus:ring-1 focus:ring-[#6D5AE6] disabled:opacity-50 disabled:bg-[#F2F2F0] disabled:cursor-not-allowed',
              leftIcon ? 'pl-9' : undefined,
              rightIcon ? 'pr-9' : undefined,
              error ? 'border-rose-500 focus:border-rose-500 focus:ring-rose-500' : undefined,
              className,
            )}
            {...props}
          />
          {rightIcon && <div className="absolute right-3 text-[#8A8D95]">{rightIcon}</div>}
        </div>
        {error && <p className="text-xs text-rose-600 font-medium">{error}</p>}
        {helperText && !error && <p className="text-xs text-[#60636B]">{helperText}</p>}
      </div>
    )
  },
)

Input.displayName = 'Input'
