/**
 * AI Call Analytics — Forgot Password Page.
 */

import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { Activity, AlertCircle, ArrowLeft, ArrowRight, CheckCircle2, Lock, Mail } from 'lucide-react'
import { authApi } from '../api/auth'
import { Button } from '../components/ui/Button'

export function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [step, setStep] = useState<'request' | 'reset' | 'success'>('request')
  const [isLoading, setIsLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  const handleRequestReset = async (e: React.FormEvent) => {
    e.preventDefault()
    setErrorMessage(null)
    setIsLoading(true)

    try {
      const res = await authApi.forgotPassword({ email })
      setSuccessMessage(res.message || 'Password reset instructions dispatched.')
      setStep('reset')
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unable to initiate password reset.'
      setErrorMessage(msg)
    } finally {
      setIsLoading(false)
    }
  }

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault()
    setErrorMessage(null)

    if (newPassword !== confirmPassword) {
      setErrorMessage('Passwords do not match.')
      return
    }

    if (newPassword.length < 8) {
      setErrorMessage('Password must be at least 8 characters long.')
      return
    }

    setIsLoading(true)
    try {
      await authApi.resetPassword({ email, new_password: newPassword })
      setStep('success')
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to update password.'
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
          Reset Password
        </h1>
        <p className="text-xs sm:text-sm text-[#60636B] mt-1 font-medium">
          Recover access to your AI Call Analytics workspace
        </p>
      </div>

      {/* Card */}
      <div className="w-full max-w-md bg-white border border-[#E5E5E2] rounded-2xl shadow-sm p-6 sm:p-8 space-y-6">
        {errorMessage && (
          <div className="flex items-start gap-3 p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs animate-in fade-in duration-200">
            <AlertCircle className="h-4 w-4 text-rose-600 shrink-0 mt-0.5" />
            <div className="leading-relaxed font-medium">{errorMessage}</div>
          </div>
        )}

        {step === 'request' && (
          <form onSubmit={handleRequestReset} className="space-y-4">
            <p className="text-xs text-[#60636B]">
              Enter your account's email address below and we'll help you reset your password.
            </p>

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

            <Button
              type="submit"
              disabled={isLoading || !email}
              className="w-full py-2.5 mt-2 bg-[#6D5AE6] hover:bg-[#5844D6] text-white font-medium rounded-xl transition-all shadow-sm shadow-[#6D5AE6]/25 flex items-center justify-center gap-2 cursor-pointer"
            >
              {isLoading ? (
                <span className="flex items-center gap-2">
                  <span className="h-4 w-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Processing...
                </span>
              ) : (
                <>
                  <span>Continue</span>
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </Button>
          </form>
        )}

        {step === 'reset' && (
          <form onSubmit={handleResetPassword} className="space-y-4 animate-in fade-in duration-200">
            {successMessage && (
              <div className="flex items-start gap-2.5 p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs">
                <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0 mt-0.5" />
                <div>{successMessage}</div>
              </div>
            )}

            <div>
              <label
                htmlFor="new-password"
                className="block text-xs font-semibold text-[#17181C] uppercase tracking-wider mb-1.5"
              >
                New Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-[#8A8D95]" />
                <input
                  id="new-password"
                  type="password"
                  required
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Minimum 8 characters"
                  className="w-full pl-10 pr-3.5 py-2.5 rounded-xl border border-[#E5E5E2] bg-[#FAFAF8] text-sm text-[#17181C] placeholder-[#8A8D95] focus:outline-none focus:border-[#6D5AE6] focus:ring-2 focus:ring-[#6D5AE6]/20 transition-all font-mono"
                />
              </div>
            </div>

            <div>
              <label
                htmlFor="confirm-password"
                className="block text-xs font-semibold text-[#17181C] uppercase tracking-wider mb-1.5"
              >
                Confirm New Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-[#8A8D95]" />
                <input
                  id="confirm-password"
                  type="password"
                  required
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Repeat new password"
                  className="w-full pl-10 pr-3.5 py-2.5 rounded-xl border border-[#E5E5E2] bg-[#FAFAF8] text-sm text-[#17181C] placeholder-[#8A8D95] focus:outline-none focus:border-[#6D5AE6] focus:ring-2 focus:ring-[#6D5AE6]/20 transition-all font-mono"
                />
              </div>
            </div>

            <Button
              type="submit"
              disabled={isLoading || !newPassword || !confirmPassword}
              className="w-full py-2.5 mt-2 bg-[#6D5AE6] hover:bg-[#5844D6] text-white font-medium rounded-xl transition-all shadow-sm shadow-[#6D5AE6]/25 flex items-center justify-center gap-2 cursor-pointer"
            >
              {isLoading ? (
                <span className="flex items-center gap-2">
                  <span className="h-4 w-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Updating Password...
                </span>
              ) : (
                <>
                  <span>Save New Password</span>
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </Button>
          </form>
        )}

        {step === 'success' && (
          <div className="text-center py-4 space-y-4 animate-in fade-in duration-200">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-emerald-100 text-emerald-600">
              <CheckCircle2 className="h-6 w-6" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-[#17181C]">Password Reset Complete</h3>
              <p className="text-xs text-[#60636B] mt-1">
                Your password has been securely updated. You can now log in with your new credentials.
              </p>
            </div>
            <Link to="/login" className="block pt-2">
              <Button className="w-full py-2.5 bg-[#6D5AE6] hover:bg-[#5844D6] text-white font-medium rounded-xl">
                Return to Sign In
              </Button>
            </Link>
          </div>
        )}

        {/* Back to Login */}
        <div className="text-center pt-2 text-xs text-[#60636B]">
          <Link
            to="/login"
            className="inline-flex items-center gap-1.5 font-medium text-[#6D5AE6] hover:text-[#5844D6] hover:underline"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to Sign In
          </Link>
        </div>
      </div>
    </div>
  )
}
