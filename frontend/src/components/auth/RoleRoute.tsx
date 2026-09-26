/**
 * AI Call Analytics — Role Guard Route Component.
 * Restricts child routes to specified user roles (e.g. ADMIN vs COMPANY).
 */

import { Link, Outlet } from 'react-router-dom'
import { ShieldAlert } from 'lucide-react'
import { useAuthStore } from '../../stores/authStore'
import { type UserRole } from '../../api/auth'
import { Button } from '../ui/Button'
import { EmptyState } from '../ui/EmptyState'

interface RoleRouteProps {
  allowedRoles: UserRole[]
}

export function RoleRoute({ allowedRoles }: RoleRouteProps) {
  const { user } = useAuthStore()

  const userRole = user?.role

  if (!userRole || !allowedRoles.includes(userRole)) {
    return (
      <div className="py-16 px-4">
        <EmptyState
          title="Access Denied (403)"
          description={`Your current role (${userRole || 'Unknown'}) is not authorized to access this section. This area requires ${allowedRoles.join(' or ')} privileges.`}
          icon={<ShieldAlert className="h-10 w-10 text-rose-500" />}
          action={
            <Link to="/overview">
              <Button size="sm">Return to Overview</Button>
            </Link>
          }
        />
      </div>
    )
  }

  return <Outlet />
}
