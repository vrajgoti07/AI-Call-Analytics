import { ChevronRight, Home } from 'lucide-react'
import { Link, useLocation } from 'react-router-dom'

export function Breadcrumbs() {
  const location = useLocation()
  const pathnames = location.pathname.split('/').filter(Boolean)

  if (pathnames.length === 0) {
    return (
      <div className="flex items-center gap-1.5 text-xs text-neutral-500">
        <Home className="h-3.5 w-3.5 text-[#6D5AE6]" />
        <span>Overview</span>
      </div>
    )
  }

  return (
    <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 text-xs text-neutral-500">
      <Link to="/overview" className="hover:text-neutral-900 flex items-center gap-1">
        <Home className="h-3.5 w-3.5 text-neutral-400 hover:text-[#6D5AE6] transition-colors" />
      </Link>
      {pathnames.map((name, index) => {
        const routeTo = `/${pathnames.slice(0, index + 1).join('/')}`
        const isLast = index === pathnames.length - 1
        const formattedName =
          name.length > 20
            ? `${name.slice(0, 8)}...${name.slice(-4)}`
            : name.charAt(0).toUpperCase() + name.slice(1)

        return (
          <div key={routeTo} className="flex items-center gap-1.5">
            <ChevronRight className="h-3 w-3 text-neutral-300" />
            {isLast ? (
              <span className="font-semibold text-neutral-900">{formattedName}</span>
            ) : (
              <Link to={routeTo} className="hover:text-neutral-900 transition-colors">
                {formattedName}
              </Link>
            )}
          </div>
        )
      })}
    </nav>
  )
}
