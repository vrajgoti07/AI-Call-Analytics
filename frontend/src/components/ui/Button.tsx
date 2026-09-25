import React from 'react'
import { Loader2 } from 'lucide-react'
import { cn } from '../../lib/utils'

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'outline'
  size?: 'sm' | 'md' | 'lg'
  isLoading?: boolean
  leftIcon?: React.ReactNode
  rightIcon?: React.ReactNode
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = 'primary',
      size = 'md',
      isLoading = false,
      leftIcon,
      rightIcon,
      children,
      disabled,
      ...props
    },
    ref,
  ) => {
    const baseStyles =
      'inline-flex items-center justify-center font-medium rounded-lg transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#6D5AE6] focus-visible:ring-offset-2 focus-visible:ring-offset-white disabled:opacity-50 disabled:pointer-events-none cursor-pointer select-none active:scale-[0.98]'

    const sizeStyles = {
      sm: 'text-xs px-3 py-1.5 gap-1.5',
      md: 'text-sm px-4 py-2 gap-2',
      lg: 'text-base px-5 py-2.5 gap-2.5',
    }

    const variantStyles = {
      primary: 'bg-[#6D5AE6] hover:bg-[#5844D6] active:bg-[#4834C4] text-white shadow-xs',
      secondary: 'bg-white hover:bg-[#F2F2F0] text-[#17181C] border border-[#E5E5E2] shadow-xs',
      ghost: 'bg-transparent hover:bg-[#F2F2F0] text-[#60636B] hover:text-[#17181C]',
      danger: 'bg-rose-600 hover:bg-rose-700 active:bg-rose-800 text-white shadow-xs',
      outline: 'bg-transparent border border-[#E5E5E2] hover:bg-[#F2F2F0] text-[#17181C]',
    }

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={cn(baseStyles, sizeStyles[size], variantStyles[variant], className)}
        {...props}
      >
        {isLoading ? (
          <Loader2 className="h-4 w-4 animate-spin text-current" />
        ) : (
          leftIcon
        )}
        {children}
        {!isLoading && rightIcon}
      </button>
    )
  },
)

Button.displayName = 'Button'
