import { useEffect, useRef, useState } from 'react'
import { Bell, Building2, ChevronDown, Cpu, LogOut, Menu, Search } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { Breadcrumbs } from './Breadcrumbs'
import { useJobs } from '../../hooks/useJobs'
import { useSystemHealth } from '../../hooks/useSystemHealth'
import { useUiStore } from '../../stores/uiStore'
import { useAuthStore } from '../../stores/authStore'
import { authApi, type CompanyResponse } from '../../api/auth'

export function TopHeader() {
  const { setMobileDrawerOpen } = useUiStore()
  const { user, logout, switchWorkspace } = useAuthStore()
  const navigate = useNavigate()

  const [companies, setCompanies] = useState<CompanyResponse[]>([])
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Real backend job status
  const { data: jobsData } = useJobs(undefined, 1, 10)
  const activeJobs = (jobsData?.items ?? []).filter(
    (j) => j.status === 'PROCESSING' || j.status === 'STARTED' || j.status === 'PENDING',
  )

  // Real backend health status
  const { data: healthData, isError: healthError } = useSystemHealth()
  const isHealthy = !healthError && healthData?.status === 'ok'

  // Load companies for switcher
  useEffect(() => {
    if (user) {
      authApi.listCompanies().then(setCompanies).catch(() => {})
    }
  }, [user])

  // Close dropdown on click outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleSwitchCompany = async (companyId: string) => {
    try {
      await switchWorkspace(companyId)
      setDropdownOpen(false)
      window.location.reload()
    } catch {
      // ignore
    }
  }

  const handleLogout = () => {
    logout()
    navigate('/login', { replace: true })
  }

  const initials = user?.full_name
    ? user.full_name
        .split(' ')
        .map((n) => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2)
    : 'AI'

  const activeCompanyName = user?.company?.name || 'Workspace'

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
          className="flex items-center gap-2.5 w-64 md:w-80 px-3.5 py-1.5 rounded-lg border border-[#E5E5E2] bg-[#F7F7F5] text-xs text-neutral-500 hover:border-[#D1D1CD] hover:text-neutral-800 transition-colors cursor-pointer shadow-xs"
        >
          <Search className="h-3.5 w-3.5 text-neutral-400" />
          <span className="flex-1 text-left truncate">Search calls, transcripts, themes...</span>
          <kbd className="px-1.5 py-0.5 rounded bg-white text-[10px] text-neutral-500 border border-[#E5E5E2] font-mono shadow-xs">
            ⌘K
          </kbd>
        </button>
      </div>

      {/* Right Cluster */}
      <div className="flex items-center gap-2 sm:gap-3">
        {/* Active Jobs Pill */}
        {activeJobs.length > 0 && (
          <Link
            to="/jobs"
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-50 border border-amber-200 text-amber-700 text-xs font-medium"
            title={`${activeJobs.length} active background processing tasks`}
          >
            <Cpu className="h-3.5 w-3.5 text-amber-600 animate-spin" />
            <span className="hidden sm:inline">{activeJobs.length} Active Jobs</span>
            <span className="sm:hidden">{activeJobs.length}</span>
          </Link>
        )}

        {/* Backend API Connection Indicator */}
        <div
          className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-[#E5E5E2] bg-[#F7F7F5] text-xs font-mono"
          title={`Backend status: ${isHealthy ? 'Connected' : 'Offline'}`}
        >
          <span
            className={`h-2 w-2 rounded-full ${
              isHealthy ? 'bg-emerald-500' : 'bg-rose-500'
            }`}
          />
          <span className="text-neutral-600 text-[11px] font-sans font-medium">
            {isHealthy ? 'Connected' : 'Offline'}
          </span>
        </div>

        {/* Company Workspace Switcher Dropdown */}
        <div className="relative" ref={dropdownRef}>
          <button
            type="button"
            onClick={() => setDropdownOpen(!dropdownOpen)}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-[#E5E5E2] bg-white hover:bg-[#F7F7F5] text-xs font-medium text-[#17181C] transition-colors cursor-pointer shadow-xs"
            title="Active Company Workspace"
          >
            <Building2 className="h-3.5 w-3.5 text-[#6D5AE6]" />
            <span className="max-w-[120px] truncate">{activeCompanyName}</span>
            {companies.length > 1 && <ChevronDown className="h-3 w-3 text-neutral-400" />}
          </button>

          {dropdownOpen && (
            <div className="absolute right-0 mt-2 w-64 rounded-xl border border-[#E5E5E2] bg-white p-2 shadow-lg z-50 animate-in fade-in zoom-in-95 duration-100">
              <div className="px-2.5 py-1.5 text-[10px] font-semibold text-[#8A8D95] uppercase tracking-wider">
                Workspaces ({companies.length})
              </div>
              <div className="space-y-1 mt-1 max-h-48 overflow-y-auto">
                {companies.map((c) => {
                  const isCurrent = c.id === user?.company_id
                  return (
                    <button
                      key={c.id}
                      type="button"
                      onClick={() => handleSwitchCompany(c.id)}
                      className={`flex w-full items-center justify-between px-2.5 py-1.5 rounded-lg text-xs font-medium text-left transition-colors cursor-pointer ${
                        isCurrent
                          ? 'bg-[#F2F0FD] text-[#5844D6] font-semibold'
                          : 'text-[#17181C] hover:bg-[#F2F2F0]'
                      }`}
                    >
                      <span className="truncate">{c.name}</span>
                      {isCurrent && (
                        <span className="text-[10px] text-[#6D5AE6] font-mono px-1.5 py-0.5 rounded bg-white border border-[#DDD6FE]">
                          Active
                        </span>
                      )}
                    </button>
                  )
                })}
              </div>

              {/* User details and logout */}
              <div className="border-t border-[#E5E5E2] mt-2 pt-2 space-y-1">
                <div className="px-2.5 py-1 text-xs text-[#60636B]">
                  <div className="font-semibold text-[#17181C] truncate">{user?.full_name}</div>
                  <div className="text-[11px] truncate text-[#8A8D95]">{user?.email}</div>
                  <div className="mt-0.5 inline-block text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-neutral-100 text-neutral-600 font-semibold">
                    {user?.role}
                  </div>
                </div>

                <button
                  type="button"
                  onClick={handleLogout}
                  className="flex w-full items-center gap-2 px-2.5 py-1.5 text-xs font-medium text-rose-600 hover:bg-rose-50 rounded-lg transition-colors cursor-pointer"
                >
                  <LogOut className="h-3.5 w-3.5" />
                  <span>Sign Out</span>
                </button>
              </div>
            </div>
          )}
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

        {/* User Avatar */}
        <div
          onClick={() => setDropdownOpen(!dropdownOpen)}
          className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#F2F0FD] border border-[#DDD6FE] text-[#5844D6] text-xs font-bold font-mono cursor-pointer hover:border-[#6D5AE6] transition-colors"
          title={`${user?.full_name} (${user?.role})`}
        >
          {initials}
        </div>
      </div>
    </header>
  )
}
