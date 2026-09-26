import React from 'react'
import {
  Activity,
  AlertTriangle,
  Building2,
  ChevronLeft,
  ChevronRight,
  Cpu,
  FileText,
  FolderArchive,
  LayoutDashboard,
  PhoneCall,
  Search,
  Settings,
  Sparkles,
} from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { useUiStore } from '../../stores/uiStore'
import { useAuthStore } from '../../stores/authStore'
import { cn } from '../../lib/utils'

interface NavItem {
  name: string
  to: string
  icon: React.ComponentType<{ className?: string }>
  badge?: string
}

interface NavSection {
  title: string
  items: NavItem[]
}

const companySections: NavSection[] = [
  {
    title: 'Main',
    items: [
      { name: 'Overview', to: '/overview', icon: LayoutDashboard },
      { name: 'ZIP Batches', to: '/batches', icon: FolderArchive },
      { name: 'Calls', to: '/calls', icon: PhoneCall },
    ],
  },
  {
    title: 'Analytics',
    items: [
      { name: 'Reports', to: '/reports', icon: FileText },
      { name: 'Themes', to: '/themes', icon: Sparkles },
      { name: 'Escalation Risk', to: '/risk', icon: AlertTriangle },
    ],
  },
  {
    title: 'Tools',
    items: [
      { name: 'Semantic Search', to: '/search', icon: Search },
    ],
  },
  {
    title: 'Account',
    items: [
      { name: 'Profile / Settings', to: '/profile', icon: Settings },
    ],
  },
]

const adminSections: NavSection[] = [
  {
    title: 'Main',
    items: [
      { name: 'Overview', to: '/overview', icon: LayoutDashboard },
    ],
  },
  {
    title: 'Administration',
    items: [
      { name: 'Companies', to: '/admin/companies', icon: Building2 },
      { name: 'System Settings', to: '/settings', icon: Settings },
    ],
  },
  {
    title: 'Operations',
    items: [
      { name: 'Processing Jobs', to: '/jobs', icon: Cpu },
      { name: 'AI Evaluation', to: '/evaluation', icon: Activity },
    ],
  },
  {
    title: 'Platform Analytics',
    items: [
      { name: 'ZIP Batches', to: '/batches', icon: FolderArchive },
      { name: 'Calls', to: '/calls', icon: PhoneCall },
      { name: 'Reports', to: '/reports', icon: FileText },
    ],
  },
]

export function Sidebar({ className }: { className?: string }) {
  const { sidebarCollapsed, toggleSidebar, mobileDrawerOpen, setMobileDrawerOpen } = useUiStore()
  const { user } = useAuthStore()

  const navSections = user?.role === 'ADMIN' ? adminSections : companySections

  const sidebarContent = (
    <div className="flex h-full flex-col justify-between p-4 bg-white border-r border-[#E5E5E2]">
      <div className="space-y-6">
        {/* Brand Header */}
        <div className="flex items-center gap-3 px-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#6D5AE6] text-white shadow-sm shadow-[#6D5AE6]/20">
            <Activity className="h-5 w-5" />
          </div>
          {!sidebarCollapsed && (
            <div>
              <h1 className="text-sm font-semibold tracking-tight text-[#17181C]">
                AI Call Analytics
              </h1>
              <p className="text-[11px] text-[#60636B] font-medium">
                {user?.role === 'ADMIN' ? 'Platform Administration' : 'Enterprise Intelligence'}
              </p>
            </div>
          )}
        </div>

        {/* Navigation Groups */}
        <nav className="space-y-5" aria-label="Main Navigation">
          {navSections.map((section) => (
            <div key={section.title} className="space-y-1">
              {!sidebarCollapsed && (
                <div className="px-3 text-[11px] font-semibold text-[#8A8D95] uppercase tracking-wider">
                  {section.title}
                </div>
              )}
              {section.items.map((item) => {
                const Icon = item.icon
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    onClick={() => setMobileDrawerOpen(false)}
                    className={({ isActive }) =>
                      cn(
                        'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors cursor-pointer select-none',
                        isActive
                          ? 'bg-[#F2F0FD] text-[#5844D6] font-semibold shadow-xs'
                          : 'text-[#60636B] hover:text-[#17181C] hover:bg-[#F2F2F0]',
                        sidebarCollapsed && 'justify-center px-2',
                      )
                    }
                    title={sidebarCollapsed ? item.name : undefined}
                  >
                    <Icon className="h-4 w-4 shrink-0 text-current" />
                    {!sidebarCollapsed && <span>{item.name}</span>}
                  </NavLink>
                )
              })}
            </div>
          ))}
        </nav>
      </div>

      {/* Footer / Toggle Button (Desktop only) */}
      <div className="hidden md:block border-t border-[#E5E5E2] pt-3">
        <button
          type="button"
          onClick={toggleSidebar}
          className="flex w-full items-center gap-3 px-3 py-2 text-xs font-medium text-[#60636B] hover:text-[#17181C] hover:bg-[#F2F2F0] rounded-lg cursor-pointer transition-colors"
        >
          {sidebarCollapsed ? (
            <ChevronRight className="h-4 w-4 mx-auto" />
          ) : (
            <>
              <ChevronLeft className="h-4 w-4" />
              <span>Collapse sidebar</span>
            </>
          )}
        </button>
      </div>
    </div>
  )

  return (
    <>
      {/* Desktop Sidebar */}
      <aside
        className={cn(
          'hidden md:block transition-all duration-200 shrink-0 z-30',
          sidebarCollapsed ? 'w-16' : 'w-60',
          className,
        )}
      >
        {sidebarContent}
      </aside>

      {/* Mobile Drawer */}
      {mobileDrawerOpen && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex md:hidden bg-neutral-900/30 backdrop-blur-xs"
        >
          <div
            className="fixed inset-0"
            onClick={() => setMobileDrawerOpen(false)}
            aria-hidden="true"
          />
          <div className="relative w-64 h-full bg-white shadow-xl z-10 animate-in slide-in-from-left duration-200">
            {sidebarContent}
          </div>
        </div>
      )}
    </>
  )
}
