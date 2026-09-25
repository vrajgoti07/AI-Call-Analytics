import { Bell, Cpu, Menu, Search } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { Breadcrumbs } from './Breadcrumbs'
import { useJobs } from '../../hooks/useJobs'
import { useSystemHealth } from '../../hooks/useSystemHealth'
import { useUiStore } from '../../stores/uiStore'

export function TopHeader() {
  const { setMobileDrawerOpen } = useUiStore()
  const navigate = useNavigate()

  // Real backend job status
  const { data: jobsData } = useJobs(undefined, 1, 10)
  const activeJobs = (jobsData?.items ?? []).filter(
    (j) => j.status === 'PROCESSING' || j.status === 'STARTED' || j.status === 'PENDING',
  )

  // Real backend health status
  const { data: healthData, isError: healthError } = useSystemHealth()
  const isHealthy = !healthError && healthData?.status === 'ok'

  return (
    <header className="h-16 shrink-0 border-b border-[#E5E5E2] bg-white px-4 sm:px-6 flex items-center justify-between z-20">
      {/* Left Cluster */}
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => setMobileDrawerOpen(true)}
          className="md:hidden p-2 text-neutral-500 hover:text-neutral-900 rounded-lg hover:bg-neutral-100 cursor-pointer transition-colors"
          aria-label="Open navigation menu"
        >
          <Menu className="h-5 w-5" />
        </button>

        <Breadcrumbs />
      </div>

      {/* Center / Search Bar */}
      <div className="hidden sm:flex items-center">
        <button
          type="button"
          onClick={() => navigate('/search')}
          className="flex items-center gap-2.5 w-72 md:w-96 px-3.5 py-1.5 rounded-lg border border-[#E5E5E2] bg-[#F7F7F5] text-xs text-neutral-500 hover:border-[#D1D1CD] hover:text-neutral-800 transition-colors cursor-pointer shadow-xs"
        >
          <Search className="h-3.5 w-3.5 text-neutral-400" />
          <span className="flex-1 text-left">Search calls, transcripts, themes...</span>
          <kbd className="px-1.5 py-0.5 rounded bg-white text-[10px] text-neutral-500 border border-[#E5E5E2] font-mono shadow-xs">
            ⌘K
          </kbd>
        </button>
      </div>

      {/* Right Cluster */}
      <div className="flex items-center gap-3">
        {/* Active Jobs Pill */}
        {activeJobs.length > 0 && (
          <Link
            to="/jobs"
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-50 border border-amber-200 text-amber-700 text-xs font-medium"
            title={`${activeJobs.length} active background processing tasks`}
          >
            <Cpu className="h-3.5 w-3.5 text-amber-600 animate-spin" />
            <span>{activeJobs.length} Active Jobs</span>
          </Link>
        )}

        {/* Backend API Connection Indicator */}
        <div
          className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-[#E5E5E2] bg-[#F7F7F5] text-xs font-mono"
          title={`Backend status: ${isHealthy ? 'Connected' : 'Offline'}`}
        >
          <span
            className={`h-2 w-2 rounded-full ${
              isHealthy ? 'bg-emerald-500' : 'bg-rose-500'
            }`}
          />
          <span className="text-neutral-600 text-[11px] font-sans font-medium">
            API: {isHealthy ? 'Connected' : 'Offline'}
          </span>
        </div>

        {/* Risk Alerts */}
        <Link
          to="/risk"
          className="p-2 text-neutral-500 hover:text-neutral-900 rounded-lg hover:bg-neutral-100 transition-colors cursor-pointer"
          title="Escalation Risk Dashboard"
          aria-label="Escalation Risk Dashboard"
        >
          <Bell className="h-4 w-4" />
        </Link>

        {/* User / Workspace Avatar */}
        <div className="flex items-center gap-2 pl-2 border-l border-[#E5E5E2]">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#F2F0FD] border border-[#DDD6FE] text-[#5844D6] text-xs font-bold font-mono">
            AI
          </div>
        </div>
      </div>
    </header>
  )
}
