/**
AI Call Analytics — Protected Route Authentication Guard.
 */

import { useEffect } from 'react'
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { Activity } from 'lucide-react'
import { useAuthStore } from '../../stores/authStore'

export function ProtectedRoute() {
  const { isAuthenticated, isInitializing, initializeAuth } = useAuthStore()
  const location = useLocation()

  useEffect(() => {
    initializeAuth()
  }, [initializeAuth])

  if (isInitializing) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-[#FAFAF8]">
        <div className="flex flex-col items-center gap-4 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-[#6D5AE6] text-white shadow-lg shadow-[#6D5AE6]/25 animate-pulse">
            <Activity className="h-6 w-6" />
          </div>
          <div className="space-y-1">
            <h2 className="text-sm font-semibold text-[#17181C]">Authenticating Session</h2>
            <p className="text-xs text-[#60636B]">Verifying workspace credentials...</p>
          </div>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return <Outlet />
}
