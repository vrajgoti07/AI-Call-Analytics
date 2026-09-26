/**
 * AI Call Analytics — Admin Companies Management Page.
 * Strictly restricted to platform ADMIN role.
 */

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Building2,
  CheckCircle2,
  XCircle,
  Search,
  Users,
  PhoneCall,
  FolderArchive,
  RefreshCw,
  Power,
  ShieldCheck,
} from 'lucide-react'
import { authApi, type AdminCompanyItem } from '../api/auth'
import { Button } from '../components/ui/Button'
import { EmptyState } from '../components/ui/EmptyState'

export function AdminCompaniesPage() {
  const queryClient = useQueryClient()
  const [searchTerm, setSearchTerm] = useState('')
  const [actionError, setActionError] = useState<string | null>(null)

  const {
    data: companies = [],
    isLoading,
    isRefetching,
    refetch,
    error,
  } = useQuery({
    queryKey: ['admin-companies'],
    queryFn: () => authApi.listAdminCompanies(),
  })

  const toggleStatusMutation = useMutation({
    mutationFn: ({ companyId, isActive }: { companyId: string; isActive: boolean }) =>
      authApi.updateCompanyStatus(companyId, isActive),
    onSuccess: (updated) => {
      queryClient.setQueryData<AdminCompanyItem[]>(['admin-companies'], (old) => {
        if (!old) return [updated]
        return old.map((c) => (c.id === updated.id ? updated : c))
      })
      setActionError(null)
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : 'Failed to update company status'
      setActionError(msg)
    },
  })

  const filteredCompanies = companies.filter(
    (c) =>
      c.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.slug.toLowerCase().includes(searchTerm.toLowerCase()),
  )

  const formatDate = (iso: string) => {
    try {
      return new Date(iso).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      })
    } catch {
      return iso
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold tracking-tight text-[#17181C]">Company Management</h1>
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-[#F2F0FD] text-[#5844D6]">
              <ShieldCheck className="h-3 w-3" />
              Admin
            </span>
          </div>
          <p className="text-xs text-[#60636B] mt-0.5">
            Platform-wide directory of registered company customer accounts and statuses.
          </p>
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={() => refetch()}
          disabled={isLoading || isRefetching}
          className="gap-2 shrink-0"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isRefetching ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {actionError && (
        <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs">
          {actionError}
        </div>
      )}

      {/* Filter Toolbar */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-[#8A8D95]" />
          <input
            type="text"
            placeholder="Search companies by name..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-3.5 py-1.5 rounded-lg border border-[#E5E5E2] bg-white text-xs text-[#17181C] placeholder-[#8A8D95] focus:outline-none focus:border-[#6D5AE6] focus:ring-1 focus:ring-[#6D5AE6]/20 transition-all"
          />
        </div>
        <div className="text-xs text-[#60636B] ml-auto">
          Total: <span className="font-semibold text-[#17181C]">{filteredCompanies.length}</span>
        </div>
      </div>

      {/* Companies Table */}
      <div className="rounded-xl border border-[#E5E5E2] bg-white overflow-hidden shadow-xs">
        {isLoading ? (
          <div className="p-8 space-y-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-12 rounded-lg bg-[#F7F7F5] animate-pulse" />
            ))}
          </div>
        ) : error ? (
          <div className="p-8 text-center">
            <EmptyState
              title="Unable to load companies"
              description="An error occurred while fetching company records."
              action={
                <Button size="sm" onClick={() => refetch()}>
                  Retry
                </Button>
              }
            />
          </div>
        ) : filteredCompanies.length === 0 ? (
          <div className="p-8 text-center">
            <EmptyState
              title="No companies found"
              description={searchTerm ? 'No companies match your search criteria.' : 'No registered companies exist yet.'}
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-[#E5E5E2] bg-[#FAFAF8] text-[#8A8D95] font-semibold uppercase tracking-wider text-[10px]">
                  <th className="py-3 px-4">Company</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-center">Users</th>
                  <th className="py-3 px-4 text-center">Batches</th>
                  <th className="py-3 px-4 text-center">Calls</th>
                  <th className="py-3 px-4">Created Date</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E5E5E2]">
                {filteredCompanies.map((c) => (
                  <tr key={c.id} className="hover:bg-[#FAFAF8] transition-colors">
                    <td className="py-3.5 px-4 font-medium text-[#17181C]">
                      <div className="flex items-center gap-2.5">
                        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#F2F0FD] text-[#5844D6]">
                          <Building2 className="h-4 w-4" />
                        </div>
                        <div>
                          <div className="font-semibold text-sm">{c.name}</div>
                          <div className="text-[11px] text-[#8A8D95] font-mono">{c.slug}</div>
                        </div>
                      </div>
                    </td>

                    <td className="py-3.5 px-4">
                      {c.is_active ? (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                          <CheckCircle2 className="h-3 w-3 text-emerald-600" />
                          Active
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-rose-50 text-rose-700 border border-rose-200">
                          <XCircle className="h-3 w-3 text-rose-600" />
                          Disabled
                        </span>
                      )}
                    </td>

                    <td className="py-3.5 px-4 text-center text-[#60636B] font-medium">
                      <span className="inline-flex items-center gap-1">
                        <Users className="h-3 w-3 text-[#8A8D95]" />
                        {c.user_count}
                      </span>
                    </td>

                    <td className="py-3.5 px-4 text-center text-[#60636B] font-medium">
                      <span className="inline-flex items-center gap-1">
                        <FolderArchive className="h-3 w-3 text-[#8A8D95]" />
                        {c.batch_count}
                      </span>
                    </td>

                    <td className="py-3.5 px-4 text-center text-[#60636B] font-medium">
                      <span className="inline-flex items-center gap-1">
                        <PhoneCall className="h-3 w-3 text-[#8A8D95]" />
                        {c.call_count}
                      </span>
                    </td>

                    <td className="py-3.5 px-4 text-[#60636B]">{formatDate(c.created_at)}</td>

                    <td className="py-3.5 px-4 text-right">
                      <Button
                        variant={c.is_active ? 'outline' : 'primary'}
                        size="sm"
                        disabled={toggleStatusMutation.isPending}
                        onClick={() =>
                          toggleStatusMutation.mutate({
                            companyId: c.id,
                            isActive: !c.is_active,
                          })
                        }
                        className={`h-7 px-2.5 text-xs gap-1.5 ${
                          c.is_active
                            ? 'text-rose-700 hover:bg-rose-50 hover:border-rose-300'
                            : 'bg-emerald-600 hover:bg-emerald-700 text-white'
                        }`}
                      >
                        <Power className="h-3 w-3" />
                        {c.is_active ? 'Deactivate' : 'Activate'}
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
