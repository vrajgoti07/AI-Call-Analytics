import { Suspense, lazy } from 'react'
import { Link, Navigate, Route, Routes } from 'react-router-dom'
import { ApplicationShell } from '../components/layout/ApplicationShell'
import { ProtectedRoute } from '../components/auth/ProtectedRoute'
import { RoleRoute } from '../components/auth/RoleRoute'
import { EmptyState } from '../components/ui/EmptyState'
import { Button } from '../components/ui/Button'

// Auth Pages
const LoginPage = lazy(() =>
  import('../pages/LoginPage').then((m) => ({ default: m.LoginPage })),
)
const RegisterPage = lazy(() =>
  import('../pages/RegisterPage').then((m) => ({ default: m.RegisterPage })),
)
const ForgotPasswordPage = lazy(() =>
  import('../pages/ForgotPasswordPage').then((m) => ({ default: m.ForgotPasswordPage })),
)

// App Pages (Lazy-loaded for code-splitting)
const OverviewPage = lazy(() =>
  import('../pages/OverviewPage').then((m) => ({ default: m.OverviewPage })),
)
const BatchesPage = lazy(() =>
  import('../pages/BatchesPage').then((m) => ({ default: m.BatchesPage })),
)
const BatchDetailPage = lazy(() =>
  import('../pages/BatchDetailPage').then((m) => ({ default: m.BatchDetailPage })),
)
const CallsPage = lazy(() =>
  import('../pages/CallsPage').then((m) => ({ default: m.CallsPage })),
)
const CallDetailPage = lazy(() =>
  import('../pages/CallDetailPage').then((m) => ({ default: m.CallDetailPage })),
)
const SearchPage = lazy(() =>
  import('../pages/SearchPage').then((m) => ({ default: m.SearchPage })),
)
const ThemesPage = lazy(() =>
  import('../pages/ThemesPage').then((m) => ({ default: m.ThemesPage })),
)
const ThemeDetailPage = lazy(() =>
  import('../pages/ThemeDetailPage').then((m) => ({ default: m.ThemeDetailPage })),
)
const RiskPage = lazy(() =>
  import('../pages/RiskPage').then((m) => ({ default: m.RiskPage })),
)
const ReportsPage = lazy(() =>
  import('../pages/ReportsPage').then((m) => ({ default: m.ReportsPage })),
)
const EvaluationPage = lazy(() =>
  import('../pages/EvaluationPage').then((m) => ({ default: m.EvaluationPage })),
)
const JobsPage = lazy(() =>
  import('../pages/JobsPage').then((m) => ({ default: m.JobsPage })),
)
const SettingsPage = lazy(() =>
  import('../pages/SettingsPage').then((m) => ({ default: m.SettingsPage })),
)
const AdminCompaniesPage = lazy(() =>
  import('../pages/AdminCompaniesPage').then((m) => ({ default: m.AdminCompaniesPage })),
)

function PageLoadingFallback() {
  return (
    <div className="p-6 space-y-4 animate-in fade-in duration-100">
      <div className="h-7 w-1/3 bg-[#F2F2F0] rounded-md animate-pulse" />
      <div className="h-4 w-1/2 bg-[#F2F2F0] rounded-md animate-pulse" />
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 pt-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-28 rounded-xl bg-[#F2F2F0] animate-pulse" />
        ))}
      </div>
      <div className="h-64 rounded-xl bg-[#F2F2F0] animate-pulse mt-6" />
    </div>
  )
}

export function AppRouter() {
  return (
    <Routes>
      {/* Public Auth Routes */}
      <Route
        path="/login"
        element={
          <Suspense fallback={<PageLoadingFallback />}>
            <LoginPage />
          </Suspense>
        }
      />
      <Route
        path="/register"
        element={
          <Suspense fallback={<PageLoadingFallback />}>
            <RegisterPage />
          </Suspense>
        }
      />
      <Route
        path="/forgot-password"
        element={
          <Suspense fallback={<PageLoadingFallback />}>
            <ForgotPasswordPage />
          </Suspense>
        }
      />

      {/* Protected Application Routes */}
      <Route element={<ProtectedRoute />}>
        <Route element={<ApplicationShell />}>
          <Route path="/" element={<Navigate to="/overview" replace />} />

          {/* Accessible to COMPANY and ADMIN */}
          <Route
            path="/overview"
            element={
              <Suspense fallback={<PageLoadingFallback />}>
                <OverviewPage />
              </Suspense>
            }
          />
          <Route
            path="/batches"
            element={
              <Suspense fallback={<PageLoadingFallback />}>
                <BatchesPage />
              </Suspense>
            }
          />
          <Route
            path="/batches/:batchId"
            element={
              <Suspense fallback={<PageLoadingFallback />}>
                <BatchDetailPage />
              </Suspense>
            }
          />
          <Route
            path="/calls"
            element={
              <Suspense fallback={<PageLoadingFallback />}>
                <CallsPage />
              </Suspense>
            }
          />
          <Route
            path="/calls/:callId"
            element={
              <Suspense fallback={<PageLoadingFallback />}>
                <CallDetailPage />
              </Suspense>
            }
          />
          <Route
            path="/search"
            element={
              <Suspense fallback={<PageLoadingFallback />}>
                <SearchPage />
              </Suspense>
            }
          />
          <Route path="/semantic-search" element={<Navigate to="/search" replace />} />
          <Route
            path="/themes"
            element={
              <Suspense fallback={<PageLoadingFallback />}>
                <ThemesPage />
              </Suspense>
            }
          />
          <Route
            path="/themes/:themeId"
            element={
              <Suspense fallback={<PageLoadingFallback />}>
                <ThemeDetailPage />
              </Suspense>
            }
          />
          <Route
            path="/risk"
            element={
              <Suspense fallback={<PageLoadingFallback />}>
                <RiskPage />
              </Suspense>
            }
          />
          <Route path="/escalation-risk" element={<Navigate to="/risk" replace />} />
          <Route
            path="/reports"
            element={
              <Suspense fallback={<PageLoadingFallback />}>
                <ReportsPage />
              </Suspense>
            }
          />
          <Route
            path="/reports/:reportId"
            element={
              <Suspense fallback={<PageLoadingFallback />}>
                <ReportsPage />
              </Suspense>
            }
          />
          <Route
            path="/profile"
            element={
              <Suspense fallback={<PageLoadingFallback />}>
                <SettingsPage />
              </Suspense>
            }
          />

          {/* ADMIN ONLY Routes */}
          <Route element={<RoleRoute allowedRoles={['ADMIN']} />}>
            <Route
              path="/admin/companies"
              element={
                <Suspense fallback={<PageLoadingFallback />}>
                  <AdminCompaniesPage />
                </Suspense>
              }
            />
            <Route
              path="/jobs"
              element={
                <Suspense fallback={<PageLoadingFallback />}>
                  <JobsPage />
                </Suspense>
              }
            />
            <Route path="/admin/processing-jobs" element={<Navigate to="/jobs" replace />} />
            <Route
              path="/evaluation"
              element={
                <Suspense fallback={<PageLoadingFallback />}>
                  <EvaluationPage />
                </Suspense>
              }
            />
            <Route path="/admin/ai-evaluation" element={<Navigate to="/evaluation" replace />} />
            <Route
              path="/settings"
              element={
                <Suspense fallback={<PageLoadingFallback />}>
                  <SettingsPage />
                </Suspense>
              }
            />
            <Route path="/admin/system-settings" element={<Navigate to="/settings" replace />} />
          </Route>

          <Route
            path="*"
            element={
              <div className="py-12">
                <EmptyState
                  title="Page Not Found"
                  description="The route you navigated to does not exist in the application."
                  action={
                    <Link to="/overview">
                      <Button size="sm">Return to Overview</Button>
                    </Link>
                  }
                />
              </div>
            }
          />
        </Route>
      </Route>
    </Routes>
  )
}
