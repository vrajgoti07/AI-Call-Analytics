import React, { useEffect } from 'react'
import { X } from 'lucide-react'
import { cn } from '../../lib/utils'

export interface DrawerProps {
  isOpen: boolean
  onClose: () => void
  title?: string
  children: React.ReactNode
  side?: 'left' | 'right'
  width?: string
  className?: string
}

export function Drawer({
  isOpen,
  onClose,
  title,
  children,
  side = 'right',
  width = 'max-w-md',
  className,
}: DrawerProps) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onClose])

  if (!isOpen) return null

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex bg-neutral-900/40 backdrop-blur-xs"
    >
      <div
        className="fixed inset-0"
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        className={cn(
          'relative w-full h-full bg-white border-[#E5E5E2] shadow-2xl flex flex-col z-10 transition-transform duration-200 text-[#17181C]',
          side === 'right' ? 'ml-auto border-l' : 'mr-auto border-r',
          width,
          className,
        )}
      >
        <div className="flex items-center justify-between border-b border-[#E5E5E2] px-6 py-4">
          <h3 className="text-base font-semibold text-[#17181C]">{title}</h3>
          <button
            type="button"
            onClick={onClose}
            className="text-neutral-400 hover:text-neutral-700 p-1.5 rounded-lg hover:bg-[#F2F2F0] cursor-pointer transition-colors"
            aria-label="Close drawer"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-6">{children}</div>
      </div>
    </div>
  )
}
