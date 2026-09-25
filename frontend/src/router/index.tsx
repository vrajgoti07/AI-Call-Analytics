import { Navigate, Route, Routes } from 'react-router-dom'
import { ApplicationShell } from '../components/layout/ApplicationShell'
import { OverviewPage } from '../pages/OverviewPage'
import { CallsPage } from '../pages/CallsPage'
import { CallDetailPage } from '../pages/CallDetailPage'
import { SearchPage } from '../pages/SearchPage'
import { ThemesPage } from '../pages/ThemesPage'
import { ThemeDetailPage } from '../pages/ThemeDetailPage'
import { RiskPage } from '../pages/RiskPage'
import { EvaluationPage } from '../pages/EvaluationPage'
import { JobsPage } from '../pages/JobsPage'
import { SettingsPage } from '../pages/SettingsPage'
import { EmptyState } from '../components/ui/EmptyState'
import { Button } from '../components/ui/Button'
import { Link } from 'react-router-dom'

export function AppRouter() {
  return (
    <Routes>
      <Route element={<ApplicationShell />}>
        <Route path="/" element={<Navigate to="/overview" replace />} />
        <Route path="/overview" element={<OverviewPage />} />
        <Route path="/calls" element={<CallsPage />} />
        <Route path="/calls/:callId" element={<CallDetailPage />} />
        <Route path="/search" element={<SearchPage />} />
        <Route path="/themes" element={<ThemesPage />} />
        <Route path="/themes/:themeId" element={<ThemeDetailPage />} />
        <Route path="/risk" element={<RiskPage />} />
        <Route path="/evaluation" element={<EvaluationPage />} />
        <Route path="/jobs" element={<JobsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
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
    </Routes>
  )
}
