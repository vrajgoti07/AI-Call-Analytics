/**
AI Call Analytics — Login Page.
 */

import React, { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { Activity, AlertCircle, ArrowRight, CheckCircle2, Lock, Mail } from 'lucide-react'
import { authApi } from '../api/auth'
import { useAuthStore } from '../stores/authStore'
import { Button } from '../components/ui/Button'

export function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { setAuth } = useAuthStore()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/overview'

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setErrorMessage(null)
    setIsLoading(true)

    try {
      const res = await authApi.login({ email, password })
      setAuth(res.access_token, res.user)
      navigate(from, { replace: true })
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Invalid credentials. Please try again.'
      setErrorMessage(msg)
    } finally {
      setIsLoading(false)
    }
  }

  const fillDemoAdmin = () => {
    setEmail('admin@acmecorp.com')
    setPassword('Password123!')
    setErrorMessage(null)
  }

  return (
    <div className="min-h-screen w-full flex flex-col justify-center items-center bg-[#FAFAF8] p-4 sm:p-6">
      {/* Brand Header */}
      <div className="flex flex-col items-center mb-8 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-[#6D5AE6] text-white shadow-md shadow-[#6D5AE6]/25 mb-3">
          <Activity className="h-6 w-6" />
        </div>
        <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-[#17181C]">
          AI Call Analytics
        </h1>
        <p className="text-xs sm:text-sm text-[#60636B] mt-1 font-medium">
          Sign in to access your company intelligence workspace
        </p>
      </div>

      {/* Main Login Card */}
      <div className="w-full max-w-md bg-white border border-[#E5E5E2] rounded-2xl shadow-sm p-6 sm:p-8 space-y-6">
        {errorMessage && (
          <div className="flex items-start gap-3 p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs animate-in fade-in duration-200">
            <AlertCircle className="h-4 w-4 text-rose-600 shrink-0 mt-0.5" />
            <div className="leading-relaxed font-medium">{errorMessage}</div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="email"
              className="block text-xs font-semibold text-[#17181C] uppercase tracking-wider mb-1.5"
            >
              Email Address
            </label>
            <div className="relative">
              <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-[#8A8D95]" />
              <input
                id="email"
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@company.com"
                className="w-full pl-10 pr-3.5 py-2.5 rounded-xl border border-[#E5E5E2] bg-[#FAFAF8] text-sm text-[#17181C] placeholder-[#8A8D95] focus:outline-none focus:border-[#6D5AE6] focus:ring-2 focus:ring-[#6D5AE6]/20 transition-all"
              />
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label
                htmlFor="password"
                className="block text-xs font-semibold text-[#17181C] uppercase tracking-wider"
              >
                Password
              </label>
            </div>
            <div className="relative">
              <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-[#8A8D95]" />
              <input
                id="password"
                type="password"
                required
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full pl-10 pr-3.5 py-2.5 rounded-xl border border-[#E5E5E2] bg-[#FAFAF8] text-sm text-[#17181C] placeholder-[#8A8D95] focus:outline-none focus:border-[#6D5AE6] focus:ring-2 focus:ring-[#6D5AE6]/20 transition-all font-mono"
              />
            </div>
          </div>

          <Button
            type="submit"
            disabled={isLoading || !email || !password}
            className="w-full py-2.5 mt-2 bg-[#6D5AE6] hover:bg-[#5844D6] text-white font-medium rounded-xl transition-all shadow-sm shadow-[#6D5AE6]/25 flex items-center justify-center gap-2 cursor-pointer"
          >
            {isLoading ? (
              <span className="flex items-center gap-2">
                <span className="h-4 w-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Signing In...
              </span>
            ) : (
              <>
                <span>Sign In</span>
                <ArrowRight className="h-4 w-4" />
              </>
            )}
          </Button>
        </form>

        {/* Demo Quick Login Helper */}
        <div className="pt-2 border-t border-[#E5E5E2]">
          <div className="p-3 bg-[#F7F7F5] border border-[#E5E5E2] rounded-xl space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-[#17181C] flex items-center gap-1.5">
                <CheckCircle2 className="h-3.5 w-3.5 text-[#6D5AE6]" />
                Demo Credentials
              </span>
              <button
                type="button"
                onClick={fillDemoAdmin}
                className="text-[11px] font-semibold text-[#6D5AE6] hover:underline cursor-pointer"
              >
                Auto-fill
              </button>
            </div>
            <div className="text-[11px] text-[#60636B] font-mono leading-tight space-y-0.5">
              <div>admin@acmecorp.com</div>
              <div>Password123!</div>
            </div>
          </div>
        </div>

        {/* Registration Link */}
        <div className="text-center pt-1 text-xs text-[#60636B]">
          Need a workspace for your team?{' '}
          <Link
            to="/register"
            className="font-semibold text-[#6D5AE6] hover:text-[#5844D6] hover:underline"
          >
            Create Company Workspace
          </Link>
        </div>
      </div>
    </div>
  )
}
