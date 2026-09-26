/**
AI Call Analytics — Workspace Registration Page.
 */

import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Activity, AlertCircle, ArrowRight, Building2, Lock, Mail, User } from 'lucide-react'
import { authApi } from '../api/auth'
import { useAuthStore } from '../stores/authStore'
import { Button } from '../components/ui/Button'

export function RegisterPage() {
  const navigate = useNavigate()
  const { setAuth } = useAuthStore()

  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [companyName, setCompanyName] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setErrorMessage(null)

    if (password.length < 8) {
      setErrorMessage('Password must be at least 8 characters long.')
      return
    }

    setIsLoading(true)

    try {
      const res = await authApi.register({
        full_name: fullName,
        email,
        password,
        company_name: companyName,
      })
      setAuth(res.access_token, res.user)
      navigate('/overview', { replace: true })
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Registration failed. Please try again.'
      setErrorMessage(msg)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen w-full flex flex-col justify-center items-center bg-[#FAFAF8] p-4 sm:p-6">
      {/* Brand Header */}
      <div className="flex flex-col items-center mb-8 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-[#6D5AE6] text-white shadow-md shadow-[#6D5AE6]/25 mb-3">
          <Activity className="h-6 w-6" />
        </div>
        <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-[#17181C]">
          Create Enterprise Workspace
        </h1>
        <p className="text-xs sm:text-sm text-[#60636B] mt-1 font-medium">
          Set up multi-tenant AI call analytics for your organization
        </p>
      </div>

      {/* Registration Card */}
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
              htmlFor="companyName"
              className="block text-xs font-semibold text-[#17181C] uppercase tracking-wider mb-1.5"
            >
              Company / Workspace Name
            </label>
            <div className="relative">
              <Building2 className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-[#8A8D95]" />
              <input
                id="companyName"
                type="text"
                required
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                placeholder="e.g. Acme Corporation"
                className="w-full pl-10 pr-3.5 py-2.5 rounded-xl border border-[#E5E5E2] bg-[#FAFAF8] text-sm text-[#17181C] placeholder-[#8A8D95] focus:outline-none focus:border-[#6D5AE6] focus:ring-2 focus:ring-[#6D5AE6]/20 transition-all"
              />
            </div>
          </div>

          <div>
            <label
              htmlFor="fullName"
              className="block text-xs font-semibold text-[#17181C] uppercase tracking-wider mb-1.5"
            >
              Your Full Name
            </label>
            <div className="relative">
              <User className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-[#8A8D95]" />
              <input
                id="fullName"
                type="text"
                required
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="e.g. Sarah Connor"
                className="w-full pl-10 pr-3.5 py-2.5 rounded-xl border border-[#E5E5E2] bg-[#FAFAF8] text-sm text-[#17181C] placeholder-[#8A8D95] focus:outline-none focus:border-[#6D5AE6] focus:ring-2 focus:ring-[#6D5AE6]/20 transition-all"
              />
            </div>
          </div>

          <div>
            <label
              htmlFor="email"
              className="block text-xs font-semibold text-[#17181C] uppercase tracking-wider mb-1.5"
            >
              Work Email Address
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
            <label
              htmlFor="password"
              className="block text-xs font-semibold text-[#17181C] uppercase tracking-wider mb-1.5"
            >
              Password (min 8 characters)
            </label>
            <div className="relative">
              <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-[#8A8D95]" />
              <input
                id="password"
                type="password"
                required
                minLength={8}
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full pl-10 pr-3.5 py-2.5 rounded-xl border border-[#E5E5E2] bg-[#FAFAF8] text-sm text-[#17181C] placeholder-[#8A8D95] focus:outline-none focus:border-[#6D5AE6] focus:ring-2 focus:ring-[#6D5AE6]/20 transition-all font-mono"
              />
            </div>
          </div>

          <Button
            type="submit"
            disabled={isLoading || !fullName || !email || !password || !companyName}
            className="w-full py-2.5 mt-2 bg-[#6D5AE6] hover:bg-[#5844D6] text-white font-medium rounded-xl transition-all shadow-sm shadow-[#6D5AE6]/25 flex items-center justify-center gap-2 cursor-pointer"
          >
            {isLoading ? (
              <span className="flex items-center gap-2">
                <span className="h-4 w-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Setting up Workspace...
              </span>
            ) : (
              <>
                <span>Create Workspace</span>
                <ArrowRight className="h-4 w-4" />
              </>
            )}
          </Button>
        </form>

        {/* Existing Account Link */}
        <div className="text-center pt-2 border-t border-[#E5E5E2] text-xs text-[#60636B]">
          Already have an account?{' '}
          <Link
            to="/login"
            className="font-semibold text-[#6D5AE6] hover:text-[#5844D6] hover:underline"
          >
            Sign In here
          </Link>
        </div>
      </div>
    </div>
  )
}
