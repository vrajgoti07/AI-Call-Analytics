import { cn } from '../../lib/utils'

export interface TabItem {
  id: string
  label: string
  count?: number
  icon?: React.ReactNode
}

export interface TabsProps {
  tabs: TabItem[]
  activeTab: string
  onChange: (tabId: string) => void
  className?: string
}

export function Tabs({ tabs, activeTab, onChange, className }: TabsProps) {
  return (
    <div className={cn('flex items-center gap-1 border-b border-[#E5E5E2] pb-1', className)}>
      {tabs.map((tab) => {
        const isActive = tab.id === activeTab
        return (
          <button
            key={tab.id}
            type="button"
            onClick={() => onChange(tab.id)}
            className={cn(
              'flex items-center gap-2 px-3.5 py-2 text-sm font-medium rounded-lg transition-colors cursor-pointer select-none',
              isActive
                ? 'bg-[#F2F0FD] text-[#5844D6] border border-[#DDD6FE] font-semibold shadow-xs'
                : 'text-[#60636B] hover:text-[#17181C] hover:bg-[#F2F2F0]',
            )}
          >
            {tab.icon}
            <span>{tab.label}</span>
            {tab.count !== undefined && (
              <span
                className={cn(
                  'text-xs px-2 py-0.5 rounded-full font-mono tabular-nums',
                  isActive
                    ? 'bg-[#EDE9FE] text-[#5844D6]'
                    : 'bg-neutral-100 text-neutral-600',
                )}
              >
                {tab.count}
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}
