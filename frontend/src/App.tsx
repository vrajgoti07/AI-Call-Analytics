import { useQuery } from '@tanstack/react-query'
import { Activity, CheckCircle, XCircle } from 'lucide-react'

/**
 * API base URL — reads from env or defaults to localhost.
 */
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

/**
 * Fetch health status from the backend.
 */
async function fetchHealth(): Promise<{ status: string; service: string }> {
  const res = await fetch(`${API_BASE}/health`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

function App() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['health'],
    queryFn: fetchHealth,
    refetchInterval: 30_000,
  })

  return (
    <div className="min-h-screen flex items-center justify-center p-8">
      <div className="w-full max-w-md rounded-2xl border border-[var(--color-surface-lighter)] bg-[var(--color-surface-light)] p-8 shadow-2xl">
        {/* Header */}
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-[var(--color-primary)] shadow-lg shadow-[var(--color-primary)]/25">
            <Activity className="h-8 w-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-[var(--color-text)]">
            AI Call Analytics
          </h1>
          <p className="mt-1 text-sm text-[var(--color-text-muted)]">
            System Health Check
          </p>
        </div>

        {/* Status Card */}
        <div className="rounded-xl border border-[var(--color-surface-lighter)] bg-[var(--color-surface)] p-6">
          {isLoading && (
            <div className="flex items-center gap-3 text-[var(--color-text-muted)]">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-current border-t-transparent" />
              <span>Checking backend status…</span>
            </div>
          )}

          {isError && (
            <div className="flex items-center gap-3 text-[var(--color-danger)]">
              <XCircle className="h-5 w-5 shrink-0" />
              <div>
                <p className="font-medium">Backend unreachable</p>
                <p className="mt-1 text-xs text-[var(--color-text-muted)]">
                  {(error as Error).message}
                </p>
              </div>
            </div>
          )}

          {data && (
            <div className="space-y-4">
              <div className="flex items-center gap-3 text-[var(--color-success)]">
                <CheckCircle className="h-5 w-5 shrink-0" />
                <span className="font-medium">Backend is running</span>
              </div>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-[var(--color-text-muted)]">Status</span>
                  <span className="font-mono">{data.status}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[var(--color-text-muted)]">Service</span>
                  <span className="font-mono text-xs">{data.service}</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <p className="mt-6 text-center text-xs text-[var(--color-text-muted)]">
          Phase 0 — Foundation
        </p>
      </div>
    </div>
  )
}

export default App
